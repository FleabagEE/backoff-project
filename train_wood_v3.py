"""Train only one explicit new-board final_v3 session; no old data/holdout scoring."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
import csv
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score,balanced_accuracy_score,confusion_matrix,f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from event_segmentation import band_energy,calibrate
from models import LogSpectrum
from wood_v3_model import CLASS_NAMES,event_view,score_take


def validate_take(info,config):
    if config.get('session_type')!='final' or config.get('collection_protocol')!='single_action_2s':
        raise ValueError('Only new final single-action 2s session is eligible')
    if config.get('setup_id')!='A_wood30x30x6_v3_candidate2':
        raise ValueError('Different hardware setup')
    if (config.get('sample_rate'),config.get('fft_window_samples'),config.get('feature_count'),config.get('selected_channel_1_based'))!=(48000,2400,1200,2):
        raise ValueError('Capture/FFT profile mismatch')
    if (info.get('split'),info.get('recording_kind'),info.get('event_protocol'),info.get('valid'))!=('train','take','single_action_2s',True):
        raise ValueError('Expected a valid training take, never holdout/trial/pilot/diagnostic')
    if info.get('class_name') not in CLASS_NAMES or not 1.9<=info.get('duration_s',0)<=2.2:
        raise ValueError('Unexpected class or take duration')
    name=info['class_name'];note=info.get('variation','').lower()
    if name not in note.split('_') or (name=='rub' and 'scratch_nail_wood' not in note):
        raise ValueError('Class/notes mismatch')


def load_session(folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(Path('data_sessions/final_v3').resolve()):
        raise ValueError('Source must be one explicit final_v3 session; no old or pilot sources')
    config=json.loads((folder/'config.json').read_text(encoding='utf-8'))
    takes=[];seen=set()
    for p in sorted(folder.glob('take_*.npz')):
        if '.excluded.' in p.name:continue
        with np.load(p,allow_pickle=False) as d:
            info=json.loads(str(d['metadata_json']))
            if info.get('split')!='train':continue
            validate_take(info,config)
            if json.loads(str(d['config_json']))!=config:raise ValueError('Mixed capture configurations')
            X=d['X'].copy();times=d['elapsed_s'].copy()
            if X.ndim!=2 or X.shape[1]!=1200 or len(times)!=len(X) or np.any(np.diff(times)<=0):
                raise ValueError('Invalid feature/timestamp shape or cadence')
            if info['take_id'] in seen:raise ValueError('Duplicate take ID')
            seen.add(info['take_id'])
            takes.append(dict(info=info,X=X,times=times,energy=band_energy(X),
                              rms=d['rms_fs'].copy(),peak=d['peak_fs'].copy(),
                              label=CLASS_NAMES.index(info['class_name']),file=p.name,
                              sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    if set(t['label'] for t in takes)!={0,1,2}:raise ValueError('All three classes required')
    return config,takes


def fit_data(takes,indexes,detector):
    features=[];labels=[];summary=[]
    for i in indexes:
        t=takes[i]
        if t['label']==0:
            select=np.ones(len(t['X']),dtype=bool);count=0
        else:
            view=event_view(t['times'],t['energy'],detector)
            select=view['positive_mask'];count=view['detected_events']
        features.append(t['X'][select]);labels.extend([t['label']]*int(select.sum()))
        summary.append(dict(take_id=t['info']['take_id'],class_name=CLASS_NAMES[t['label']],
                            retained=int(select.sum()),dropped=int((~select).sum()),detected_events=count))
    if set(labels)!={0,1,2}:raise ValueError('Energy cleaning removed a class; stop rather than fabricate training samples')
    return np.concatenate(features),np.array(labels),summary


def pipeline(cutoff,C):
    return make_pipeline(LogSpectrum(max_hz=cutoff),StandardScaler(),
                         LinearSVC(C=C,class_weight='balanced',dual='auto',max_iter=20000,random_state=42))


def metrics(y,pred):
    y=np.asarray(y);pred=np.asarray(pred)
    return dict(accuracy=float(accuracy_score(y,pred)),balanced_accuracy=float(balanced_accuracy_score(y,pred)),
                macro_f1=float(f1_score(y,pred,labels=[0,1,2],average='macro',zero_division=0)),
                confusion_matrix=confusion_matrix(y,pred,labels=[0,1,2]).tolist(),
                scratch_to_neutral_fraction=float(np.mean(pred[y==2]==0)) if np.any(y==2) else None)


def train(source,output,neutral_quiet_confirmed=False):
    if not neutral_quiet_confirmed:
        raise ValueError('This run requires operator confirmation that neutral takes are all quiet')
    config,takes=load_session(source)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    take_y=np.array([t['label'] for t in takes]);take_ids=np.array([t['info']['take_id'] for t in takes])
    counts=Counter(CLASS_NAMES[t['label']] for t in takes)
    fold_plan=[]
    splitter=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42)
    for tr,te in splitter.split(np.zeros(len(takes)),take_y,take_ids):
        assert not set(take_ids[tr])&set(take_ids[te])
        quiet=np.concatenate([takes[i]['energy'] for i in tr if takes[i]['label']==0])
        detector=calibrate(quiet)
        X,y,summary=fit_data(takes,tr,detector)
        fold_plan.append(dict(train=tr,test=te,X=X,y=y,detector=detector,selection=summary))
    results=[];detail={}
    for cutoff in (8000,12000,16000,None):
        for C in (.0003,.001,.003,.01):
            ref=[];raw=[];gated=[];recorded_ref=[];event_y=[];event_pred=[];take_rows=[];fold_rows=[]
            for number,fold in enumerate(fold_plan):
                model=pipeline(cutoff,C).fit(fold['X'],fold['y'])
                fold_truth=[];fold_prediction=[]
                for i in fold['test']:
                    t=takes[i];r=score_take(model,t['X'],t['times'],fold['detector'])
                    # Secondary energy-derived weak labels, NOT independent ground truth.
                    labels=np.where(r['view']['positive_mask'],t['label'],0) if t['label'] else np.zeros(len(t['X']),int)
                    ref.extend(labels);raw.extend(r['raw']);gated.extend(r['gated'])
                    recorded_ref.extend([t['label']]*len(t['X']))
                    event_y.append(t['label']);event_pred.append(r['take_label'])
                    fold_truth.append(t['label']);fold_prediction.append(r['take_label'])
                    take_rows.append(dict(take_id=t['info']['take_id'],fold=number,class_name=CLASS_NAMES[t['label']],
                        predicted_class=CLASS_NAMES[r['take_label']],windows=len(t['X']),
                        detected_events=r['view']['detected_events'],expected_events=t['info'].get('expected_events'),
                        event_active_windows=int(r['view']['positive_mask'].sum()),
                        event_set=r['event_set'],events=r['event_predictions']))
                fold_rows.append(dict(fold=number,training_take_ids=take_ids[fold['train']].tolist(),
                    test_take_ids=take_ids[fold['test']].tolist(),quiet_gate=asdict(fold['detector']),
                    take_metrics=metrics(fold_truth,fold_prediction),fit_rows=int(len(fold['y']))))
            row=dict(cutoff_hz=cutoff,C=C,take_metrics=metrics(event_y,event_pred),
                     weak_window_no_gate=metrics(ref,raw),weak_window_gate=metrics(ref,gated),
                     recorded_take_label_windows_no_gate=metrics(recorded_ref,raw),
                     recorded_take_label_windows_gate=metrics(recorded_ref,gated))
            results.append(row);detail[(cutoff,C)]=dict(folds=fold_rows,takes=take_rows)
            print(json.dumps(dict(cutoff_hz=cutoff,C=C,take_accuracy=row['take_metrics']['accuracy'],
                                  take_scratch_to_neutral=row['take_metrics']['scratch_to_neutral_fraction'])),flush=True)
    # Primary target is independent take label, not gate-defined window truth.
    selected=max(results,key=lambda r:(r['take_metrics']['accuracy'],r['take_metrics']['macro_f1'],
                                      r['weak_window_no_gate']['macro_f1'],-r['C'],
                                      -(r['cutoff_hz'] or 24000)))
    quiet=np.concatenate([t['energy'] for t in takes if t['label']==0]);detector=calibrate(quiet)
    X,y,selection=fit_data(takes,np.arange(len(takes)),detector)
    final=pipeline(selected['cutoff_hz'],selected['C']).fit(X,y)
    model_path=output/'model.joblib';joblib.dump(final,model_path)
    params=dict(format_version=1,setup_id=config['setup_id'],source_session=str(Path(source).resolve()),
        class_names=CLASS_NAMES,model_file='model.joblib',model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        sample_rate=48000,fft_samples=2400,input_features=1200,cutoff_hz=selected['cutoff_hz'],C=selected['C'],
        gate=dict(type='0.5-8 kHz deweighted smoothed FFT energy proxy',enabled=True,threshold=detector.gate_energy,
                  calibration='P95 of all NEW neutral (operator-confirmed quiet) training windows'),
        event_detector=asdict(detector),smoothing=dict(N=1,K_knock=1,K_rub=1,neutral_release=1),cooldown_s=0,
        decision_status='PROVISIONAL: window gate and event-mean outputs available; no development-trial temporal tuning',
        limitation='Only quiet neutral, one performer/session, no adversarial validation or untouched holdout/test yet.')
    (output/'decision_params.json').write_text(json.dumps(params,indent=2),encoding='utf-8')
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_session=str(Path(source).resolve()),
        setup_id=config['setup_id'],counts=dict(counts),raw_windows=sum(len(t['X']) for t in takes),
        fit_windows=len(y),fit_windows_by_class=dict(Counter(CLASS_NAMES[i] for i in y)),
        selection_metric='five-fold take-grouped CV take-label accuracy; ties macro F1 then weak-window macro F1; selection CV is not untouched evaluation',
        selected=selected,grid=results,selected_details=detail[(selected['cutoff_hz'],selected['C'])],
        final_window_selection=selection,all_neutral_confirmed_quiet=True,
        weak_window_label_warning='Quiet-like/outside-event windows in positive takes labelled neutral by training-fold quiet energy. Gated accuracy against these weak labels is partly circular; do not claim it as independent window ground truth. Recorded take-label metrics also include genuine quiet gaps as positives. Independent take labels and missing-event counts are primary.',
        holdout_evaluated=False,development_trials_evaluated=0,fresh_tests_evaluated=0,
        raw_take_hashes=[dict(file=t['file'],sha256=t['sha256']) for t in takes])
    (output/'training_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (output/'take_cv_predictions.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['take_id','fold','class_name','predicted_class','windows','detected_events','expected_events','event_active_windows','event_set']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for r in report['selected_details']['takes']:writer.writerow(r)
    # Refuse silent source changes during fitting. No data file is written here.
    for t in takes:
        if hashlib.sha256((Path(source)/t['file']).read_bytes()).hexdigest()!=t['sha256']:
            raise RuntimeError('Source changed while training; review before using artifacts')
    print('SELECTED',json.dumps(selected),flush=True)
    print('ARTIFACTS',str(output.resolve()),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--output',required=True)
    parser.add_argument('--neutral-quiet-confirmed',action='store_true')
    args=parser.parse_args()
    train(args.source,args.output,args.neutral_quiet_confirmed)
