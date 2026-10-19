"""Real GUI-widget recording tests with synthetic input; no microphone capture."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import numpy as np

from collection import CollectionSession
from recording_policy import fast_take_warnings, single_action_phase
from visualizer import App


class FastTakeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        dpg.create_context()
        app=App.__new__(App)
        app.fast_takes=True;app.event_rhythm=False;app.record_key_held=False
        app.devices={};app.selected_device=None;app.session_type='final';app.scratch_surface='wood'
        app.collected_data={};app.pending_take=None;app.pending_holdout=None
        app.is_recording=False;app.record_val=None;app.unsaved=False
        app.take_counts={split:dict(knock=0,rub=0,neutral=0) for split in ('train','holdout')}
        app.trial_counts={}
        app.ear=SimpleNamespace(stream_reader=SimpleNamespace(status_count=0))
        app.healthy=lambda:True
        app.session_root=self.temp.name
        app.session=CollectionSession(dict(feature_count=4,session_type='final'),self.temp.name)
        app.build_ui()
        for name in ('knock','rub','neutral'):app.add_class(name)
        self.app=app

    def tearDown(self):
        dpg.destroy_context();self.temp.cleanup()

    def prepare(self,split='train'):
        dpg.set_value('split',split)
        dpg.set_value('variation','knock_medium_right_center')
        self.app.select_class('knock')

    def finish(self):
        self.app.frames=[np.ones(4),np.ones(4)]
        self.app.times=[.05,1.95];self.app.rms=[.001,.002];self.app.peaks=[.005,.02]
        with patch('visualizer.time.monotonic',return_value=102.01):
            self.assertFalse(self.app.recording_tick(1.99))
            self.assertTrue(self.app.recording_tick(2.01))

    def test_launch_defaults_and_full_preflight(self):
        self.assertEqual(dpg.get_value('recording_kind'),'take')
        self.assertEqual(dpg.get_value('split'),'train')
        self.assertEqual(dpg.get_value('take_limit'),2)
        self.assertEqual(dpg.get_value('performer'),'A')
        self.prepare()
        self.assertEqual(self.app.refresh_fast_panel(),[])
        summary=dpg.get_value('preflight_summary')
        self.assertIn(str(self.app.session.path.resolve()),summary)
        self.assertIn('knock_medium_right_center',summary)
        self.assertIn('Length: 2s',summary)
        self.assertEqual(self.app.session.take_paths(),[])

    def test_r_autostops_saves_distinct_files_and_preserves_notes(self):
        self.prepare()
        for index in range(2):
            self.app.release_record_key()
            with patch('visualizer.time.monotonic',return_value=100):
                self.app.record_shortcut()
            self.assertTrue(self.app.is_recording)
            self.app.record_shortcut()  # Held/repeated R cannot stop the take.
            self.assertTrue(self.app.is_recording)
            self.assertEqual(self.app.take_notes['expected_events'],1)
            self.assertEqual(self.app.take_notes['event_protocol'],'single_action_2s')
            self.finish()
            self.assertFalse(self.app.is_recording)
            self.assertEqual(len(self.app.session.take_paths()),index+1)
            self.assertEqual(dpg.get_value('variation'),'knock_medium_right_center')
        for path in self.app.session.take_paths():
            with np.load(path,allow_pickle=False) as data:
                info=json.loads(str(data['metadata_json']))
                self.assertTrue(info['valid']);self.assertEqual(info['requested_take_s'],2)
                self.assertEqual(info['class_name'],'knock');self.assertEqual(info['split'],'train')
        self.assertEqual(self.app.take_counts['train']['knock'],2)
        self.assertIn('train 2',dpg.get_value('fast_count_knock'))

    def test_typing_r_in_notes_does_not_record(self):
        self.prepare()
        with patch('visualizer.dpg.is_item_focused',side_effect=lambda tag:tag=='variation'):
            self.app.record_shortcut()
        self.assertFalse(self.app.is_recording)
        self.assertEqual(self.app.session.take_paths(),[])

    def test_diagnostic_length_and_class_mismatch_are_blocked(self):
        self.prepare()
        for field,value in [('recording_kind','diagnostic'),('take_limit',25),('variation','rub_scratch_nail_wood')]:
            original=dpg.get_value(field);dpg.set_value(field,value)
            self.app.release_record_key();self.app.record_shortcut()
            self.assertFalse(self.app.is_recording)
            self.assertIn('TAKE NOT STARTED',dpg.get_value('status'))
            self.assertEqual(self.app.session.take_paths(),[])
            dpg.set_value(field,original)

    def test_holdout_confirmation_still_required_then_two_second_save(self):
        self.prepare('holdout')
        self.app.record_shortcut()
        self.assertFalse(self.app.is_recording)
        self.assertTrue(dpg.is_item_shown('holdout_dialog'))
        with patch('visualizer.time.monotonic',return_value=100):
            self.app.confirm_holdout()
        self.assertTrue(self.app.is_recording)
        self.finish()
        with np.load(self.app.session.take_paths()[0],allow_pickle=False) as data:
            info=json.loads(str(data['metadata_json']))
            self.assertTrue(info['holdout_confirmed']);self.assertEqual(info['split'],'holdout')
        self.assertEqual(self.app.take_counts['holdout']['knock'],1)
        self.assertEqual(self.app.take_counts['train']['knock'],0)

    def test_short_take_is_retained_but_excluded(self):
        self.prepare()
        with patch('visualizer.time.monotonic',return_value=100):self.app.record_shortcut()
        self.app.frames=[np.ones(4)];self.app.times=[.1];self.app.rms=[.001];self.app.peaks=[.005]
        with patch('visualizer.time.monotonic',return_value=100.5):self.app.stop_take()
        self.assertEqual(self.app.session.take_paths(),[])
        files=self.app.session.take_paths(include_excluded=True)
        self.assertEqual(len(files),1);self.assertIn('.excluded.',files[0].name)
        self.assertEqual(self.app.take_counts['train']['knock'],0)

    def test_visible_cue_timing_and_exact_class_word_check(self):
        self.assertIn('READY',single_action_phase(.1,'rub'))
        self.assertIn('SCRATCH ONCE',single_action_phase(.35,'rub'))
        self.assertIn('STAY STILL',single_action_phase(1.5,'rub'))
        self.assertEqual(fast_take_warnings('take','rub','rub_scratch_nail_wood',2),[])
        self.assertTrue(fast_take_warnings('take','rub','scrubbing wood',2))


if __name__=='__main__':unittest.main()
