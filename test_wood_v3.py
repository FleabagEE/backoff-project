from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np

from event_segmentation import EventConfig
from train_wood_v3 import validate_take,pipeline,metrics
from wood_v3_model import CLASS_NAMES,WoodV3Model,event_view


class WoodV3Tests(unittest.TestCase):
    def test_training_refuses_other_setup_holdout_and_note_mismatch(self):
        c=dict(session_type='final',collection_protocol='single_action_2s',
               setup_id='A_wood30x30x6_v3_candidate2',sample_rate=48000,
               fft_window_samples=2400,feature_count=1200,selected_channel_1_based=2)
        i=dict(split='train',recording_kind='take',event_protocol='single_action_2s',
               valid=True,class_name='rub',variation='rub_scratch_nail_wood',duration_s=2)
        validate_take(i,c)
        for changed in (dict(i,split='holdout'),dict(i,recording_kind='diagnostic'),
                        dict(i,variation='knock_medium'),dict(i,duration_s=25)):
            with self.assertRaises(ValueError):validate_take(changed,c)
        for changed in (dict(c,session_type='pilot'),dict(c,setup_id='old')):
            with self.assertRaises(ValueError):validate_take(i,changed)

    def test_short_take_clipped_context_keeps_only_observed_active_windows(self):
        t=np.arange(0,2,.05);energy=np.ones(len(t));energy[(t>=.05)&(t<.2)]=10
        view=event_view(t,energy,EventConfig(2,4,2))
        self.assertEqual(view['detected_events'],1)
        self.assertEqual(view['complete_events'],0)
        self.assertEqual(int(view['positive_mask'].sum()),3)
        self.assertFalse(view['positive_mask'][energy==1].any())
        empty=event_view(t,np.ones(len(t)),EventConfig(2,4,2))
        self.assertEqual(empty['detected_events'],0)
        self.assertFalse(empty['positive_mask'].any())

    def test_model_parameter_roundtrip_gate_and_hash_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);X=np.ones((6,1200));X[2:4,40:50]=20;X[4:6,100:120]=30
            model=pipeline(8000,.001).fit(X,[0,0,1,1,2,2])
            path=root/'model.joblib';joblib.dump(model,path)
            params=dict(class_names=CLASS_NAMES,model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        event_detector=asdict(EventConfig(1e30,2e30,1e30)),gate=dict(enabled=True))
            pp=root/'decision_params.json';pp.write_text(json.dumps(params))
            loaded=WoodV3Model(path,pp)
            np.testing.assert_array_equal(loaded.model.predict(X),model.predict(X))
            with patch.object(loaded.model,'predict',side_effect=AssertionError('quiet must skip model')):
                np.testing.assert_array_equal(loaded.predict_windows(X),np.zeros(6,dtype=int))
            loaded.params['gate']['enabled']=False
            np.testing.assert_array_equal(loaded.predict_windows(X),model.predict(X))
            params['model_sha256']='wrong';pp.write_text(json.dumps(params))
            with self.assertRaises(ValueError):WoodV3Model(path,pp)

    def test_confusion_class_order_and_scratch_neutral_rate(self):
        result=metrics([0,1,2,2],[0,1,0,2])
        self.assertEqual(result['confusion_matrix'],[[1,0,0],[0,1,0],[1,0,1]])
        self.assertEqual(result['scratch_to_neutral_fraction'],.5)


if __name__=='__main__':unittest.main()
