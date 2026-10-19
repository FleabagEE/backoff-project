"""Offline event boundaries from existing FFT features; never changes capture.

Undo known frequency weighting before summing squared smoothed magnitudes.
Energy is a proxy, not exact unsmoothed PCM band power. Units are arbitrary but
consistent. Quiet-only calibration must be separate from scored test windows.
"""
from dataclasses import asdict, dataclass

import numpy as np


def band_energy(X, rate=48000, fft_samples=2400):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[1] != fft_samples // 2:
        raise ValueError('Expected full 1200 saved amplitudes per window')
    if not np.isfinite(X).all() or (X < 0).any():
        raise ValueError('Invalid FFT amplitudes')
    hz = np.arange(1, X.shape[1] + 1) * rate / fft_samples
    weight = np.logspace(0, np.log2(np.log2(rate / 2)), X.shape[1], base=2)
    select = (hz >= 500) & (hz <= 8000)
    return np.sum((X[:, select] / weight[select]) ** 2, axis=1)


@dataclass(frozen=True)
class EventConfig:
    gate_energy: float
    onset_energy: float
    release_energy: float
    refractory_s: float = 1.7
    rearm_quiet_s: float = .15
    pre_s: float = .2
    post_s: float = 1.5


def calibrate(quiet_energy):
    quiet = np.asarray(quiet_energy, dtype=float)
    if quiet.ndim != 1 or len(quiet) < 50 or not np.isfinite(quiet).all() or (quiet < 0).any():
        raise ValueError('Need at least 50 finite quiet windows')
    p95, p99 = np.percentile(quiet, [95, 99])
    return EventConfig(gate_energy=float(p95), onset_energy=float(max(1.25*p99, 1.5*p95)),
                       release_energy=float(p95))


def segment_events(elapsed_s, energy, config):
    times = np.asarray(elapsed_s, dtype=float)
    values = np.asarray(energy, dtype=float)
    if (times.ndim != 1 or values.shape != times.shape or len(times) == 0
            or not np.isfinite(times).all() or not np.isfinite(values).all()
            or np.any(np.diff(times) <= 0) or (values < 0).any()):
        raise ValueError('Need matching finite arrays with increasing timestamps')
    armed, quiet_start, last_onset = True, None, -np.inf
    onsets = []
    for t, value in zip(times, values):
        if value <= config.release_energy:
            if quiet_start is None:
                quiet_start = t
            if t - quiet_start >= config.rearm_quiet_s:
                armed = True
        else:
            quiet_start = None
        if armed and value > config.onset_energy and t-last_onset >= config.refractory_s:
            onsets.append(float(t)); last_onset = t; armed = False
    context = np.zeros(len(times), dtype=bool)
    events = []
    for onset in onsets:
        start, stop = onset-config.pre_s, onset+config.post_s
        complete = start >= times[0] and stop <= times[-1]
        indexes = np.flatnonzero((times >= start) & (times <= stop))
        events.append(dict(onset_s=onset, start_s=start, stop_s=stop,
                           complete=bool(complete), window_count=len(indexes)))
        if complete:
            context[indexes] = True
    active = values > config.gate_energy
    # For positive TRAINING only: drop outside-event and quiet-like context
    # windows. Retain them in replay/evaluation; never hide missed events.
    return dict(config=asdict(config), events=events, detected_events=len(events),
                complete_events=sum(e['complete'] for e in events),
                context_mask=context, training_positive_mask=context & active,
                active_mask=active)


def event_decisions(times, scores, events, class_names):
    """Mean decision-score event classifier for later trial comparison."""
    times, scores = np.asarray(times), np.asarray(scores)
    if scores.shape != (len(times), len(class_names)):
        raise ValueError('One multiclass decision-score vector per saved window')
    result = []
    for event in events:
        select = (times >= event['start_s']) & (times <= event['stop_s'])
        if select.any():
            result.append(dict(onset_s=event['onset_s'],
                               label=class_names[int(np.argmax(scores[select].mean(axis=0)))],
                               complete=event['complete']))
    return result


def inspect_session(source, quiet_take_id, output):
    """Export boundaries/counts only from explicitly selected final_v3 TRAIN takes."""
    import json
    from pathlib import Path
    folder = Path(source).resolve()
    allowed = Path('data_sessions/final_v3').resolve()
    if not folder.is_relative_to(allowed):
        raise ValueError('Only the new final_v3 folder is eligible; pilot/old sessions are excluded')
    config = json.loads((folder/'config.json').read_text(encoding='utf-8'))
    if config.get('session_type') != 'final' or config.get('training_window_policy') != 'offline_event_segmentation_required':
        raise ValueError('Expected the new event-style final session')
    takes = []
    for path in sorted(folder.glob('take_*.npz')):
        if '.excluded.' in path.name:
            continue
        with np.load(path,allow_pickle=False) as d:
            info=json.loads(str(d['metadata_json']))
            if not info.get('valid',True) or info.get('split')!='train' or info.get('recording_kind')!='take':
                continue
            if json.loads(str(d['config_json'])) != config:
                raise ValueError('Mixed setup configuration')
            takes.append(dict(info=info, times=d['elapsed_s'].copy(), energy=band_energy(d['X'])))
    quiet = next((t for t in takes if t['info']['take_id']==quiet_take_id),None)
    if quiet is None or quiet['info']['class_name']!='neutral' or 'quiet' not in quiet['info'].get('variation',''):
        raise ValueError('Explicit new-session quiet training take required')
    calibration = quiet['times'] < 5.0
    detector = calibrate(quiet['energy'][calibration])
    rows=[]
    for take in takes:
        if take['info']['class_name'] not in ('knock','rub'):
            continue
        segmented=segment_events(take['times'],take['energy'],detector)
        rows.append(dict(take_id=take['info']['take_id'],class_name=take['info']['class_name'],
                         variation=take['info']['variation'],expected_events=take['info'].get('expected_events'),
                         detected_events=segmented['detected_events'],complete_events=segmented['complete_events'],
                         events=segmented['events'],total_windows=len(take['times']),
                         kept_positive_training_windows=int(segmented['training_positive_mask'].sum()),
                         dropped_positive_training_windows=int((~segmented['training_positive_mask']).sum())))
    report=dict(source=str(folder),setup_id=config['setup_id'],quiet_take_id=quiet_take_id,
                calibration_interval_s=[0,5],calibration_windows=int(calibration.sum()),
                config=asdict(detector),takes=rows,
                note='Quiet first 5s reserved for gate calibration, excluded from checkpoint model fitting/scoring. Positive outside-event/low-energy windows dropped for fitting. Keep full timelines for replay and report expected vs detected events; energy boundaries are weak labels, not human ground truth.')
    destination=Path(output)
    if destination.exists():
        raise FileExistsError('Keep earlier reports; choose a new output path')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--quiet-take-id',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    inspect_session(args.source,args.quiet_take_id,args.output)
