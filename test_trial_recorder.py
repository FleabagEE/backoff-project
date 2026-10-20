import unittest

from models import TrialRecorder


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def run_trial(recorder, trial_type, labels, practice=False):
    recorder.start(trial_type, practice=practice)
    for label in labels:
        recorder.add(label)
    return recorder.stop()


class TrialRecorderTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.rec = TrialRecorder(clock=self.clock)

    def test_positive_rules(self):
        self.assertTrue(run_trial(self.rec, 'knock_pos', ['neutral', 'knock', 'neutral'])['passed'])
        self.assertTrue(run_trial(self.rec, 'rub_pos', ['rub', 'rub'])['passed'])
        self.assertFalse(run_trial(self.rec, 'rub_pos', ['neutral', 'knock', 'rub'])['passed'])
        self.assertFalse(run_trial(self.rec, 'knock_pos', ['neutral'] * 5)['passed'])  # missed

    def test_negative_rules(self):
        self.assertTrue(run_trial(self.rec, 'knock_neg', ['neutral', 'rub', 'neutral'])['passed'])
        self.assertFalse(run_trial(self.rec, 'knock_neg', ['neutral', 'knock'])['passed'])
        self.assertTrue(run_trial(self.rec, 'rub_neg', ['neutral'])['passed'])

    def test_one_wrong_frame_fails_the_trial(self):
        labels = ['neutral'] * 50 + ['rub'] * 20 + ['knock'] + ['neutral'] * 50
        result = run_trial(self.rec, 'rub_pos', labels)
        self.assertFalse(result['passed'])
        self.assertEqual(result['label_set'], ['knock', 'neutral', 'rub'])
        self.assertEqual(result['n_frames'], 121)

    def test_empty_set_is_invalid_not_counted(self):
        result = run_trial(self.rec, 'knock_neg', [])
        self.assertFalse(result['valid'])
        self.assertIsNone(result['passed'])
        self.assertEqual(self.rec.tally['knock_neg'], [0, 0])

    def test_unexpected_label_and_forced_invalid(self):
        self.assertFalse(run_trial(self.rec, 'rub_neg', ['neutral', 'Knock'])['valid'])
        self.rec.start('knock_pos')
        self.rec.add('knock')
        result = self.rec.stop(invalid_reason='audio stopped')
        self.assertFalse(result['valid'])
        self.assertEqual(result['invalid_reason'], 'audio stopped')
        self.assertEqual(self.rec.tally['knock_pos'], [0, 0])

    def test_tally_practice_and_undo(self):
        run_trial(self.rec, 'knock_pos', ['knock'], practice=True)
        run_trial(self.rec, 'knock_pos', ['neutral', 'knock'])
        run_trial(self.rec, 'knock_pos', ['neutral'])
        self.assertEqual(self.rec.tally['knock_pos'], [1, 2])  # practice not counted
        undone = self.rec.undo_last()
        self.assertFalse(undone['passed'])
        self.assertEqual(self.rec.tally['knock_pos'], [1, 1])
        self.assertEqual(len(self.rec.history), 2)
        self.rec.reset_tally()
        self.assertEqual(self.rec.tally['knock_pos'], [0, 0])

    def test_labels_only_collected_while_active(self):
        self.rec.add('knock')  # before start: ignored
        result = run_trial(self.rec, 'knock_neg', ['neutral'])
        self.rec.add('knock')  # after stop: ignored
        self.assertTrue(result['passed'])
        self.assertEqual(result['labels'], ['neutral'])

    def test_duration_and_state_errors(self):
        self.rec.start('rub_pos')
        self.clock.now = 7.5
        self.rec.add('rub')
        with self.assertRaises(RuntimeError):
            self.rec.start('rub_pos')
        with self.assertRaises(RuntimeError):
            self.rec.undo_last()
        self.assertEqual(self.rec.stop()['duration_s'], 7.5)
        with self.assertRaises(RuntimeError):
            self.rec.stop()
        with self.assertRaises(ValueError):
            self.rec.start('knock+')  # old naming is rejected


if __name__ == '__main__':
    unittest.main()
