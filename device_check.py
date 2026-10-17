"""Read-only audio diagnostic; does not import or change the starter pipeline."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import sounddevice as sd


def dbfs(value):
    return 20 * math.log10(value) if value > 0 else float('-inf')


def run(args):
    apis = sd.query_hostapis()
    if args.device is None:
        print('INDEX | HOST API | INPUT CHANNELS | DEFAULT Hz | NAME')
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels']:
                print(f"{i:5} | {apis[d['hostapi']]['name']} | "
                      f"{d['max_input_channels']} | {d['default_samplerate']:g} | {d['name']}")
        print('Indices belong to sounddevice. Re-list after reconnecting USB.')
        return

    d = sd.query_devices(args.device, 'input')
    if args.channels > d['max_input_channels']:
        raise ValueError(f"Device exposes only {d['max_input_channels']} input channels")
    rate = args.rate
    block = math.ceil((rate / 100) / 2) * 2  # models.get_ear -> updates_per_second=100
    info = dict(device=args.device, name=d['name'], host_api=apis[d['hostapi']]['name'],
                channels=args.channels, sample_rate=rate, dtype='int16', blocksize=block,
                label=args.label)
    print('CONFIG ' + json.dumps(info, ensure_ascii=False), flush=True)
    print('Current starter profile: stereo int16, 48000 Hz, select ch2.'
          ' This script measures all requested channels with sounddevice; starter uses PyAudio.', flush=True)
    print('Levels: percent digital full scale (FS); dBFS=20log10(amplitude/FS).'
          ' clip%=samples at int16 rails. No audio file is saved.', flush=True)

    output = None
    writer = None
    total_n = 0
    total_sq = np.zeros(args.channels)
    total_clip = np.zeros(args.channels, dtype=np.int64)
    total_peak = np.zeros(args.channels)
    interval_rms = []
    overflow_count = 0
    try:
        # Open stream before creating CSV: failed devices leave no misleading log.
        with sd.InputStream(device=args.device, samplerate=rate, channels=args.channels,
                            dtype='int16', blocksize=block) as stream:
            print(f'OPENED actual_rate={stream.samplerate:g} Hz; Ctrl+C stops.', flush=True)
            if args.csv:
                path = Path(args.csv)
                path.parent.mkdir(parents=True, exist_ok=True)
                output = path.open('a', newline='', encoding='utf-8')
                writer = csv.DictWriter(output, fieldnames=[
                    'started_utc', 'label', 'device', 'name', 'host_api', 'sample_rate',
                    'channels', 'elapsed_s', 'channel', 'rms_fs', 'rms_dbfs',
                    'peak_fs', 'peak_dbfs', 'clip_pct', 'overflow_blocks'])
                if path.stat().st_size == 0:
                    writer.writeheader()
            started_utc = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            start = time.monotonic()
            while time.monotonic() - start < args.seconds:
                sq = np.zeros(args.channels)
                peak = np.zeros(args.channels)
                clipped = np.zeros(args.channels, dtype=np.int64)
                n = 0
                overflows = 0
                # Aggregate ~0.5 s for readable live output and robust transient peaks.
                target = min(args.interval, args.seconds - (time.monotonic() - start))
                while n < max(1, int(rate * target)):
                    data, overflowed = stream.read(block)
                    x = data.astype(np.float64) / 32768.0
                    sq += np.sum(x * x, axis=0)
                    peak = np.maximum(peak, np.max(np.abs(x), axis=0))
                    clipped += np.sum((data == -32768) | (data == 32767), axis=0)
                    n += len(data)
                    overflows += int(overflowed)
                elapsed = time.monotonic() - start
                rms = np.sqrt(sq / n)
                interval_rms.append(rms)
                total_n += n
                total_sq += sq
                total_clip += clipped
                total_peak = np.maximum(total_peak, peak)
                overflow_count += overflows
                for c in range(args.channels):
                    clip_pct = 100 * clipped[c] / n
                    print(f'{elapsed:5.1f}s ch{c+1} RMS={100*rms[c]:7.3f}% FS '
                          f'({dbfs(rms[c]):6.1f} dBFS) peak={100*peak[c]:7.3f}% FS '
                          f'clip={clip_pct:.4f}% overflow_blocks={overflows}', flush=True)
                    if writer:
                        writer.writerow(dict(started_utc=started_utc, label=args.label,
                            device=args.device, name=d['name'], host_api=info['host_api'],
                            sample_rate=rate, channels=args.channels, elapsed_s=round(elapsed, 3),
                            channel=c+1, rms_fs=rms[c], rms_dbfs=dbfs(rms[c]),
                            peak_fs=peak[c], peak_dbfs=dbfs(peak[c]), clip_pct=clip_pct,
                            overflow_blocks=overflows))
                if output:
                    output.flush()
    except KeyboardInterrupt:
        print('\nStopped by user.')
    finally:
        if output:
            output.close()
        if total_n:
            print(f'SUMMARY label={args.label} captured_s={total_n/rate:.2f} '
                  f'overflow_blocks={overflow_count}')
            for c in range(args.channels):
                rms = math.sqrt(total_sq[c] / total_n)
                med = float(np.median(np.array(interval_rms)[:, c]))
                print(f'ch{c+1} overall_RMS={100*rms:.4f}% FS ({dbfs(rms):.1f} dBFS) '
                      f'median_interval_RMS={100*med:.4f}% FS '
                      f'max_peak={100*total_peak[c]:.3f}% FS '
                      f'clip={100*total_clip[c]/total_n:.5f}%')


def main():
    # Windows terminals may lack glyphs; never let a device name crash diagnostics.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=int, help='sounddevice input index; omit to list')
    parser.add_argument('--channels', type=int, default=2, help='default 2 (current starter); use 1 only for mono diagnostics')
    parser.add_argument('--rate', type=int, default=48000, help='default 48000, matching the frozen starter profile')
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--interval', type=float, default=0.5)
    parser.add_argument('--label', default='channel_check')
    parser.add_argument('--csv', help='append per-channel interval measurements to this CSV')
    args = parser.parse_args()
    if args.channels < 1 or args.seconds <= 0 or args.interval <= 0 or (args.rate is not None and args.rate <= 0):
        parser.error('channels, seconds, interval and rate must be positive')
    try:
        run(args)
    except (sd.PortAudioError, ValueError, RuntimeError, OSError) as exc:
        print(f'ERROR: {exc}\nClose visualizer/other audio apps, re-list devices, and check '
              'Windows microphone permissions. Do not change starter rate/FFT to fix a device entry.',
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
