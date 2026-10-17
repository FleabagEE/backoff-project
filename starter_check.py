"""Exercise the existing starter audio/FFT pipeline without Dear PyGui."""
import argparse
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from models import get_ear, get_audio_features


def check_raw_stereo(device, seconds, rate):
    """Compare PyAudio channels directly, without touching starter configuration."""
    import pyaudio
    pa = pyaudio.PyAudio()
    stream = None
    try:
        block = int(np.ceil(rate / 100 / 2) * 2)
        stream = pa.open(input_device_index=device, channels=2, rate=rate,
                         format=pyaudio.paInt16, input=True, frames_per_buffer=block)
        print(f'RAW_STEREO backend=PyAudio device={device} rate={rate} '
              f'channels=2 int16 block={block}; diagnostic only, no FFT changes.', flush=True)
        print('0-5 s quiet; 5-10 s knock; 10-15 s rub.', flush=True)
        n_total = 0
        peak_total = np.zeros(2)
        clipped_total = np.zeros(2, dtype=np.int64)
        start = time.monotonic()
        while time.monotonic() - start < seconds:
            sq = np.zeros(2)
            peak = np.zeros(2)
            clipped = np.zeros(2, dtype=np.int64)
            n = 0
            while n < rate * 0.5:
                # Default overflow handling raises instead of hiding dropped audio.
                raw = stream.read(block)
                data = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2)
                x = data.astype(np.float64) / 32768
                sq += np.sum(x * x, axis=0)
                peak = np.maximum(peak, np.max(np.abs(x), axis=0))
                clipped += np.sum((data == -32768) | (data == 32767), axis=0)
                n += len(data)
            n_total += n
            peak_total = np.maximum(peak_total, peak)
            clipped_total += clipped
            elapsed = time.monotonic() - start
            for c in range(2):
                print(f'{elapsed:5.1f}s ch{c+1} RMS={100*np.sqrt(sq[c]/n):.4f}% FS '
                      f'peak={100*peak[c]:.3f}% FS clip={100*clipped[c]/n:.5f}%', flush=True)
        for c in range(2):
            print(f'SUMMARY ch{c+1} max_peak={100*peak_total[c]:.3f}% FS '
                  f'clip={100*clipped_total[c]/n_total:.5f}%', flush=True)
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pa.terminate()


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=int, required=True, help='PyAudio index, not sounddevice index')
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--raw-stereo', action='store_true', help='diagnose PyAudio L/R without the FFT pipeline')
    parser.add_argument('--rate', type=int, default=48000, help='raw-stereo only; match existing starter rate (default 48000)')
    args = parser.parse_args()
    if args.seconds <= 0 or args.rate <= 0:
        parser.error('--seconds and --rate must be positive')
    if args.raw_stereo:
        check_raw_stereo(args.device, args.seconds, args.rate)
        return
    ear = None
    try:
        # No rate, FFT or preprocessing overrides: call the starter verbatim.
        ear = get_ear(args.device)
        reader = ear.stream_reader
        print(f'CHECK backend={type(reader).__name__} rate={ear.rate} '
              f'FFT_samples={ear.FFT_window_size}', flush=True)
        print('0-5 s quiet; 5-10 s knock; 10-15 s rub. No training data saved.', flush=True)
        start = time.monotonic()
        report = start
        last_count = ear.num_ffts
        while time.monotonic() - start < args.seconds:
            freqs, amps = get_audio_features(ear)
            now = time.monotonic()
            if now >= report:
                data = reader.data_buffer.get_most_recent(ear.FFT_window_size).astype(np.float64)
                pcm_rms = float(np.sqrt(np.mean(data * data)))
                pcm_peak = float(np.max(np.abs(data)))
                peak_index = int(np.argmax(amps))
                active = reader.stream.is_active() if hasattr(reader.stream, 'is_active') else reader.stream.active
                print(f'{now-start:5.1f}s active={active} FFT_updates={ear.num_ffts-last_count} '
                      f'PCM_RMS={pcm_rms:.3f} PCM_peak={pcm_peak:.3f} '
                      f'FFT_peak={float(amps[peak_index]):.3g} '
                      f'peak_Hz={float(freqs[peak_index]):.1f}', flush=True)
                last_count = ear.num_ffts
                report = now + 0.5
            time.sleep(0.02)
        print(f'DONE total_FFT_updates={ear.num_ffts}', flush=True)
    except KeyboardInterrupt:
        print('Stopped.')
    finally:
        if ear is not None:
            ear.stream_reader.terminate()


if __name__ == '__main__':
    main()
