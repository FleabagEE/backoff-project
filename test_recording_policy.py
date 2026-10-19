"""Prevent split mistakes and leakage of event trials into training."""
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from collection import CollectionSession, training_eligible
from recording_policy import recording_plan, authorize_plan, TRIAL_TYPES
from trial_replay import score_trial, replay


class RecordingTests(unittest.TestCase):
    def test_real_gui_diagnostic_start_stop_saves_without_container_enable(self):
        import dearpygui.dearpygui as dpg
        from visualizer import App
        from types import SimpleNamespace
        dpg.create_context()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                app=App.__new__(App)
                app.devices={}; app.selected_device=None; app.session_type='final'
                app.collected_data={}; app.pending_take=None; app.unsaved=False
                app.ear=SimpleNamespace(stream_reader=SimpleNamespace(status_count=0))
                app.healthy=lambda: True
                app.session=CollectionSession(dict(feature_count=4),tmp)
                app.build_ui(); app.add_class('neutral')
                dpg.set_value('recording_kind','diagnostic')
                dpg.set_value('take_limit',10)
                app.start_take(recording_plan('diagnostic','train','neutral','gui_level_check_quiet'),'A')
                self.assertTrue(app.is_recording)
                self.assertFalse(dpg.get_item_configuration('select_neutral')['enabled'])
                app.frames=[np.ones(4),np.ones(4)]
                app.times=[.1,9.9]; app.rms=[.001,.001]; app.peaks=[.005,.005]
                app.stop_take()
                self.assertFalse(app.is_recording)
                self.assertTrue(dpg.get_item_configuration('select_neutral')['enabled'])
                self.assertEqual(len(app.session.take_paths()),1)
                with np.load(app.session.take_paths()[0],allow_pickle=False) as data:
                    info=json.loads(str(data['metadata_json']))
                    self.assertEqual(info['split'],'diagnostic')
                    self.assertTrue(info['valid'])
                self.assertEqual(app.collected_data['neutral'],[])
                app.event_rhythm=True
                app.add_class('rub')
                app.take_counts={s:dict(neutral=0,knock=0,rub=0) for s in ('train','holdout')}
                dpg.set_value('take_limit',25)
                app.start_take(recording_plan('take','train','rub','r01 scratch_nail_wood'),'A')
                self.assertEqual(app.take_notes['expected_events'],12)
                self.assertEqual(app.take_notes['event_protocol'],'one_action_every_2s')
                app.frames=[np.ones(4),np.ones(4)]
                app.times=[.1,24.9];app.rms=[.001,.001];app.peaks=[.005,.005]
                app.stop_take()
                self.assertEqual(len(app.session.take_paths()),2)
        finally:
            dpg.destroy_context()

    def test_holdout_needs_fresh_explicit_confirmation_and_snapshot(self):
        from visualizer import App
        app=App.__new__(App)
        app.record_val='rub'; app.pending_take=None; app.is_recording=False; app.pending_holdout=None
        app.healthy=lambda:True
        app.message=MagicMock(); app.start_take=MagicMock()
        values=dict(mode='Train',recording_kind='take',split='holdout',performer='A',
                    variation='scratch_nail_paper holdout right index',trial_type='knock_pos',action_performed='')
        with patch('visualizer.dpg') as dpg:
            dpg.get_value.side_effect=values.__getitem__
            app.record_callback()
            app.start_take.assert_not_called()
            dpg.show_item.assert_called_with('holdout_dialog')
            app.confirm_holdout()
            plan=app.start_take.call_args.args[0]
            self.assertEqual(plan['split'],'holdout'); self.assertTrue(plan['holdout_confirmed'])
            app.start_take.reset_mock()
            app.record_callback()
            app.start_take.assert_not_called() # each subsequent take also needs confirmation
            values['variation']='scratch_nail_paper changed settings'
            app.confirm_holdout()
            app.start_take.assert_not_called()

    def test_diagnostic_never_enters_training_or_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=CollectionSession(dict(feature_count=4),tmp)
            session.save_take('neutral',np.ones((2,4)),[.1,.2],[.001]*2,[.1]*2,split='train')
            plan=recording_plan('diagnostic','train','neutral','gui_level_check_quiet')
            self.assertEqual(plan['split'],'diagnostic')
            name=plan.pop('class_name')
            self.assertFalse(training_eligible(dict(plan,class_name=name)))
            self.assertFalse(training_eligible(dict(plan,class_name=name,split='train')))
            session.save_take(name,np.ones((2,4)),[.1,9.9],[.001]*2,[.1]*2,**plan)
            with np.load(session.export(),allow_pickle=False) as data:
                self.assertEqual(len(data['X']),2)
                self.assertNotIn('diagnostic',data['split'])

    def test_guard_wrong_split_and_old_rub(self):
        with self.assertRaises(ValueError):
            recording_plan('take','train','rub','scratch_nail_paper holdout')
        with self.assertRaises(ValueError):
            recording_plan('take','train','rub','old fingertip rub')
        plan=recording_plan('take','holdout','rub','scratch_nail_paper')
        with self.assertRaises(ValueError):
            authorize_plan(plan)
        self.assertFalse(training_eligible(dict(class_name='rub',variation='old rub',split='train')))

    def test_trial_eight_seconds_and_never_training_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=CollectionSession(dict(feature_count=4),tmp)
            session.save_take('neutral',np.ones((2,4)),[.1,.2],[.001]*2,[.1]*2,split='train')
            plan=recording_plan('trial','train','rub','',trial_type='knock_neg',action_performed='one scratch')
            self.assertEqual(plan.pop('take_limit'),8)
            name=plan.pop('class_name')
            self.assertFalse(training_eligible(dict(plan,class_name=name)))
            session.save_take(name,np.ones((2,4)),[.1,7.9],[.001]*2,[.1]*2,duration_s=8,**plan)
            with np.load(session.export(),allow_pickle=False) as data:
                self.assertEqual(len(data['X']),2)
                self.assertNotIn('trial',data['split'])

    def test_bakeoff_set_scoring(self):
        for target in ('knock','rub'):
            other='rub' if target=='knock' else 'knock'
            self.assertTrue(score_trial(target+'_pos',{target}))
            self.assertTrue(score_trial(target+'_pos',{'neutral',target}))
            self.assertFalse(score_trial(target+'_pos',{'neutral'}))
            self.assertFalse(score_trial(target+'_pos',{target,other}))
            self.assertTrue(score_trial(target+'_neg',{'neutral',other}))
            self.assertFalse(score_trial(target+'_neg',{'neutral',target}))
            self.assertFalse(score_trial(target+'_pos',set()))

    def test_replay_includes_onset_and_tail_and_resets_policy_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path
            session=CollectionSession(dict(feature_count=1),tmp)
            for i in range(2):
                session.save_take('rub',np.array([[0],[1],[0]],dtype=float),[.1,2.1,7.9],
                                  [.001,.01,.001],[.01,.1,.01],duration_s=8,recording_kind='trial',
                                  split='trial',trial_type='rub_pos',action_performed='one scratch')
            calls=[]
            def policy(label,rms,peak,elapsed,state):
                calls.append(state.get('count',0)); state['count']=state.get('count',0)+1
                return label
            factory=lambda _: lambda X: ['rub' if x[0] else 'neutral' for x in X]
            with patch('trial_replay.resolve',side_effect=lambda s: factory if s=='fake:adapter' else policy):
                result=replay([session.path],Path(tmp)/'replay.json',adapter='fake:adapter',
                              model_path='B-model',policy='fake:policy')
            self.assertEqual(calls,[0,1,2,0,1,2])
            self.assertEqual(result['passed'],2)
            self.assertTrue(all(r['predicted_set']==['neutral','rub'] for r in result['trials']))


if __name__=='__main__':
    unittest.main()
