"""Audit final FFT takes and export separate train/holdout files without editing raw data."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from collection import atomic_npz

CLASSES = ['neutral', 'knock', 'rub']


def read_overrides(path):
    result = {}
    if path:
        with Path(path).open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                key = row['take_id']
                if key in result or row['split'] not in ('train', 'holdout') or not row['reason']:
                    raise ValueError('Duplicate or invalid split correction')
                result[key] = row
    return result


def load_takes(folder, overrides=None):
    folder = Path(folder)
    config = json.loads((folder/'config.json').read_text(encoding='utf-8'))
    if config.get('session_type') != 'final':
        raise ValueError('Final QA refuses pilot or unspecified sessions')
    overrides = overrides or {}
    takes = []
    seen_ids = set()
    for path in sorted(folder.glob('take_*.npz')):
        if '.excluded.' in path.name:
            continue
        with np.load(path, allow_pickle=False) as data:
            info = json.loads(str(data['metadata_json']))
            if not info.get('valid', True):
                continue
            if info['take_id'] in seen_ids:
                raise ValueError('Duplicate take IDs')
            seen_ids.add(info['take_id'])
            if info.get('recording_kind') in ('trial', 'diagnostic') or info.get('split') in ('trial', 'diagnostic'):
                continue
            if json.loads(str(data['config_json'])) != config:
                raise ValueError(f'Configuration mismatch: {path.name}')
            arrays = {k: data[k].copy() for k in ('X', 'elapsed_s', 'rms_fs', 'peak_fs')}
        X = arrays['X']
        if (X.ndim != 2 or X.shape[1] != config['feature_count'] or not len(X)
                or not np.isfinite(X).all() or (X < 0).any()):
            raise ValueError(f'Invalid amplitudes: {path.name}')
        for key in ('elapsed_s', 'rms_fs', 'peak_fs'):
            v = arrays[key]
            if v.shape != (len(X),) or not np.isfinite(v).all() or (v < 0).any():
                raise ValueError(f'Invalid {key}: {path.name}')
        if np.any(np.diff(arrays['elapsed_s']) <= 0):
            raise ValueError(f'Non-increasing timestamps: {path.name}')
        effective = dict(info, original_split=info.get('split', 'train'))
        if info['take_id'] in overrides:
            correction = overrides[info['take_id']]
            effective.update(split=correction['split'], split_correction_reason=correction['reason'])
        if effective.get('split') not in ('train', 'holdout') or info['class_name'] not in CLASSES:
            raise ValueError(f'Invalid class/split: {path.name}')
        # Interaction 2 has changed. Historical fingertip rub is never selected
        # for current training OR current holdout, regardless of its raw split.
        if info['class_name'] == 'rub' and not any(tag in info.get('variation', '') for tag in ('scratch_nail_paper', 'scratch_nail_wood')):
            continue
        takes.append(dict(info=effective, arrays=arrays, file=path.name,
                          source_session=str(folder), source_config=config,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    ids = [t['info']['take_id'] for t in takes]
    if len(ids) != len(set(ids)) or set(overrides) - seen_ids:
        raise ValueError('Duplicate take IDs or correction refers to missing/excluded take')
    if not takes:
        raise ValueError('No accepted takes')
    return config, takes


def stacked(takes):
    return (np.concatenate([t['arrays']['X'] for t in takes]),
            np.concatenate([np.full(len(t['arrays']['X']), CLASSES.index(t['info']['class_name'])) for t in takes]),
            np.concatenate([np.full(len(t['arrays']['X']), t['info']['take_id']) for t in takes]))


def baseline(takes):
    """Fixed QA recipe; preprocessing fitted inside each training fold only."""
    train = [t for t in takes if t['info']['split'] == 'train']
    holdout = [t for t in takes if t['info']['split'] == 'holdout']
    if not train:
        return dict(skipped='No training takes')
    X, y, groups = stacked(train)
    X = np.log1p(X)
    def model():
        return make_pipeline(StandardScaler(), LinearSVC(dual=False, max_iter=10000, random_state=0))
    def metrics(actual, predicted):
        return dict(confusion_matrix=confusion_matrix(actual, predicted, labels=range(3)).tolist(),
                    report=classification_report(actual, predicted, labels=range(3),
                                                 target_names=CLASSES, output_dict=True, zero_division=0))
    if len(np.unique(y)) < 2 or len(np.unique(groups)) < 2:
        return dict(skipped='Need multiple classes and training takes')
    cv_predictions = np.full(len(y), -1, dtype=int)
    folds = []
    for fit, test in GroupKFold(n_splits=min(5, len(np.unique(groups)))).split(X, y, groups):
        fit_ids, test_ids = sorted(set(groups[fit])), sorted(set(groups[test]))
        assert not set(fit_ids) & set(test_ids)
        if len(np.unique(y[fit])) < 2:
            return dict(skipped='A training fold lacks multiple classes')
        cv_predictions[test] = model().fit(X[fit], y[fit]).predict(X[test])
        folds.append(dict(fit_take_ids=fit_ids, test_take_ids=test_ids))
    result = dict(recipe='log1p(full original amplitudes) -> StandardScaler -> LinearSVC',
                  classes=CLASSES, folds=folds, grouped_cv=metrics(y, cv_predictions),
                  fitted_take_ids=sorted(set(groups)), note='Window QA only; not SPACE trial-set or stranger accuracy')
    if holdout:
        HX, hy, hg = stacked(holdout)
        assert not set(groups) & set(hg)
        pred = model().fit(X, y).predict(np.log1p(HX))
        result['holdout'] = metrics(hy, pred)
        result['holdout_take_ids'] = sorted(set(hg))
        result['holdout_prediction_sets'] = [dict(take_id=str(g), actual=CLASSES[int(hy[hg == g][0])],
                                                predicted_set=[CLASSES[i] for i in sorted(set(pred[hg == g]))])
                                             for g in sorted(set(hg))]
    return result


def audit(folder, output, overrides_path=None, scratch_sessions=(), exclusions_path=None):
    config, takes = load_takes(folder, read_overrides(overrides_path))
    sources = [dict(session=str(folder), config=config)]
    signature_keys = ('sample_rate', 'frames_per_capture_block', 'fft_window_ms', 'fft_window_samples',
                      'feature_count', 'selected_channel_1_based', 'dtype', 'feature_pipeline',
                      'smoothing_length_ms', 'target_feature_updates_per_second')
    for source in scratch_sessions:
        other_config, other = load_takes(source)
        if any(other_config.get(k) != config.get(k) for k in signature_keys):
            raise ValueError('Capture/feature profile differs between source sessions')
        if any(t['info']['class_name'] != 'rub' for t in other):
            raise ValueError('Scratch sessions must contain only the replacement rub class')
        takes.extend(other)
        sources.append(dict(session=str(source), config=other_config))
    if exclusions_path:
        with Path(exclusions_path).open(encoding='utf-8-sig', newline='') as handle:
            exclusions = {r['take_id']: r['reason'] for r in csv.DictReader(handle)}
        unknown = set(exclusions) - {t['info']['take_id'] for t in takes}
        if unknown:
            raise ValueError(f'Unknown explicit exclusion IDs: {unknown}')
        takes = [t for t in takes if t['info']['take_id'] not in exclusions]
    if len({t['info']['take_id'] for t in takes}) != len(takes):
        raise ValueError('Repeated source session or duplicate take ID')
    if scratch_sessions:
        config = dict(config, interaction_2='rub means scratch_nail_paper',
                      source_sessions=sources, setup_id='v2_composite_original_knock_neutral_new_paper_scratch')
    output = Path(output)
    # Never overwrite an earlier review/export: use a fresh output directory.
    output.mkdir(parents=True, exist_ok=False)
    quiet = [t['arrays']['rms_fs'] for t in takes if t['info']['split'] == 'train'
             and t['info']['class_name'] == 'neutral' and 'quiet' in t['info'].get('variation', '').lower()]
    threshold = float(np.percentile(np.concatenate(quiet), 95)) if quiet else None
    rows = []
    for t in takes:
        info, arrays = t['info'], t['arrays']
        rms = arrays['rms_fs']
        row = dict(take_id=info['take_id'], class_name=info['class_name'], split=info['split'],
                   original_split=info['original_split'], performer=info.get('performer', ''),
                   variation=info.get('variation', ''), rows=len(rms), duration_s=info.get('duration_s'),
                   source_session=t['source_session'],
                   friction_review=bool(info['class_name']=='neutral' and 'drag' in info.get('variation', '').lower()),
                   median_rms_fs=float(np.median(rms)), p10_rms_fs=float(np.percentile(rms, 10)),
                   max_peak_fs=float(np.max(arrays['peak_fs'])),
                   quiet_like_fraction=float(np.mean(rms <= threshold)) if threshold else None,
                   median_near_quiet=bool(np.median(rms) <= threshold) if threshold else None,
                   file=t['file'], sha256=t['sha256'])
        rows.append(row)
    with (output/'take_audit.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for split in ('train', 'holdout'):
        subset = [t for t in takes if t['info']['split'] == split]
        if not subset:
            continue
        X, y, ids = stacked(subset)
        atomic_npz(output/f'{split}.npz', X=X, y=y, class_names=np.array(CLASSES), take_ids=ids,
                   split=np.full(len(X), split),
                   **{key: np.concatenate([t['arrays'][key] for t in subset])
                      for key in ('elapsed_s', 'rms_fs', 'peak_fs')},
                   config_json=np.array(json.dumps(config)),
                   takes_json=np.array(json.dumps([t['info'] for t in subset])))
    counts = {s: dict(Counter(t['info']['class_name'] for t in takes if t['info']['split'] == s))
              for s in ('train', 'holdout')}
    report = dict(source_session=str(Path(folder)), additional_scratch_sessions=list(map(str,scratch_sessions)),
                  counts=counts, total_rows=sum(r['rows'] for r in rows),
                  quiet_p95_rms_fs=threshold, threshold_note='Descriptive quiet-like fraction; NOT a production gate',
                  short_takes=[r['take_id'] for r in rows if (r['duration_s'] or 0) < 24],
                  peak_at_or_above_70pct=[r['take_id'] for r in rows if r['max_peak_fs'] >= .7],
                  suspicious_rub=[r['take_id'] for r in rows if r['class_name']=='rub' and r['median_near_quiet']],
                  baseline=baseline(takes))
    (output/'qa_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    summary = ['# Final dataset QA', '', f'Source: `{folder}`', '',
               f'Takes: {counts}', f"Total feature rows: {report['total_rows']}",
               f'Quiet P95 RMS: {100*threshold:.4f}% FS (descriptive, not an energy gate)' if threshold else 'No quiet reference',
               f"Short takes (<24 s): {report['short_takes']}",
               f"Takes reaching 70% FS: {report['peak_at_or_above_70pct']}",
               f"Rub takes with median at/below quiet P95: {report['suspicious_rub']}", '',
               'Recipe: log1p amplitudes, StandardScaler, LinearSVC. GroupKFold by take;',
               'all preprocessing fits inside training folds. Holdout excluded from fitting/tuning.',
               'Full confusion matrices, per-class metrics and fold IDs: qa_report.json.', '',
               'Single performer A, one table, correlated windows. This is not a bakeoff trial-set test.',
               'Raw takes are untouched. Effective split corrections are recorded in the manifest.',
               'Use train.npz for fitting; holdout.npz for one final evaluation only.']
    for key in ('grouped_cv', 'holdout'):
        value = report['baseline'].get(key)
        if value:
            summary += ['', f"{key} window accuracy: {value['report'].get('accuracy', 0):.4f}",
                        'Confusion matrix rows=actual, columns=predicted; neutral, knock, rub:',
                        '```', str(np.array(value['confusion_matrix'])), '```']
    (output/'QA.md').write_text('\n'.join(summary)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('counts', 'total_rows', 'short_takes', 'suspicious_rub')}, indent=2))
    print(f'QA and separate datasets: {output}')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('--output', required=True, help='new directory; existing outputs are never overwritten')
    parser.add_argument('--overrides', help='CSV: take_id,split,reason; explicit reviewed corrections only')
    parser.add_argument('--scratch-session', action='append', default=[], help='additional final scratch-only session; repeat as needed')
    parser.add_argument('--exclusions', help='CSV: take_id,reason; preserve raw files but omit these takes')
    args = parser.parse_args()
    audit(args.session, args.output, args.overrides, args.scratch_session, args.exclusions)
