"""Read-only audio diagnostic; does not import or change the starter pipeline."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
import time
import uuid

import numpy as np
import sounddevice as sd


def dbfs(value):
    return 20 * math.log10(value) if value > 0 else float('-inf')


class RmsWindows:
    """Non-overlapping 50 ms PCM RMS measurements; no FFT/feature changes."""
    def __init__(self, rate, channels):
        self.frames = round(rate * 0.05)
        self.squares = np.zeros(channels)
        self.count = 0
        self.values = []

    def append(self, samples):
        offset = 0
        while offset < len(samples):
            size = min(self.frames - self.count, len(samples) - offset)
            part = samples[offset:offset + size]
            self.squares += np.sum(part * part, axis=0)
            self.count += size
            offset += size
            if self.count == self.frames:
                self.values.append(np.sqrt(self.squares / self.frames))
                self.squares = np.zeros_like(self.squares)
                self.count = 0


def append_summary(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    exists = path.exists() and path.stat().st_size > 0
    if exists:
        with path.open(newline='', encoding='utf-8') as handle:
            if next(csv.reader(handle)) != fields:
                raise ValueError(f'Summary CSV schema differs: use a new file, not {path}')
    with path.open('a', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


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
    windows = RmsWindows(rate, args.channels)
    started_utc = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    run_id = uuid.uuid4().hex[:12]
    target_frames = round(rate * args.seconds)
    try:
        # Open stream before creating CSV: failed devices leave no misleading log.
        with sd.InputStream(device=args.device, samplerate=rate, channels=args.channels,
                            dtype='int16', blocksize=block) as stream:
            print(f'OPENED actual_rate={stream.samplerate:g} Hz; Ctrl+C stops.', flush=True)
            print(f'WARMUP {args.warmup_seconds:g}s (discarded), then {args.seconds:g}s measurement.', flush=True)
            remaining = round(rate * args.warmup_seconds)
            while remaining > 0:
                size = min(block, remaining)
                stream.read(size)
                remaining -= size
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
            print('MEASURING NOW: perform only the condition named in label.', flush=True)
            while total_n < target_frames:
                sq = np.zeros(args.channels)
                peak = np.zeros(args.channels)
                clipped = np.zeros(args.channels, dtype=np.int64)
                n = 0
                overflows = 0
                # Aggregate ~0.5 s for readable live output and robust transient peaks.
                target = min(max(1, round(rate * args.interval)), target_frames - total_n)
                while n < target:
                    data, overflowed = stream.read(min(block, target - n))
                    x = data.astype(np.float64) / 32768.0
                    windows.append(x)
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
            complete = total_n == target_frames
            print(f'SUMMARY label={args.label} captured_s={total_n/rate:.2f} '
                  f'overflow_blocks={overflow_count} complete={complete} '
                  f'RMS_window_ms=50 window_count={len(windows.values)}')
            rows = []
            for c in range(args.channels):
                rms = math.sqrt(total_sq[c] / total_n)
                med = float(np.median(np.array(interval_rms)[:, c]))
                median = float(np.median(np.array(windows.values)[:, c])) if windows.values else float('nan')
                p10 = float(np.percentile(np.array(windows.values)[:, c], 10)) if windows.values else float('nan')
                print(f'ch{c+1} overall_RMS={100*rms:.4f}% FS ({dbfs(rms):.1f} dBFS) '
                      f'median_interval_RMS={100*med:.4f}% FS '
                      f'median_window_RMS={100*median:.4f}% FS '
                      f'p10_window_RMS={100*p10:.4f}% FS '
                      f'max_peak={100*total_peak[c]:.3f}% FS '
                      f'clip={100*total_clip[c]/total_n:.5f}%')
                rows.append(dict(run_id=run_id, started_utc=started_utc, label=args.label,
                    gain_note=args.gain_note, device=args.device, name=d['name'],
                    host_api=info['host_api'], sample_rate=rate, channels=args.channels,
                    channel=c+1, requested_s=args.seconds, captured_s=total_n/rate,
                    warmup_s=args.warmup_seconds, complete=complete, rms_window_ms=50,
                    rms_window_count=len(windows.values), median_rms_fs=median,
                    p10_rms_fs=p10, overall_rms_fs=rms, max_peak_fs=total_peak[c],
                    clip_pct=100*total_clip[c]/total_n, overflow_blocks=overflow_count))
            if args.summary_csv:
                append_summary(args.summary_csv, rows)
                print(f'SUMMARY_CSV {args.summary_csv}', flush=True)


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
    parser.add_argument('--summary-csv', help='append one run-summary row per channel, including median/P10 of 50 ms RMS')
    parser.add_argument('--gain-note', default='', help='operator gain/configuration identifier; no hardware settings are changed')
    parser.add_argument('--warmup-seconds', type=float, default=1.0, help='discard startup audio before the timed measurement (default 1)')
    args = parser.parse_args()
    if args.channels < 1 or args.seconds <= 0 or args.interval <= 0 or (args.rate is not None and args.rate <= 0):
        parser.error('channels, seconds, interval and rate must be positive')
    if args.warmup_seconds < 0:
        parser.error('warmup-seconds must not be negative')
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
