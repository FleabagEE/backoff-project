"""B's production training: energy gate + models.train_model(MODEL_B_PIPELINE).

Preprocessing, model and decision layer all live in models.py; this script only
runs grouped CV selection, final fitting and the one-time holdout evaluation.

1) Select gate/stability settings by grouped CV on corrected train.npz, then fit
   on all training takes and save <out>.model + <out>.json:
       uv run python train_b_model.py
2) Evaluate the saved model ONCE on holdout.npz (refuses to run twice):
       uv run python train_b_model.py --eval-holdout

The SVM is trained only on gate-active frames: at inference inactive frames are
forced to neutral, so quiet gaps inside knock/rub takes never act as labels.
Raw data is never modified.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from models import (B_MAX_HZ, B_SVM_C, MODEL_B_PIPELINE, NEUTRAL, TRIAL_TYPES, GateConfig,
                    StabilityConfig, calibrate_gate, decode_sequence, load_model, save_model,
                    train_model, trial_passes)

DATA_DIR = Path('handoff/20261017_195725_85cb47b5_review1')
CLASS_NAMES = ['neutral', 'knock', 'rub']
QUIET_PREFIX = 'quiet hands off'  # variation notes of the hands-off neutral takes
N_SPLITS = 6
K_KNOCK_OPTIONS = [1, 2, 3]
K_RUB_OPTIONS = [2, 4, 6, 8]
RELEASE_FRAMES = 3


def load_split(name):
    path = DATA_DIR / f'{name}.npz'
    with np.load(path, allow_pickle=False) as d:
        data = {k: d[k].copy() for k in ('X', 'y', 'take_ids', 'split', 'elapsed_s', 'rms_fs', 'peak_fs')}
        class_names = d['class_names'].tolist()
        config = json.loads(str(d['config_json']))
        takes = json.loads(str(d['takes_json']))
    assert data['X'].shape[1] == 1200 and config['sample_rate'] == 48000
    assert config['selected_channel_1_based'] == 2
    assert class_names == CLASS_NAMES, class_names
    assert set(data['split'].tolist()) == {name}, 'corrected split mismatch'
    variation = {t['take_id']: t['variation'] for t in takes}
    data['quiet'] = np.array([variation[t].startswith(QUIET_PREFIX) for t in data['take_ids']])
    data['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    data['path'] = str(path)
    return data


def fit_model(X, y):
    """Same models.train_model() path as the GUI; preprocessing lives inside the Pipeline."""
    model, _ = train_model(X, y, CLASS_NAMES, MODEL_B_PIPELINE)
    return model


def gated_predict(model, gate, X, rms, peak):
    """Inactive frames -> neutral without consulting the model (same as live inference)."""
    active = gate.is_active(rms, peak)
    labels = np.full(len(X), NEUTRAL, dtype=object)
    if active.any():
        labels[active] = np.asarray(CLASS_NAMES, dtype=object)[model.predict(X[active])]
    return labels, active


def simulate_trials(labels, data, stability, segment_s):
    """Chop each take into segment_s pieces; decode each piece like one SPACE trial.
    Knock/rub takes give positive trials; every take gives negatives for other actions."""
    counts = {t: [0, 0] for t in TRIAL_TYPES}  # [passed, total]
    groups, elapsed, y = data['take_ids'], data['elapsed_s'], data['y']
    for take in np.unique(groups):
        idx = np.where(groups == take)[0]
        idx = idx[np.argsort(elapsed[idx])]
        truth = CLASS_NAMES[y[idx[0]]]
        trial_types = [f'{truth}+'] if truth != NEUTRAL else []
        trial_types += [f'{x}-' for x in ('knock', 'rub') if x != truth]
        segment = np.floor(elapsed[idx] / segment_s).astype(int)
        for s in np.unique(segment):
            part = idx[segment == s]
            if elapsed[part[-1]] - elapsed[part[0]] < 0.8 * segment_s:
                continue  # short tail
            seen = set(decode_sequence(labels[part], stability))
            for trial_type in trial_types:
                counts[trial_type][0] += trial_passes(trial_type, seen)
                counts[trial_type][1] += 1
    return {t: dict(passed=p, total=n, rate=round(p / n, 3) if n else None) for t, (p, n) in counts.items()}


def frame_metrics(labels, active, data):
    """Confusion on gate-active frames (truth = take label) plus active fraction per class."""
    y = data['y']
    pred = np.array([CLASS_NAMES.index(label) for label in labels])
    cm = np.zeros((3, 3), int)
    np.add.at(cm, (y[active], pred[active]), 1)
    with np.errstate(invalid='ignore', divide='ignore'):
        recall = np.nan_to_num(cm.diagonal() / cm.sum(1)).round(3).tolist()
    active_fraction = {c: round(float(active[y == i].mean()), 3) for i, c in enumerate(CLASS_NAMES)}
    acc = float(np.trace(cm) / cm.sum()) if cm.sum() else 0.0
    return dict(active_fraction=active_fraction, active_window_acc=round(acc, 4),
                active_recall=recall, active_confusion=cm.tolist())


def stability_grid():
    for k_knock, k_rub in itertools.product(K_KNOCK_OPTIONS, K_RUB_OPTIONS):
        yield StabilityConfig(k_frames={'knock': k_knock, 'rub': k_rub}, release_frames=RELEASE_FRAMES)


def summarize(trials):
    rates = [trials[t]['rate'] for t in TRIAL_TYPES]
    return round(float(np.mean(rates)), 4), round(float(np.min(rates)), 4)


def cross_validate(data, args):
    X, y, groups, rms, peak, quiet = (data[k] for k in ('X', 'y', 'take_ids', 'rms_fs', 'peak_fs', 'quiet'))
    folds = list(StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=0).split(X, y, groups))
    results = []
    for scale in args.gate_scales:
        labels = np.empty(len(y), dtype=object)
        active = np.zeros(len(y), dtype=bool)
        for tr, te in folds:
            # Gate is calibrated only from quiet takes inside the training fold.
            gate = calibrate_gate(rms[tr][quiet[tr]], peak[tr][quiet[tr]], scale, args.gate_percentile)
            fit_rows = tr[gate.is_active(rms[tr], peak[tr])]
            model = fit_model(X[fit_rows], y[fit_rows])
            labels[te], active[te] = gated_predict(model, gate, X[te], rms[te], peak[te])
        metrics = frame_metrics(labels, active, data)
        print(f'\n=== gate scale {scale} (x quiet P{args.gate_percentile:g}) ===')
        print(f"active fraction {metrics['active_fraction']}  active-frame acc "
              f"{metrics['active_window_acc']}  recall n/k/r {metrics['active_recall']}")
        for stability in stability_grid():
            trials = simulate_trials(labels, data, stability, args.segment_s)
            mean_rate, min_rate = summarize(trials)
            results.append(dict(gate_scale=scale, k_frames=stability.k_frames, mean_pass=mean_rate,
                                min_pass=min_rate, trials=trials, **metrics))
            print(f"  K={stability.k_frames}  mean {mean_rate:.3f} min {min_rate:.3f}  " +
                  '  '.join(f"{t} {trials[t]['passed']}/{trials[t]['total']}" for t in TRIAL_TYPES))
    return results


def train(args):
    out_model, out_json = Path(args.out).with_suffix('.model'), Path(args.out).with_suffix('.json')
    if out_json.exists() and 'holdout' in json.loads(out_json.read_text(encoding='utf-8')):
        raise SystemExit(f'{out_json} already has a holdout result; use a new --out name.')
    data = load_split('train')
    results = cross_validate(data, args)
    best = max(results, key=lambda r: (r['mean_pass'], r['min_pass']))
    print(f"\nSelected by CV: gate scale {best['gate_scale']}, K {best['k_frames']}, "
          f"mean pass {best['mean_pass']}, min pass {best['min_pass']}")

    gate = calibrate_gate(data['rms_fs'][data['quiet']], data['peak_fs'][data['quiet']],
                          best['gate_scale'], args.gate_percentile)
    fit_rows = gate.is_active(data['rms_fs'], data['peak_fs'])
    model = fit_model(data['X'][fit_rows], data['y'][fit_rows])
    stability = StabilityConfig(k_frames=best['k_frames'], release_frames=RELEASE_FRAMES)

    out_model.parent.mkdir(parents=True, exist_ok=True)
    save_model(model, CLASS_NAMES, out_model)
    meta = dict(created_utc=datetime.now(timezone.utc).isoformat(), class_names=CLASS_NAMES,
                model_file=out_model.name, model=dict(model_type=MODEL_B_PIPELINE, max_hz=B_MAX_HZ, C=B_SVM_C),
                gate=dict(rms_fs=gate.rms_fs, peak_fs=gate.peak_fs, enabled=gate.enabled,
                          scale=best['gate_scale'], percentile=args.gate_percentile),
                stability=dict(k_frames=stability.k_frames, release_frames=stability.release_frames,
                               default_k=stability.default_k),
                training=dict(data=data['path'], sha256=data['sha256'], rows_total=int(len(data['y'])),
                              rows_fit=int(fit_rows.sum()),
                              rows_fit_per_class={c: int((data['y'][fit_rows] == i).sum())
                                                  for i, c in enumerate(CLASS_NAMES)}),
                cv=dict(n_splits=N_SPLITS, segment_s=args.segment_s, selected=best, all=results))
    out_json.write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print(f'Saved {out_model} and {out_json}')
    print(f'Gate: RMS > {100 * gate.rms_fs:.4f}% FS or peak > {100 * gate.peak_fs:.4f}% FS')


def eval_holdout(args):
    out_model, out_json = Path(args.out).with_suffix('.model'), Path(args.out).with_suffix('.json')
    meta = json.loads(out_json.read_text(encoding='utf-8'))
    if 'holdout' in meta:
        raise SystemExit('Holdout already evaluated for this model; do not tune on it.')
    model, classes = load_model(out_model)
    assert classes == CLASS_NAMES
    g = meta['gate']
    gate = GateConfig(g['rms_fs'], g['peak_fs'], g['enabled'])
    s = meta['stability']
    stability = StabilityConfig(k_frames=s['k_frames'], release_frames=s['release_frames'],
                                default_k=s['default_k'])
    data = load_split('holdout')
    labels, active = gated_predict(model, gate, data['X'], data['rms_fs'], data['peak_fs'])
    metrics = frame_metrics(labels, active, data)
    trials = simulate_trials(labels, data, stability, meta['cv']['segment_s'])
    meta['holdout'] = dict(evaluated_utc=datetime.now(timezone.utc).isoformat(), data=data['path'],
                           sha256=data['sha256'], trials=trials, **metrics)
    out_json.write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print(json.dumps(meta['holdout'], indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default='b_models/b_svm_v1', help='output path without extension')
    parser.add_argument('--gate-scales', type=float, nargs='+', default=[0.0, 1.0, 1.5, 2.0],
                        help='multiples of quiet percentile; 0 disables the gate')
    parser.add_argument('--gate-percentile', type=float, default=95.0)
    parser.add_argument('--segment-s', type=float, default=5.0, help='simulated trial length')
    parser.add_argument('--eval-holdout', action='store_true', help='evaluate saved model on holdout ONCE')
    args = parser.parse_args()
    eval_holdout(args) if args.eval_holdout else train(args)


if __name__ == '__main__':
    main()
