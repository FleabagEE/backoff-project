"""Live bakeoff SPACE trial mode in the GUI, without audio hardware."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import dearpygui.dearpygui as dpg

from visualizer import App, BAKEOFF_LOCKED


class FakeSender:
    def __init__(self):
        self.labels = []

    def update(self, label):
        self.labels.append(label)

    def reset(self):
        pass


class BakeoffTrialGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        dpg.create_context()
        app = App.__new__(App)
        app.fast_takes = False; app.event_rhythm = False; app.record_key_held = False
        app.devices = {}; app.selected_device = None; app.session_type = 'final'; app.scratch_surface = 'wood'
        app.collected_data = {}; app.pending_take = None; app.pending_holdout = None
        app.is_recording = False; app.record_val = None; app.session = None
        app.ear = SimpleNamespace(stream_reader=SimpleNamespace(status_count=0))
        app.healthy = lambda: True
        app.model = object(); app.infer_classes = ['neutral', 'knock', 'rub']
        app.slide_sender = FakeSender()
        app.trial_log_root = Path(self.temp.name)
        app.build_ui()
        dpg.set_value('mode', 'Infer')
        self.app = app

    def tearDown(self):
        dpg.destroy_context()
        self.temp.cleanup()

    def press_space(self):
        self.app.space_shortcut()
        self.app.release_space_key()

    def run_trial(self, trial_type, labels, practice=False):
        dpg.set_value('bakeoff_trial_type', trial_type)
        dpg.set_value('bakeoff_practice', practice)
        self.press_space()
        for label in labels:
            self.app.publish_label(label)
        self.press_space()

    def log_records(self):
        return [json.loads(line) for line in self.app.trial_log_path.read_text(encoding='utf-8').splitlines()]

    def test_space_starts_locks_and_stops_with_pass(self):
        dpg.set_value('bakeoff_trial_type', 'knock_pos')
        self.press_space()
        self.assertTrue(self.app.trial.active)
        self.assertIn('RECORDING', dpg.get_value('bakeoff_state'))
        for tag in BAKEOFF_LOCKED:
            self.assertFalse(dpg.is_item_enabled(tag), tag)
        for label in ['neutral', 'knock', 'neutral']:
            self.app.publish_label(label)
        self.assertIn('{knock, neutral}', dpg.get_value('bakeoff_set'))
        self.press_space()
        self.assertFalse(self.app.trial.active)
        self.assertIn('knock_pos PASS', dpg.get_value('bakeoff_result'))
        self.assertIn('knock_pos 1/1', dpg.get_value('bakeoff_tally'))
        for tag in BAKEOFF_LOCKED:
            self.assertTrue(dpg.is_item_enabled(tag), tag)

    def test_same_label_goes_to_display_slides_and_trial(self):
        labels = ['neutral', 'knock', 'knock', 'rub', 'neutral']
        self.run_trial('rub_pos', labels)
        self.assertEqual(self.app.slide_sender.labels, labels)
        self.assertEqual(self.app.trial.history[-1]['labels'], labels)
        self.assertEqual(dpg.get_value('prediction'), 'Prediction: neutral')
        self.assertIn('rub_pos FAIL', dpg.get_value('bakeoff_result'))  # one knock frame fails rub_pos

    def test_holding_space_toggles_once(self):
        self.app.space_shortcut()
        self.app.space_shortcut()  # key repeat while held
        self.assertTrue(self.app.trial.active)
        self.app.release_space_key()
        self.press_space()
        self.assertFalse(self.app.trial.active)

    def test_space_ignored_in_train_mode_or_while_typing(self):
        dpg.set_value('mode', 'Train')
        self.press_space()
        self.assertFalse(self.app.trial.active)
        dpg.set_value('mode', 'Infer')
        with patch('visualizer.dpg.is_item_visible', return_value=True), \
                patch('visualizer.dpg.is_item_focused', side_effect=lambda tag: tag == 'variation'):
            self.press_space()
        self.assertFalse(self.app.trial.active)

    def test_click_button_uses_same_start_stop_and_log(self):
        callback=dpg.get_item_callback('bakeoff_toggle')
        dpg.run_callbacks([[callback,'bakeoff_toggle',None,None]])
        self.assertTrue(self.app.trial.active)
        self.assertEqual(dpg.get_item_configuration('bakeoff_toggle')['label'],'STOP TRIAL (SPACE)')
        self.app.publish_label('knock')
        dpg.run_callbacks([[callback,'bakeoff_toggle',None,None]])
        self.assertFalse(self.app.trial.active)
        self.assertTrue(self.app.trial.history[-1]['passed'])
        self.assertEqual(dpg.get_item_configuration('bakeoff_toggle')['label'],'START TRIAL (SPACE)')

    def test_polling_starts_stops_without_callbacks_and_does_not_repeat(self):
        with patch('visualizer.dpg.is_key_down',return_value=True):
            self.app.poll_space_key()
            self.app.poll_space_key()
        self.assertTrue(self.app.trial.active)
        self.app.publish_label('knock')
        with patch('visualizer.dpg.is_key_down',return_value=False):
            self.app.poll_space_key()
        with patch('visualizer.dpg.is_key_down',return_value=True):
            self.app.poll_space_key()
        self.assertFalse(self.app.trial.active)
        self.assertTrue(self.app.trial.history[-1]['passed'])

    def test_callback_and_poll_share_one_latch_and_hidden_fields_cannot_block(self):
        with patch('visualizer.dpg.is_item_visible',return_value=False), \
                patch('visualizer.dpg.is_item_focused',return_value=True):
            self.app.space_shortcut()
        with patch('visualizer.dpg.is_key_down',return_value=True):
            self.app.poll_space_key()
        self.assertTrue(self.app.trial.active)

    def test_requires_model_and_healthy_audio(self):
        self.app.model = None
        self.press_space()
        self.assertFalse(self.app.trial.active)
        self.app.model = object()
        self.app.healthy = lambda: False
        self.press_space()
        self.assertFalse(self.app.trial.active)

    def test_invalid_trials_are_shown_and_not_counted(self):
        self.run_trial('knock_neg', [])  # SPACE twice without frames
        self.assertIn('INVALID', dpg.get_value('bakeoff_result'))
        self.press_space()
        self.app.publish_label('neutral')
        self.app.ear.stream_reader.status_count = 3  # capture problem during the trial
        self.press_space()
        self.assertIn('INVALID', dpg.get_value('bakeoff_result'))
        self.assertIn('total 0/0', dpg.get_value('bakeoff_tally'))

    def test_practice_undo_reset_and_log(self):
        self.run_trial('knock_pos', ['knock'], practice=True)
        self.assertIn('practice, not counted', dpg.get_value('bakeoff_result'))
        self.run_trial('knock_pos', ['neutral', 'knock'])
        self.run_trial('knock_neg', ['neutral', 'knock'])
        self.assertIn('total 1/2', dpg.get_value('bakeoff_tally'))
        self.app.undo_bakeoff_trial()
        self.assertIn('total 1/1', dpg.get_value('bakeoff_tally'))
        self.app.reset_bakeoff_tally()
        self.assertIn('total 0/0', dpg.get_value('bakeoff_tally'))
        events = [r['event'] for r in self.log_records()]
        self.assertEqual(events, ['trial', 'trial', 'trial', 'undo', 'reset_tally'])
        first = self.log_records()[0]
        self.assertEqual((first['trial_type'], first['practice'], first['labels']), ('knock_pos', True, ['knock']))
        self.assertTrue(str(self.app.trial_log_path).startswith(self.temp.name))

    def test_mode_change_or_fault_invalidates_running_trial(self):
        self.press_space()
        self.app.publish_label('knock')
        self.app.stop_bakeoff_trial(invalid_reason='Audio stopped or stale')
        self.assertFalse(self.app.trial.history[-1]['valid'])
        self.assertIn('Audio stopped', dpg.get_value('bakeoff_result'))


if __name__ == '__main__':
    unittest.main()
