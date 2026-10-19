"""Train-only cutoff comparison and B-gate diagnostics BEFORE joint tuning.

No holdout evaluation, capture, data edits or model saving. Repeat after actual
development trials exist to obtain event-window and fixed-setting trial results.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parent/'src'))
from models import LogSpectrum, Decoder, StabilityConfig
from qa_dataset import load_takes, read_overrides, stacked, CLASSES
from trial_replay import score_trial


def gate_statistics(rms, peak, rms_threshold, peak_threshold):
    rms=np.asarray(rms); peak=np.asarray(peak)
    rms_fail=rms <= rms_threshold
    peak_fail=peak <= peak_threshold
    return dict(windows=len(rms),rms_fail_fraction=float(rms_fail.mean()),
                peak_fail_fraction=float(peak_fail.mean()),
                both_fail_gate_inactive_fraction=float((rms_fail & peak_fail).mean()),
                median_rms_fs=float(np.median(rms)),p10_rms_fs=float(np.percentile(rms,10)))


def active_runs(mask):
    runs=[]; length=0
    for active in mask:
        if active:
            length+=1
        elif length:
            runs.append(length); length=0
    if length:
        runs.append(length)
    return runs


def make_model(cutoff):
    return make_pipeline(LogSpectrum(max_hz=cutoff),StandardScaler(),
                         LinearSVC(C=.001,class_weight='balanced',max_iter=20000,
                                   dual='auto',random_state=1))


def masks(takes):
    quiet=np.concatenate([np.full(len(t['arrays']['X']),t['info']['class_name']=='neutral'
                                  and t['info'].get('variation','').startswith('quiet hands off')) for t in takes])
    rms=np.concatenate([t['arrays']['rms_fs'] for t in takes])
    peak=np.concatenate([t['arrays']['peak_fs'] for t in takes])
    return quiet,rms,peak


def diagnose(old_session,scratch_sessions,overrides,exclusions,output,trial_sessions=()):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    _,old=load_takes(old_session,read_overrides(overrides))
    # Holdout is NEVER scored or used for threshold/model selection here.
    takes=[t for t in old if t['info']['split']=='train']
    excluded=set()
    with Path(exclusions).open(encoding='utf-8-sig') as f:
        excluded={r['take_id'] for r in csv.DictReader(f)}
    for folder in scratch_sessions:
        _,scratch=load_takes(folder)
        takes.extend(t for t in scratch if t['info']['split']=='train'
                     and t['info']['class_name']=='rub' and t['info']['take_id'] not in excluded)
    ids=[t['info']['take_id'] for t in takes]
    if len(ids)!=len(set(ids)):
        raise ValueError('Repeated source/take')
    meta=json.loads(Path('b_models/b_svm_v1.json').read_text(encoding='utf-8'))
    g=meta['gate']; rt,pt=g['rms_fs'],g['peak_fs']
    trials=[]
    for folder in trial_sessions:
        for p in sorted(Path(folder).glob('take_*.npz')):
            if '.excluded.' in p.name: continue
            with np.load(p,allow_pickle=False) as d:
                info=json.loads(str(d['metadata_json']))
                if info.get('recording_kind')!='trial' or not info.get('valid',True): continue
                if info.get('evaluation_role')=='fresh_test':
                    raise ValueError('Do not use untouched final trials for diagnostics/tuning')
                trials.append(dict(info=info,arrays={k:d[k].copy() for k in
                                                     ('X','rms_fs','peak_fs','elapsed_s')}))
    scratch_stats=[]
    for t in takes:
        if t['info']['class_name']=='rub':
            a=t['arrays']
            scratch_stats.append(dict(take_id=t['info']['take_id'],variation=t['info']['variation'],
                                      **gate_statistics(a['rms_fs'],a['peak_fs'],rt,pt)))
    _,rms,peak=masks([t for t in takes if t['info']['class_name']=='rub'])
    trial_stats=[]
    for t in trials:
        info,a=t['info'],t['arrays']; tm=a['elapsed_s']
        active=(a['rms_fs']>rt)|(a['peak_fs']>pt)
        run=active_runs(active)
        # Report whole-trial statistics and prescribed action interval separately:
        # six seconds of intended silence must not be called a missed scratch.
        action=(tm>=2)&(tm<3)
        trial_stats.append(dict(take_id=info['take_id'],trial_type=info['trial_type'],
                               all_windows=gate_statistics(a['rms_fs'],a['peak_fs'],rt,pt),
                               action_2_to_3s=gate_statistics(a['rms_fs'][action],a['peak_fs'][action],rt,pt)
                               if action.any() else None,
                               active_run_lengths=run,max_consecutive_active=max(run,default=0)))
    results=[]; fold_records=[]
    for drag_policy in ('include','exclude'):
        subset=[t for t in takes if not (drag_policy=='exclude' and t['info']['class_name']=='neutral'
                                        and 'drag' in t['info'].get('variation','').lower())]
        X,y,groups=stacked(subset); quiet,rms_all,peak_all=masks(subset)
        folds=list(GroupKFold(n_splits=5).split(X,y,groups))
        fold_plan=[]
        for tr,te in folds:
            q=rms_all[tr][quiet[tr]]
            if not len(q): raise ValueError('No quiet reference in a training fold')
            threshold=float(np.percentile(q,95))
            # Only positive quiet-like training windows are removed. Neutral data
            # is retained. Threshold is recalibrated INSIDE each training fold.
            keep=(y[tr]==0)|(rms_all[tr]>threshold)
            fit=tr[keep]
            if len(set(y[fit]))!=3: raise ValueError('Cleaning removed a class')
            fold_plan.append((fit,te))
            fold_records.append(dict(drag_policy=drag_policy,quiet_p95_rms_fs=threshold,
                                     fit_take_ids=sorted(set(groups[fit])),test_take_ids=sorted(set(groups[te])),
                                     rows_dropped=int(len(tr)-len(fit))))
        for cutoff in (8000,12000,16000,None):
            predictions=np.empty(len(y),dtype=int)
            for fit,te in fold_plan:
                assert not set(groups[fit])&set(groups[te])
                predictions[te]=make_model(cutoff).fit(X[fit],y[fit]).predict(X[te])
            gated=predictions.copy()
            gated[(rms_all<=rt)&(peak_all<=pt)]=0
            row=dict(drag_policy=drag_policy,cutoff_hz=cutoff,features_kept=1200 if cutoff is None else cutoff//20,
                     accuracy=float(accuracy_score(y,predictions)),
                     balanced_accuracy=float(balanced_accuracy_score(y,predictions)),
                     macro_f1=float(f1_score(y,predictions,average='macro')),
                     recall=recall_score(y,predictions,labels=[0,1,2],average=None).tolist(),
                     fixed_B_gate_accuracy=float(accuracy_score(y,gated)))
            if trials:
                threshold=float(np.percentile(rms_all[quiet],95))
                keep=(y==0)|(rms_all>threshold)
                model=make_model(cutoff).fit(X[keep],y[keep])
                scored=[]
                for t in trials:
                    a=t['arrays']; active=(a['rms_fs']>rt)|(a['peak_fs']>pt)
                    raw=np.full(len(a['X']),'neutral',dtype=object)
                    if active.any(): raw[active]=np.array(CLASSES)[model.predict(a['X'][active])]
                    decoder=Decoder(StabilityConfig(**meta['stability']))
                    seen=set(decoder.step(label) for label in raw)
                    scored.append(dict(take_id=t['info']['take_id'],trial_type=t['info']['trial_type'],
                                       predicted_set=sorted(seen),passed=score_trial(t['info']['trial_type'],seen)))
                row['fixed_B_decision_trials']=scored
                row['trial_passed']=sum(r['passed'] for r in scored)
            results.append(row)
            print(json.dumps(row),flush=True)
    report=dict(training_counts=dict(Counter(t['info']['class_name'] for t in takes)),
                B_gate=g,scratch_train=gate_statistics(rms,peak,rt,pt),scratch_per_take=scratch_stats,
                cutoff_results=results,folds=fold_records,trial_diagnostics=trial_stats,
                trial_counts=dict(Counter(t['info']['trial_type'] for t in trials)),
                holdout_evaluated=False,joint_grid_search_run=False,
                method='Five-fold GroupKFold by take; same folds within drag policy; neutral retained; positive training RMS<=fold quiet P95 dropped; B classifier C=.001 unchanged. Raw window metrics primary; fixed B gate secondary.',
                caveat='Take labels cover continuous action plus gaps. Window CV is not SET trial validation. Cutoff is applied to existing weighted/smoothed FFT amplitudes, not raw acoustic energy.')
    (output/'diagnostics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (output/'scratch_gate_by_take.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(scratch_stats[0]));writer.writeheader();writer.writerows(scratch_stats)
    print('Scratch train gate:',json.dumps(report['scratch_train']))
    print('Actual trials:',report['trial_counts'],'Holdout evaluated: False. Full grid: NOT run.')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old-session',default='data_sessions/20261017_195725_85cb47b5')
    p.add_argument('--scratch-session',action='append',required=True)
    p.add_argument('--overrides',default='docs/final_split_corrections.csv')
    p.add_argument('--exclusions',default='docs/final_v2_exclusions.csv')
    p.add_argument('--trial-session',action='append',default=[])
    p.add_argument('--output',required=True)
    a=p.parse_args()
    diagnose(a.old_session,a.scratch_session,a.overrides,a.exclusions,a.output,a.trial_session)
