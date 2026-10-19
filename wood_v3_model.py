"""Load the wooden-board model and matching decision parameters; no capture changes."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np

from event_segmentation import EventConfig, band_energy, segment_events

CLASS_NAMES=['neutral','knock','rub']


def event_view(times, energy, config):
    """Use observed portions of edge-clipped events in a 2s single-action take.

    Quiet-like/outside-event positive fit windows are dropped. Context is not
    padded, and missing events remain missing. These are energy-derived weak
    boundaries, not human-annotated per-window ground truth.
    """
    result=segment_events(times,energy,config)
    context=np.zeros(len(times),dtype=bool)
    for event in result['events']:
        context |= (times>=event['start_s']) & (times<=event['stop_s'])
    result['observed_context_mask']=context
    result['positive_mask']=context & (energy>config.gate_energy)
    return result


def score_take(model,X,times,config):
    energy=band_energy(X)
    view=event_view(times,energy,config)
    scores=model.decision_function(X)
    raw=model.predict(X)
    gated=raw.copy();gated[energy<=config.gate_energy]=0
    positive=view['positive_mask']
    take_label=int(np.argmax(scores[positive].mean(axis=0))) if positive.any() else 0
    events=[]
    for event in view['events']:
        select=(times>=event['start_s'])&(times<=event['stop_s'])&(energy>config.gate_energy)
        label=int(np.argmax(scores[select].mean(axis=0))) if select.any() else 0
        events.append(dict(event,label=CLASS_NAMES[label],active_windows=int(select.sum())))
    return dict(raw=raw,gated=gated,take_label=take_label,view=view,energy=energy,
                event_predictions=events,event_set=sorted({'neutral'}|{e['label'] for e in events}))


class WoodV3Model:
    def __init__(self,model_path,params_path):
        model_path=Path(model_path)
        self.params=json.loads(Path(params_path).read_text(encoding='utf-8'))
        if self.params['class_names']!=CLASS_NAMES:
            raise ValueError('Unexpected class order')
        if self.params.get('model_sha256') and hashlib.sha256(model_path.read_bytes()).hexdigest()!=self.params['model_sha256']:
            raise ValueError('Model and decision parameters do not match')
        self.model=joblib.load(model_path)
        if getattr(self.model,'n_features_in_',None)!=1200 or list(self.model.classes_)!=[0,1,2]:
            raise ValueError('Expected a three-class model with full 1200-feature input')
        self.event_config=EventConfig(**self.params['event_detector'])

    def predict_windows(self,X):
        X=np.asarray(X)
        energy=band_energy(X)
        active=(energy>self.event_config.gate_energy) if self.params.get('gate',{}).get('enabled',True) else np.ones(len(X),dtype=bool)
        labels=np.zeros(len(X),dtype=int)
        if active.any():
            labels[active]=self.model.predict(X[active])
        return labels

    def predict_take(self,X,elapsed_s):
        result=score_take(self.model,np.asarray(X),np.asarray(elapsed_s),self.event_config)
        return dict(predicted_class=CLASS_NAMES[result['take_label']],
                    predicted_set=result['event_set'],events=result['event_predictions'])


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True)
    parser.add_argument('--params',required=True)
    parser.add_argument('--take',required=True)
    args=parser.parse_args()
    predictor=WoodV3Model(args.model,args.params)
    with np.load(args.take,allow_pickle=False) as data:
        print(json.dumps(predictor.predict_take(data['X'],data['elapsed_s']),indent=2))
