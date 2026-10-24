"""Fit the explicit 75+20 wood takes; preserve capture, v1, and B's decoder."""
import argparse
from collections import Counter
from dataclasses import asdict
import csv
import hashlib
import json
from pathlib import Path
import re

import joblib
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from event_segmentation import band_energy, calibrate
from models import EventDecoder, EventDecisionConfig
from train_wood_v3 import validate_take, fit_data, pipeline, metrics
from wood_v3_model import CLASS_NAMES, score_take

ORIGINAL = '20261019_135608_9c907587'
ADDITIONAL = '20261020_185237_766164bf'
ACTIONS = ('palm_slap', 'fingertip_tap', 'board_flick', 'phone_place',
           'phone_lift', 'cup_place', 'hand_rest', 'table_tap', 'typing', 'object_drag')


def validate_metadata(info, config):
    # Normalize a COPY for the v1 validator; never rewrite recording metadata.
    normalized = dict(info)
    normalized['variation'] = '_'.join(re.findall(r'[a-z0-9]+', info.get('variation', '').lower()))
    validate_take(normalized, config)
    if info.get('performer') != 'A':
        raise ValueError('Expected performer A')


def load_sources(root):
    root = Path(root).resolve()
    takes = []; seen = set(); configs = []
    for session in (ORIGINAL, ADDITIONAL):
        folder = root / session
        config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
        configs.append(config)
        for path in sorted(folder.glob('take_*.npz')):
            if '.excluded.' in path.name:
                raise ValueError('Unexpected excluded file: review source explicitly')
            with np.load(path, allow_pickle=False) as d:
                info = json.loads(str(d['metadata_json']))
                validate_metadata(info, config)
                if json.loads(str(d['config_json'])) != config:
                    raise ValueError('Embedded capture configuration mismatch')
                if info['take_id'] in seen:
                    raise ValueError('Duplicate take ID')
                seen.add(info['take_id'])
                X = d['X'].copy(); times = d['elapsed_s'].copy()
                if X.ndim != 2 or X.shape[1] != 1200 or times.shape != (len(X),) or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
                    raise ValueError('Invalid saved FFT features or timestamps')
                label = CLASS_NAMES.index(info['class_name'])
                quiet = session == ORIGINAL and label == 0
                if session == ADDITIONAL and (label != 0 or info['variation'] not in ['v3 neutral ' + a for a in ACTIONS]):
                    raise ValueError('Unexpected interference class/notes')
                takes.append(dict(info=info, X=X, times=times, energy=band_energy(X),
                    label=label, quiet=quiet, session=session, path=path, file=path.name,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    profile = ('setup_id', 'sample_rate', 'fft_window_samples', 'feature_count',
               'selected_channel_1_based', 'dtype', 'captured_channels', 'frames_per_capture_block',
               'feature_pipeline', 'preprocessing', 'smoothing_length_ms', 'host_api')
    if any(configs[0].get(k) != configs[1].get(k) for k in profile):
        raise ValueError('Different acquisition or feature profiles')
    original = Counter(t['label'] for t in takes if t['session'] == ORIGINAL)
    additional = Counter(t['info']['variation'] for t in takes if t['session'] == ADDITIONAL)
    if original != Counter({0:25, 1:25, 2:25}) or additional != Counter({'v3 neutral '+a:2 for a in ACTIONS}):
        raise ValueError(f'Expected exactly 75 original + 20 interference takes: {original}, {additional}')
    return takes


def quiet_detector(takes, indexes):
    energies = [takes[i]['energy'] for i in indexes if takes[i]['quiet']]
    if not energies:
        raise ValueError('No training-fold quiet calibration data')
    return calibrate(np.concatenate(energies))


def replay_decoder(scores, times, energy, gate):
    """Saved windows, fresh decoder per take, then GUI trial-stop flush (no padding)."""
    decoder = EventDecoder(EventDecisionConfig(trigger_energy=gate, vote_energy=gate))
    events = []; last = None
    for t, e, s in zip(times, energy, scores):
        decoder.step(float(t), float(e), s)
        if decoder.last_decision is not None and decoder.last_decision is not last:
            events.append(dict(decoder.last_decision)); last = decoder.last_decision
    decoder.flush(float(times[-1]))
    if decoder.last_decision is not None and decoder.last_decision is not last:
        events.append(dict(decoder.last_decision))
    emitted = [e['label'] for e in events if e['label'] != 'neutral']
    return emitted, events


def evaluate(model, takes, indexes, detector, fold):
    rows = []
    for i in indexes:
        t = takes[i]; result = score_take(model, t['X'], t['times'], detector)
        emitted, events = replay_decoder(model.decision_function(t['X']), t['times'], t['energy'], detector.gate_energy)
        expected = CLASS_NAMES[t['label']]
        passed = not emitted if expected == 'neutral' else bool(emitted) and set(emitted) == {expected}
        rows.append(dict(take_id=t['info']['take_id'], session=t['session'], fold=fold,
            class_name=expected, notes=t['info']['variation'], quiet=t['quiet'],
            predicted_class=CLASS_NAMES[result['take_label']],
            detected_events=result['view']['detected_events'], expected_events=1 if t['label'] else None,
            emitted=emitted, decoder_events=events, decoder_pass=passed,
            windows=len(t['X']), gated_windows=int((t['energy'] > detector.gate_energy).sum())))
    return rows


def summarize(rows):
    mean_metrics = metrics([CLASS_NAMES.index(r['class_name']) for r in rows],
                           [CLASS_NAMES.index(r['predicted_class']) for r in rows])
    by_class = {}
    for name in CLASS_NAMES:
        selected = [r for r in rows if r['class_name'] == name]
        by_class[name] = dict(takes=len(selected), passed=sum(r['decoder_pass'] for r in selected),
                             extra_outputs=sum(max(0,len(r['emitted'])-1) for r in selected))
    interference = [r for r in rows if r['session'] == ADDITIONAL]
    false = {name:sum(name in r['emitted'] for r in interference) for name in ('knock','rub')}
    decoder_matrix = np.zeros((3,4),dtype=int)
    for row in rows:
        unique=set(row['emitted'])
        predicted=0 if not unique else (CLASS_NAMES.index(next(iter(unique))) if len(unique)==1 else 3)
        decoder_matrix[CLASS_NAMES.index(row['class_name']),predicted] += 1
    return dict(mean_score_take_metrics=mean_metrics,
        B_decoder_confusion_columns=CLASS_NAMES+['mixed knock+rub'],
        B_decoder_confusion_matrix=decoder_matrix.tolist(),
        B_decoder_exactly_one_correct_action=sum(r['emitted']==[r['class_name']] for r in rows if r['class_name']!='neutral'),
        B_decoder_positive_takes=sum(r['class_name']!='neutral' for r in rows),
        B_decoder_trial_pass=sum(r['decoder_pass'] for r in rows), B_decoder_total=len(rows),
        B_decoder_by_class=by_class, interference_takes=len(interference),
        interference_false_trigger_takes=sum(bool(r['emitted']) for r in interference),
        interference_false_labels=false,
        interference_mean_score_predictions=dict(Counter(r['predicted_class'] for r in interference)))


def train(root, output, v1):
    takes = load_sources(root)
    output = Path(output)
    if output.exists():
        raise ValueError('Refuse to overwrite model artifacts')
    y = np.array([t['label'] for t in takes]); ids = np.array([t['info']['take_id'] for t in takes])
    rows = []; folds = []
    # Keep the already selected v1 classifier hyperparameters and <=8k cutoff.
    # No search on these 95 takes; scaler/model/quiet gate fit on training folds only.
    for number, (tr, te) in enumerate(StratifiedGroupKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)), y, ids)):
        assert not set(ids[tr]) & set(ids[te])
        detector = quiet_detector(takes, tr)
        X, labels, _ = fit_data(takes, tr, detector)
        model = pipeline(8000, .0003).fit(X, labels)
        current = evaluate(model, takes, te, detector, number); rows.extend(current)
        folds.append(dict(fold=number, train_ids=ids[tr].tolist(), test_ids=ids[te].tolist(),
            quiet_calibration_ids=[ids[i] for i in tr if takes[i]['quiet']], gate=asdict(detector),
            result=summarize(current)))
        print('FOLD', number, json.dumps(summarize(current)), flush=True)
    old_params = json.loads((Path(v1)/'decision_params.json').read_text(encoding='utf-8'))
    old_path = Path(v1)/'model.joblib'
    if hashlib.sha256(old_path.read_bytes()).hexdigest() != old_params['model_sha256']:
        raise ValueError('Invalid v1 model pair')
    detector = quiet_detector(takes, range(len(takes)))
    if detector.gate_energy != old_params['event_detector']['gate_energy']:
        raise ValueError('Quiet gate changed unexpectedly')
    baseline = evaluate(joblib.load(old_path), takes, [i for i,t in enumerate(takes) if t['session']==ADDITIONAL], detector, 'v1_new20')
    X, labels, selection = fit_data(takes, range(len(takes)), detector)
    model = pipeline(8000,.0003).fit(X,labels)
    for t in takes:
        if hashlib.sha256(t['path'].read_bytes()).hexdigest() != t['sha256']:
            raise RuntimeError('Raw take changed during fitting')
    output.mkdir(parents=True)
    joblib.dump(model, output/'model.joblib')
    params = dict(old_params)
    params.update(format_version=2, source_sessions=[str((Path(root)/s).resolve()) for s in (ORIGINAL,ADDITIONAL)],
        model_sha256=hashlib.sha256((output/'model.joblib').read_bytes()).hexdigest(),
        decision_status='PROVISIONAL: B event decoder unchanged; interference included; fresh live test pending',
        limitation='Only two takes per interference type, one performer/setup; CV is development evidence, no untouched live test.',
        live_event_decoder=asdict(EventDecisionConfig(trigger_energy=detector.gate_energy,vote_energy=detector.gate_energy)))
    params.pop('source_session',None)
    params['gate']=dict(params['gate'],calibration='P95 of original 25 confirmed-quiet neutral takes ONLY; interference excluded; identical to v1')
    (output/'decision_params.json').write_text(json.dumps(params,indent=2),encoding='utf-8')
    report=dict(counts=dict(Counter(CLASS_NAMES[t['label']] for t in takes)),
        actions=dict(Counter(t['info']['variation'] for t in takes if t['session']==ADDITIONAL)),
        raw_windows=sum(len(t['X']) for t in takes),fit_windows=len(labels),
        fit_windows_by_class=dict(Counter(CLASS_NAMES[int(i)] for i in labels)),
        policy='All neutral windows retained; quiet/outside-event knock/rub windows DROPPED. Original features unchanged.',
        validation='Five-fold take-grouped CV; fixed v1 cutoff 8000Hz / C=.0003. Training-fold original quiet ONLY calibrates gate. No windows from a held-out take used in fitting.',
        evaluation_limit='Mean-score take label and B majority-event trial-set pass are DIFFERENT metrics. Decoder resets per 2s take and flushes at take end, matching GUI trial stop, not uninterrupted live streaming. Multiple same-class outputs pass trial-set rule; extra_outputs reported separately. No independent per-window action annotations.',
        cross_validation=summarize(rows),folds=folds,cv_predictions=rows,
        v1_on_new_interference=summarize(baseline),v1_interference_predictions=baseline,
        v1_comparison_limit='v1 never trained on these 20 takes; v2 CV trains on other interference takes, so this is a development comparison, not a matched untouched test.',
        gate_unchanged=True,fresh_live_test=False,final_window_selection=selection,
        sources=[dict(session=t['session'],file=t['file'],sha256=t['sha256']) for t in takes])
    (output/'training_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (output/'take_cv_predictions.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['take_id','session','fold','class_name','notes','quiet','predicted_class','emitted','decoder_pass','detected_events','windows','gated_windows']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print('RESULT',json.dumps(report['cross_validation']),flush=True)
    print('V1_NEW20',json.dumps(report['v1_on_new_interference']),flush=True)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--v1',required=True)
    args=parser.parse_args()
    train(args.data_root,args.output,args.v1)
