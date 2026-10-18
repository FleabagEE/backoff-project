"""Replay saved 8 s evaluation takes into label SETs. Not a training-data exporter."""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path

import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from recording_policy import TRIAL_TYPES


def score_trial(trial_type, labels):
    if trial_type not in TRIAL_TYPES:
        raise ValueError('Unknown trial_type')
    labels = set(labels)
    if not labels or not labels <= {'neutral','knock','rub'}:
        return False
    target, polarity = trial_type.split('_')
    return labels in ({target}, {'neutral',target}) if polarity == 'pos' else target not in labels


def resolve(spec):
    module, name = spec.split(':', 1)
    return getattr(importlib.import_module(module), name)


def identity_policy(label, rms_fs, peak_fs, elapsed_s, state):
    return label


def replay(sessions, output, baseline_train=None, adapter=None, model_path=None, policy=None):
    """Adapter factory(model_path)->predictor(X)->one label string per row.

    Policy(label,rms_fs,peak_fs,elapsed_s,state)->final label string. State is
    fresh for EACH trial. Policy and model are B's responsibility; default raw
    predictions are deliberately ungated for the QA demonstration.
    """
    if bool(baseline_train) == bool(adapter):
        raise ValueError('Select exactly one baseline_train or adapter')
    if Path(output).exists():
        raise FileExistsError(output)
    fit_ids = set()
    if baseline_train:
        with np.load(baseline_train, allow_pickle=False) as data:
            if not np.all(data['split'] == 'train'):
                raise ValueError('Baseline fitting accepts train-only export')
            names = data['class_names'].tolist()
            model = make_pipeline(StandardScaler(), LinearSVC(dual=False, random_state=0, max_iter=10000))
            model.fit(np.log1p(data['X']), data['y'])
            fit_ids = set(data['take_ids'])
        def factory(_):
            return lambda X: [names[int(i)] for i in model.predict(np.log1p(X))]
    else:
        factory = resolve(adapter)
    policy_fn = resolve(policy) if policy else identity_policy
    rows, seen = [], set()
    for folder in sessions:
        for path in sorted(Path(folder).glob('take_*.npz')):
            if '.excluded.' in path.name:
                continue
            with np.load(path, allow_pickle=False) as data:
                info = json.loads(str(data['metadata_json']))
                if info.get('recording_kind') != 'trial' or not info.get('valid', True):
                    continue
                if info.get('split') != 'trial' or info.get('trial_type') not in TRIAL_TYPES:
                    raise ValueError(f'Invalid trial metadata: {path}')
                take_id = info['take_id']
                if take_id in seen or take_id in fit_ids:
                    raise ValueError('Duplicate trial or evaluation data leaked into fitting')
                seen.add(take_id)
                X = data['X']
                if not len(X) or not np.isfinite(X).all() or info.get('duration_s',0) < 7.9:
                    raise ValueError(f'Incomplete/invalid trial: {path}')
                labels = list(factory(model_path)(X))
                if len(labels) != len(X):
                    raise ValueError('Predictor must return one class string per frame')
                state, final_labels = {}, []
                for label, rms, peak, elapsed in zip(labels,data['rms_fs'],data['peak_fs'],data['elapsed_s']):
                    final = policy_fn(str(label),float(rms),float(peak),float(elapsed),state)
                    if final not in ('neutral','knock','rub'):
                        raise ValueError('Policy must output neutral/knock/rub every frame')
                    final_labels.append(final)
                predicted_set = sorted(set(final_labels))
                rows.append(dict(take_id=take_id,trial_type=info['trial_type'],
                                 action_performed=info['action_performed'],predicted_set=predicted_set,
                                 passed=score_trial(info['trial_type'],predicted_set),
                                 duration_s=info['duration_s'],frames=len(X),source=str(path)))
    counts = Counter(r['trial_type'] for r in rows)
    report = dict(demonstration=bool(baseline_train),adapter=adapter,model_path=model_path,policy=policy,
                  trials=rows,counts=dict(counts),complete_20_trial_protocol=all(counts[k]==5 for k in TRIAL_TYPES),
                  passed=sum(r['passed'] for r in rows),total=len(rows),
                  note='Development evaluation for B gate/smoothing; not independent stranger validation.')
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    with Path(output).open('x',encoding='utf-8') as handle:
        json.dump(report,handle,indent=2)
    print(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sessions',nargs='+')
    parser.add_argument('--output',required=True)
    parser.add_argument('--baseline-train',help='QA-only demonstration, never a production model')
    parser.add_argument('--adapter',help='module:factory; factory(model_path)->predictor(X)->label strings')
    parser.add_argument('--model',dest='model_path')
    parser.add_argument('--policy',help='module:function; function(label,rms,peak,time,state)->label')
    args=parser.parse_args()
    replay(args.sessions,args.output,args.baseline_train,args.adapter,args.model_path,args.policy)
