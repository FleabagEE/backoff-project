import unittest

import numpy as np

from event_segmentation import EventConfig, band_energy, calibrate, segment_events, event_decisions, inspect_session
from recording_policy import recording_plan, rhythm_phase
from collection import training_eligible


class EventTests(unittest.TestCase):
    def test_pilot_and_old_session_cannot_enter_final_event_inspection(self):
        for source in ('data_sessions/pilot_wood/20261019_130420_b7d74cb6',
                       'data_sessions/20261017_195725_85cb47b5'):
            with self.assertRaises(ValueError):
                inspect_session(source,'not_used','not_written.json')

    def test_band_uses_true_frequency_and_rejects_hum_and_above_8k(self):
        X = np.zeros((3,1200))
        X[0, 2] = 10  # 60 Hz
        X[1, 24] = 10  # 500 Hz
        X[2, 400] = 10  # 8020 Hz
        energy = band_energy(X)
        self.assertEqual(energy[0],0); self.assertGreater(energy[1],0); self.assertEqual(energy[2],0)

    def test_twelve_events_and_training_silence_is_dropped(self):
        t = np.arange(.025,25,.05); power = np.ones(len(t))
        for onset in np.arange(1,25,2):
            power[(t>=onset)&(t<onset+.25)] = 10
        config = EventConfig(2,4,2)
        result = segment_events(t,power,config)
        self.assertEqual(result['detected_events'],12)
        self.assertEqual(result['complete_events'],12)
        self.assertFalse(result['training_positive_mask'][power==1].any())
        self.assertTrue(result['training_positive_mask'][power==10].all())

    def test_tail_and_sustained_input_not_invented_as_multiple_events(self):
        t=np.arange(.025,10,.05); energy=np.ones(len(t));energy[(t>1)&(t<6)]=10
        energy[t>9.5]=10
        result=segment_events(t,energy,EventConfig(2,4,2))
        self.assertEqual(result['detected_events'],2)
        self.assertEqual(result['complete_events'],1)
        self.assertFalse(result['training_positive_mask'][t>9.5].any())

    def test_event_score_aggregation_is_per_event(self):
        t=np.arange(.025,5,.05); power=np.ones(len(t));power[(t>1)&(t<1.3)]=10
        result=segment_events(t,power,EventConfig(2,4,2))
        scores=np.zeros((len(t),3));scores[:,2]=1
        labels=event_decisions(t,scores,result['events'],['neutral','knock','rub'])
        self.assertEqual([r['label'] for r in labels],['rub'])

    def test_quiet_calibration_does_not_require_positive_or_test_data(self):
        config=calibrate(np.ones(100))
        self.assertEqual(config.gate_energy,1)
        self.assertGreater(config.onset_energy,config.gate_energy)
        with self.assertRaises(ValueError):calibrate([1])

    def test_wood_label_and_visual_cues(self):
        plan=recording_plan('take','train','rub','r01 scratch_nail_wood normal')
        self.assertTrue(training_eligible(plan))
        self.assertIn('GET READY',rhythm_phase(.5,'rub'))
        self.assertIn('1/12: SCRATCH NOW',rhythm_phase(1.1,'rub'))
        self.assertIn('STAY STILL',rhythm_phase(2.2,'rub'))
        self.assertIn('12/12: KNOCK ONCE',rhythm_phase(23.1,'knock'))


if __name__=='__main__':unittest.main()
