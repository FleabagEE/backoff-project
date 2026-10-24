import unittest
from unittest.mock import patch
import numpy as np
from train_wood_v3_neutral20 import validate_metadata, quiet_detector, replay_decoder


class Neutral20Tests(unittest.TestCase):
    def setUp(self):
        self.config = dict(session_type='final',collection_protocol='single_action_2s',
            setup_id='A_wood30x30x6_v3_candidate2',sample_rate=48000,
            fft_window_samples=2400,feature_count=1200,selected_channel_1_based=2)
        self.info = dict(split='train',recording_kind='take',event_protocol='single_action_2s',
            valid=True,class_name='neutral',duration_s=2,performer='A',variation='v3 neutral palm_slap')

    def test_notes_with_spaces_accepted_without_rewriting_original(self):
        before=dict(self.info)
        validate_metadata(self.info,self.config)
        self.assertEqual(self.info,before)

    def test_reject_wrong_class_notes_diagnostic_and_wrong_channel(self):
        for changes in ({'class_name':'knock'}, {'recording_kind':'diagnostic'}, {'split':'holdout'}, {'valid':False}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_metadata(dict(self.info,**changes),self.config)
        with self.assertRaises(ValueError):
            validate_metadata(self.info,dict(self.config,selected_channel_1_based=1))

    def test_gate_excludes_interference_and_test_fold_quiet(self):
        takes=[dict(quiet=True,energy=np.array([1.,2.])),
               dict(quiet=False,energy=np.array([1e9])),
               dict(quiet=True,energy=np.array([999.]))]
        with patch('train_wood_v3_neutral20.calibrate',return_value='detector') as calibrate:
            self.assertEqual(quiet_detector(takes,[0,1]),'detector')
            np.testing.assert_array_equal(calibrate.call_args.args[0],[1.,2.])

    def test_neutral_majority_rejects_transient_knock(self):
        scores=np.array([[0.,3.,0.]]*2+[[3.,0.,0.]]*8)
        labels,events=replay_decoder(scores,np.arange(10)*.05,np.ones(10)*2.,1.)
        self.assertEqual(labels,[])
        self.assertEqual(events[-1]['label'],'neutral')

    def test_knock_and_rub_class_mapping_at_trial_flush(self):
        for index,label in ((1,'knock'),(2,'rub')):
            scores=np.zeros((8,3));scores[:,index]=3
            emitted,_=replay_decoder(scores,np.arange(8)*.05,np.ones(8)*2.,1.)
            self.assertEqual(emitted,[label])


if __name__=='__main__':
    unittest.main()
