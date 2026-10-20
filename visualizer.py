"""UM2 collection GUI: fixed 48 kHz / 50 ms FFT, physical input 2."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time
import traceback
import uuid

import dearpygui.dearpygui as dpg
import numpy as np
import pyaudio

from collection import CollectionSession, utc_now, training_eligible
from recording_policy import (TRIAL_TYPES, recording_plan, authorize_plan, trial_phase,
                              rhythm_phase, fast_take_warnings, single_action_phase)
from models import (get_ear, get_audio_features, preprocess_data, train_model,
                    predict, save_model, load_model, DEFAULT_MODEL_TYPE, MODEL_OPTIONS,
                    SPACE_TRIAL_TYPES, TrialRecorder)
from slide_udp import DEFAULT_TARGET, LabelSender, parse_target

# Text fields where a typed space/R must never trigger an action.
TEXT_FIELDS = ('variation', 'performer', 'class_input', 'take_limit', 'action_performed')
# Widgets locked while a live bakeoff trial runs: only SPACE may act.
BAKEOFF_LOCKED = ('mode', 'bakeoff_trial_type', 'bakeoff_practice', 'bakeoff_undo',
                  'bakeoff_reset', 'save_model_button', 'load_model_button')


class App:
    def __init__(self, session_root='data_sessions', device=None, final=False,
                 setup_id='A_paper_scratch_17x27_direct_table', scratch_surface='paper', event_rhythm=False,
                 fast_takes=False,trained_model=None,decision_params=None,slide_udp=DEFAULT_TARGET,
                 trial_log_root='trial_logs'):
        # C's slide app: forwards the same final label shown as Prediction (no extra decisions).
        self.slide_sender = LabelSender(parse_target(slide_udp))
        self.trial_log_root = Path(trial_log_root)
        self.ensure_bakeoff_state()
        self.session_root = session_root
        self.setup_id = setup_id
        self.scratch_surface = scratch_surface
        self.event_rhythm = event_rhythm
        self.fast_takes = fast_takes
        self.record_key_held = False
        self.session_type = 'final' if final else 'pilot'
        self.take_counts = {split: dict(neutral=0, knock=0, rub=0) for split in ('train', 'holdout')}
        self.trial_counts = dict.fromkeys(TRIAL_TYPES, 0)
        self.pending_holdout = None
        self.ear = None
        self.session = None
        self.pending_take = None
        self.frames = []
        self.times = []
        self.rms = []
        self.peaks = []
        self.record_val = None
        self.is_recording = False
        self.collected_data = {}
        self.model = None
        self.wood_predictor = None
        self.infer_classes = []
        self.fault = None
        self.last_fft_time = None
        self.plot_max = 1000.0
        self.unsaved = False
        self.metadata_path = Path('metadata/metadata.json')
        try:
            self.metadata = json.loads(self.metadata_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.metadata = {}
        self.devices = {}
        pa = pyaudio.PyAudio()
        try:
            for index in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(index)
                if info['maxInputChannels'] < 2:
                    continue
                api = pa.get_host_api_info_by_index(info['hostApi'])['name']
                # Default DPG font cannot display CJK. API and index remain unambiguous.
                name = info['name'].encode('ascii', errors='replace').decode('ascii')
                label = f"[{index}] {api} | {name}"
                self.devices[label] = dict(index=index, name=info['name'], host_api=api)
        finally:
            pa.terminate()
        selected = None
        for label, info in self.devices.items():
            if device == info['index']:
                selected = label
                break
            if (device is None and 'USB Audio CODEC' in info['name']
                    and info['host_api'] == 'Windows WASAPI'):
                selected = label
        self.selected_device = selected
        dpg.create_context()
        dpg.configure_app(manual_callback_management=True)
        dpg.create_viewport(title='FFT Trainer - UM2 input 2', width=1180, height=880)
        self.build_ui()
        if selected:
            self.open_device(selected)
        else:
            self.message('Select a stereo USB Audio CODEC input. Connect UM2 and restart if absent.')
        # Default classes are ready for collection; no prior samples are assumed.
        for name in ('neutral', 'knock', 'rub'):
            self.add_class(name)
        if self.fast_takes:
            if self.ear is not None:
                self.ensure_session()
            self.refresh_fast_panel()
        if trained_model is not None:
            from wood_v3_model import WoodV3Model
            self.wood_predictor=WoodV3Model(trained_model,decision_params)
            if self.wood_predictor.params['setup_id']!=self.setup_id:
                raise ValueError('Model setup does not match the selected hardware setup ID')
            self.model=self.wood_predictor.model
            self.infer_classes=self.wood_predictor.params['class_names']
            self.model_source=dict(trained_model=str(trained_model),decision_params=str(decision_params),
                                   setup_id=self.setup_id)
            dpg.set_value('mode','Infer')
            self.mode_callback(None,'Infer')
            self.message('Wood v3 model + band gate loaded. PROVISIONAL: adversarial trials not validated.')

    def message(self, text):
        print(text, flush=True)
        dpg.set_value('status', text)

    def ensure_bakeoff_state(self):
        """Live bakeoff SPACE trials (Infer mode): the SAME final label is shown, sent to C and
        collected. Fills only missing attributes, so App objects built without __init__ still work."""
        defaults = dict(trial=TrialRecorder, space_key_held=lambda: False,
                        trial_log_root=lambda: Path('trial_logs'), trial_log_path=lambda: None,
                        trial_status_start=lambda: None, trial_started_utc=lambda: None,
                        model_source=lambda: None)
        for name, make in defaults.items():
            if not hasattr(self, name):
                setattr(self, name, make())

    def build_ui(self):
        self.ensure_bakeoff_state()
        with dpg.window(tag='fft_window', label='Live input / FFT', no_move=True, no_resize=True,
                        no_close=True, pos=(0, 0), width=740, height=840):
            dpg.add_combo(list(self.devices), tag='device_combo', label='Device', width=-1,
                          default_value=self.selected_device or '', callback=self.device_callback)
            dpg.add_text('Frozen profile: 48000 Hz | stereo int16 -> ch2 | FFT 50 ms / 2400 samples')
            dpg.add_text('Waiting for audio', tag='audio_status', wrap=690)
            dpg.add_text('Waiting for FFT', tag='fft_status')
            dpg.add_checkbox(label='Auto-scale plot (display only)', tag='auto_scale', default_value=True)
            with dpg.plot(label='FFT amplitude', width=-1, height=-1):
                dpg.add_plot_axis(dpg.mvXAxis, label='Frequency (Hz)', tag='x_axis')
                dpg.add_plot_axis(dpg.mvYAxis, label='Amplitude', tag='y_axis')
                dpg.add_line_series([], [], parent='y_axis', tag='fft_series')
                dpg.set_axis_limits('x_axis', 0, 24000)
                dpg.set_axis_limits('y_axis', 0, 1000)
        with dpg.window(tag='controls', label='Collection / model', no_move=True, no_resize=True,
                        no_close=True, pos=(740, 0), width=425, height=840):
            dpg.add_text('Ready', tag='status', wrap=385)
            dpg.add_text('No session yet', tag='session_path', wrap=385)
            dpg.add_text('', tag='preflight_summary', wrap=385, show=getattr(self,'fast_takes',False))
            dpg.add_text('', tag='preflight_warning', wrap=385, color=(255,100,80), show=getattr(self,'fast_takes',False))
            with dpg.group(show=getattr(self,'fast_takes',False)):
                for name in ('knock','rub','neutral'):
                    dpg.add_text(f'{name.upper()}: train 0 | holdout 0',tag=f'fast_count_{name}')
                dpg.add_text('R = next take. After editing notes, click the plot once.',wrap=385)
            dpg.add_combo(['Train', 'Infer'], default_value='Train', tag='mode', callback=self.mode_callback)
            with dpg.group(tag='train_group'):
                dpg.add_text(f'Session: {self.session_type}; new session each launch')
                dpg.add_text('rub = FINGERNAIL SCRATCH ON ' + getattr(self, 'scratch_surface', 'paper').upper(), color=(255, 220, 80), wrap=385)
                dpg.add_combo(['take', 'trial', 'diagnostic'], default_value='take', tag='recording_kind',
                              label='Recording kind', callback=self.split_callback)
                dpg.add_combo(['train', 'holdout'], default_value='train', tag='split',
                              label='DATA SPLIT', callback=self.split_callback)
                dpg.add_text('WILL SAVE AS TRAIN', tag='split_banner', color=(255, 220, 80), wrap=385)
                dpg.add_text('', tag='rhythm_status', color=(80, 230, 255), wrap=385)
                dpg.add_text('Training takes: knock 0/10, rub 0/10, neutral 0/16', tag='take_progress', wrap=385,
                             show=not getattr(self,'fast_takes',False))
                dpg.add_text('Holdout takes: knock 0/2, rub 0/2, neutral 0/2', tag='holdout_progress', wrap=385,
                             show=not getattr(self,'fast_takes',False))
                dpg.add_input_text(label='Performer', tag='performer', default_value='A', width=210)
                dpg.add_input_text(label='Variation / notes', tag='variation', width=210,
                                   hint='force, position, action')
                with dpg.group(tag='trial_options', show=False):
                    dpg.add_combo(list(TRIAL_TYPES), default_value='knock_pos', tag='trial_type', label='Trial type')
                    dpg.add_input_text(tag='action_performed', label='Action performed', width=210)
                    dpg.add_text('8 seconds: still 2s -> act ONCE ~1s -> still', wrap=385)
                dpg.add_text('Trials: knock_pos 0/5, rub_pos 0/5, knock_neg 0/5, rub_neg 0/5',
                             tag='trial_progress', wrap=385)
                dpg.add_input_float(label='Take limit (s)', tag='take_limit', default_value=2.0 if getattr(self,'fast_takes',False) else 25.0,
                                    min_value=2.0, max_value=60.0, min_clamped=True, max_clamped=True, width=140)
                with dpg.group(horizontal=True):
                    dpg.add_input_text(tag='class_input', width=185, hint='new class')
                    dpg.add_button(label='Add Class', callback=self.add_class_callback)
                dpg.add_child_window(tag='class_list', height=210, width=-1)
                dpg.add_text('Selected: none', tag='selected_class')
                dpg.add_button(label='Record Data', tag='record_button', enabled=False,
                               callback=self.record_callback)
                dpg.add_text('Each stopped take is saved automatically.', tag='recording_status', wrap=385)
                dpg.add_button(label='Export Dataset for B', callback=self.export_callback)
                dpg.add_separator()
                dpg.add_text('Optional model training (B can do this later)')
                dpg.add_combo(MODEL_OPTIONS, tag='model_type', default_value=DEFAULT_MODEL_TYPE, width=220)
                dpg.add_button(label='Train Model', tag='train_button', callback=self.train_callback,
                               enabled=not (getattr(self, 'event_rhythm', False) or getattr(self,'fast_takes',False)))
            with dpg.group(tag='infer_group', show=False):
                dpg.add_text('Prediction: ---', tag='prediction')
                dpg.add_button(label='Save Model', tag='save_model_button',
                               callback=lambda: dpg.show_item('save_model_dialog'))
                dpg.add_button(label='Load Model', tag='load_model_button',
                               callback=lambda: dpg.show_item('load_model_dialog'))
                dpg.add_separator()
                dpg.add_text('BAKEOFF TRIAL  (SPACE = start / stop)', color=(80, 230, 255))
                dpg.add_combo(list(SPACE_TRIAL_TYPES), default_value=SPACE_TRIAL_TYPES[0],
                              tag='bakeoff_trial_type', label='Trial type', width=160)
                dpg.add_checkbox(label='Practice run (not counted)', tag='bakeoff_practice')
                dpg.add_text('READY - press SPACE to start', tag='bakeoff_state', color=(150, 230, 150))
                dpg.add_text('Set: -', tag='bakeoff_set', wrap=385)
                dpg.add_text('Result: -', tag='bakeoff_result', wrap=385)
                dpg.add_text('', tag='bakeoff_tally', wrap=385)
                with dpg.group(horizontal=True):
                    dpg.add_button(label='Undo last trial', tag='bakeoff_undo', callback=self.undo_bakeoff_trial)
                    dpg.add_button(label='Reset tally', tag='bakeoff_reset', callback=self.reset_bakeoff_tally)
                dpg.add_text('', tag='bakeoff_log', wrap=385, color=(150, 150, 150))
            dpg.add_separator()
            dpg.add_text('Keep gain / mounting fixed. Windows audio enhancements OFF.', wrap=385)
        for action, callback in [('save', self.save_model_callback), ('load', self.load_model_callback)]:
            with dpg.file_dialog(tag=f'{action}_model_dialog', show=False, callback=callback,
                                 width=700, height=420, default_path='.', default_filename='model.model'):
                dpg.add_file_extension('.model')
        with dpg.window(tag='holdout_dialog', label='CONFIRM HOLDOUT FOR THIS TAKE',
                        modal=True, show=False, width=520, height=200):
            dpg.add_text('', tag='holdout_message', wrap=475)
            dpg.add_button(label='CONFIRM: SAVE THIS TAKE AS HOLDOUT', callback=self.confirm_holdout)
            dpg.add_button(label='Cancel', callback=self.cancel_holdout)
        dpg.set_viewport_resize_callback(self.resize)
        if getattr(self,'fast_takes',False):
            font_path=Path('C:/Windows/Fonts/consola.ttf')
            if font_path.exists():
                with dpg.font_registry():
                    counter_font=dpg.add_font(str(font_path),24)
                for name in ('knock','rub','neutral'):
                    dpg.bind_item_font(f'fast_count_{name}',counter_font)
                dpg.bind_item_font('rhythm_status',counter_font)
            with dpg.handler_registry():
                dpg.add_key_press_handler(key=dpg.mvKey_R,callback=self.record_shortcut)
                dpg.add_key_release_handler(key=dpg.mvKey_R,callback=self.release_record_key)
        with dpg.handler_registry():
            dpg.add_key_press_handler(key=dpg.mvKey_Spacebar, callback=self.space_shortcut)
            dpg.add_key_release_handler(key=dpg.mvKey_Spacebar, callback=self.release_space_key)
        self.refresh_bakeoff_tally()

    def split_callback(self, *_):
        trial = dpg.get_value('recording_kind') == 'trial'
        diagnostic = dpg.get_value('recording_kind') == 'diagnostic'
        dpg.configure_item('trial_options', show=trial)
        dpg.configure_item('split', enabled=not (trial or diagnostic))
        dpg.configure_item('take_limit', enabled=not trial)
        dpg.set_value('split_banner', 'DIAGNOSTIC ONLY - NEVER TRAIN OR HOLDOUT' if diagnostic else
                      'EVALUATION TRIAL ONLY - NEVER TRAIN' if trial else
                      ('WILL SAVE AS HOLDOUT - CONFIRM EACH TAKE' if dpg.get_value('split') == 'holdout'
                       else 'WILL SAVE AS TRAIN'))

    def request_snapshot(self):
        return dict(kind=dpg.get_value('recording_kind'), split=dpg.get_value('split'),
                    class_name=self.record_val, variation=dpg.get_value('variation'),
                    trial_type=dpg.get_value('trial_type'), action_performed=dpg.get_value('action_performed'),
                    performer=dpg.get_value('performer').strip())

    def ensure_session(self):
        if self.session is None:
            self.session=CollectionSession(self.config(),self.session_root)
            dpg.disable_item('device_combo')
        dpg.set_value('session_path',str(self.session.path.resolve()))

    def refresh_fast_panel(self):
        if not getattr(self,'fast_takes',False):
            return []
        snapshot=self.request_snapshot()
        seconds=dpg.get_value('take_limit')
        path=str(self.session.path.resolve()) if self.session else str(Path(self.session_root).resolve())+' (new session pending input)'
        dpg.set_value('preflight_summary',
                      f"SESSION: {path}\nClass: {snapshot['class_name'] or '(none)'} | Kind: {snapshot['kind']}\n"
                      f"Split: {snapshot['split']} | Length: {seconds:g}s | Performer: {snapshot['performer']}\n"
                      f"Notes: {snapshot['variation']}")
        warnings=fast_take_warnings(snapshot['kind'],snapshot['class_name'],snapshot['variation'],seconds)
        if not snapshot['performer']:
            warnings.append('Enter performer.')
        dpg.set_value('preflight_warning','WARNING: '+' '.join(warnings) if warnings else 'READY: 2s single-action take')
        for name in ('knock','rub','neutral'):
            dpg.set_value(f'fast_count_{name}',f"{name.upper()}: train {self.take_counts['train'][name]} | holdout {self.take_counts['holdout'][name]}")
        return warnings

    def release_record_key(self,*_):
        self.record_key_held=False

    def record_shortcut(self,*_):
        if getattr(self,'record_key_held',False):
            return
        self.record_key_held=True
        if self.is_recording or self.pending_holdout is not None:
            return
        for tag in ('variation','performer','class_input','take_limit'):
            if dpg.is_item_focused(tag) or dpg.is_item_active(tag):
                return  # Never record while typing an R in a field.
        self.record_callback()

    # ---------- live bakeoff SPACE trials (Infer mode) ----------
    def release_space_key(self, *_):
        self.space_key_held = False

    def space_shortcut(self, *_):
        if self.space_key_held:
            return  # holding SPACE must not toggle repeatedly
        self.space_key_held = True
        if dpg.get_value('mode') != 'Infer':
            return
        if any(dpg.does_item_exist(tag) and (dpg.is_item_focused(tag) or dpg.is_item_active(tag))
               for tag in TEXT_FIELDS):
            return  # never toggle while typing a space in a field
        if self.trial.active:
            self.stop_bakeoff_trial()
        else:
            self.start_bakeoff_trial()

    def start_bakeoff_trial(self):
        if self.model is None:
            self.message('Load a model before starting a bakeoff trial.')
            return
        if not self.healthy():
            self.message('Wait for healthy live audio before starting a bakeoff trial.')
            return
        self.trial.start(dpg.get_value('bakeoff_trial_type'), practice=dpg.get_value('bakeoff_practice'))
        self.trial_status_start = self.ear.stream_reader.status_count
        self.trial_started_utc = utc_now()
        for tag in BAKEOFF_LOCKED:
            dpg.disable_item(tag)
        kind = 'PRACTICE ' if self.trial.practice else ''
        dpg.set_value('bakeoff_state', f'RECORDING {kind}{self.trial.trial_type} - press SPACE to stop')
        dpg.configure_item('bakeoff_state', color=(255, 90, 90))
        dpg.set_value('bakeoff_set', 'Set: {}')
        dpg.set_value('bakeoff_result', 'Result: (running)')

    def stop_bakeoff_trial(self, invalid_reason=None):
        if not self.trial.active:
            return
        if invalid_reason is None and self.ear is not None and \
                self.ear.stream_reader.status_count != self.trial_status_start:
            invalid_reason = 'PortAudio reported capture status during this trial'
        result = self.trial.stop(invalid_reason)
        for tag in BAKEOFF_LOCKED:
            dpg.enable_item(tag)
        dpg.set_value('bakeoff_state', 'READY - press SPACE to start')
        dpg.configure_item('bakeoff_state', color=(150, 230, 150))
        dpg.set_value('bakeoff_set', 'Set: {' + ', '.join(result['label_set']) + '}')
        if not result['valid']:
            text, color = f"INVALID ({result['invalid_reason']}) - not counted, repeat", (255, 200, 80)
        else:
            text = 'PASS' if result['passed'] else 'FAIL'
            color = (120, 230, 120) if result['passed'] else (255, 90, 90)
            if result['practice']:
                text += ' (practice, not counted)'
        dpg.set_value('bakeoff_result', f"Result: {result['trial_type']} {text}  "
                      f"[{result['n_frames']} frames, {result['duration_s']:.1f}s]")
        dpg.configure_item('bakeoff_result', color=color)
        self.refresh_bakeoff_tally()
        self.log_bakeoff_event('trial', started_utc=self.trial_started_utc, **result)

    def undo_bakeoff_trial(self, *_):
        result = self.trial.undo_last()
        if result is None:
            self.message('No bakeoff trial to undo.')
            return
        dpg.set_value('bakeoff_result', f"Result: undone {result['trial_type']} "
                      f"(set {{{', '.join(result['label_set'])}}})")
        dpg.configure_item('bakeoff_result', color=(200, 200, 200))
        self.refresh_bakeoff_tally()
        self.log_bakeoff_event('undo', trial_type=result['trial_type'], label_set=result['label_set'])

    def reset_bakeoff_tally(self, *_):
        self.trial.reset_tally()
        self.refresh_bakeoff_tally()
        self.log_bakeoff_event('reset_tally')

    def refresh_bakeoff_tally(self):
        tally = self.trial.tally
        passed = sum(p for p, _ in tally.values())
        counted = sum(n for _, n in tally.values())
        dpg.set_value('bakeoff_tally', 'Tally: ' + ', '.join(
            f'{t} {p}/{n}' for t, (p, n) in tally.items()) + f'  |  total {passed}/{counted}')

    def log_bakeoff_event(self, event, **fields):
        """Append one JSON line per event. Logs are local evaluation records, not training data."""
        if self.trial_log_path is None:
            folder = self.trial_log_root / time.strftime('%Y%m%d_%H%M%S')
            folder.mkdir(parents=True, exist_ok=True)
            self.trial_log_path = folder / 'trials.jsonl'
        record = dict(event=event, logged_utc=utc_now(), model=self.model_source, **fields)
        with open(self.trial_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + '\n')
        dpg.set_value('bakeoff_log', f'Log: {self.trial_log_path.resolve()}')

    def recording_tick(self,elapsed):
        if self.take_notes.get('event_protocol')=='single_action_2s':
            dpg.set_value('rhythm_status',single_action_phase(elapsed,self.record_val))
        elif self.take_notes.get('event_protocol')=='one_action_every_2s':
            dpg.set_value('rhythm_status',rhythm_phase(elapsed,self.record_val,self.take_limit))
        if elapsed>=self.take_limit:
            self.stop_take()
            return True
        return False

    def cancel_holdout(self, *_):
        self.pending_holdout = None
        dpg.hide_item('holdout_dialog')

    def confirm_holdout(self, *_):
        pending = self.pending_holdout
        self.cancel_holdout()
        if pending is None or pending != self.request_snapshot():
            self.message('Settings changed. Click Record Data and confirm again.')
            return
        performer = pending.pop('performer')
        self.start_take(recording_plan(**pending, holdout_confirmed=True), performer)

    def resize(self, *_):
        width = dpg.get_viewport_client_width()
        height = dpg.get_viewport_client_height()
        left = max(400, width - 430)
        dpg.configure_item('fft_window', width=left, height=height)
        dpg.configure_item('controls', pos=(left, 0), width=max(300, width-left), height=height)

    def open_device(self, label):
        if self.is_recording or self.session is not None:
            raise ValueError('Restart for a different device/session; keep this dataset configuration fixed.')
        if self.ear is not None:
            self.ear.stream_reader.terminate()
            self.ear = None
        self.selected_device = label
        self.fault = None
        self.last_fft_time = None
        info = self.devices[label]
        try:
            self.ear = get_ear(info['index'])
            if self.ear.rate != 48000 or self.ear.FFT_window_size != 2400:
                raise ValueError('Frozen sample rate / FFT size mismatch')
            self.metadata.update(default_device=info['name'], default_host_api=info['host_api'])
            self.metadata_path.parent.mkdir(exist_ok=True)
            self.metadata_path.write_text(json.dumps(self.metadata, indent=2), encoding='utf-8')
            self.message(f"Input opened: [{info['index']}] {info['host_api']}, ch2. Waiting for fresh audio.")
        except Exception as exc:
            if self.ear is not None:
                self.ear.stream_reader.terminate()
                self.ear = None
            self.message(f'Cannot open input: {exc}. Select another entry; rate stays 48000 Hz.')

    def device_callback(self, sender, value):
        self.open_device(value)
        if getattr(self,'fast_takes',False) and self.ear is not None:
            self.ensure_session()
            self.refresh_fast_panel()

    def add_class_callback(self):
        name = dpg.get_value('class_input').strip()
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            self.message('Use class names with letters, numbers, underscore or hyphen.')
            return
        self.add_class(name)
        dpg.set_value('class_input', '')

    def add_class(self, name):
        if name in self.collected_data:
            return
        self.collected_data[name] = []
        with dpg.group(parent='class_list', tag=f'class_group_{name}'):
            dpg.add_text(f'{name}: 0', tag=f'count_{name}')
            with dpg.group(horizontal=True):
                dpg.add_button(label='Select', tag=f'select_{name}', callback=lambda s, a, u: self.select_class(u), user_data=name)
                dpg.add_button(label='Clear data', tag=f'clear_{name}', callback=lambda s, a, u: self.clear_class(u), user_data=name)
            dpg.add_separator()

    def select_class(self, name):
        self.stop_take()
        self.record_val = name
        dpg.set_value('selected_class', f'Selected: {name}')
        self.refresh_fast_panel()

    def clear_class(self, name):
        self.stop_take()
        if self.pending_take is not None:
            raise ValueError('Save pending take first')
        if self.session:
            self.session.exclude_class(name)
        self.collected_data[name] = []
        for counts in self.take_counts.values():
            counts[name] = 0
        dpg.set_value(f'count_{name}', f'{name}: 0')
        self.message(f'{name} cleared; saved originals are retained as excluded takes.')

    def healthy(self):
        if self.ear is None or self.fault:
            return False
        r = self.ear.stream_reader
        return (r.last_capture_time is not None and time.monotonic()-r.last_capture_time < 1.0
                and self.last_fft_time is not None and time.monotonic()-self.last_fft_time < 1.0
                and self.ear.num_ffts >= 4 and not r.last_error and r.stream.is_active())

    def config(self):
        info = self.devices[self.selected_device]
        return dict(session_type=self.session_type, setup_id=self.setup_id,
                    interaction_2=f'rub means scratch_nail_{self.scratch_surface}; old setup data excluded',
                    training_window_policy=('offline_single_action_segmentation_required' if getattr(self,'fast_takes',False) else
                                            'offline_event_segmentation_required' if getattr(self, 'event_rhythm', False) else 'take_level_labels'),
                    collection_protocol='single_action_2s' if getattr(self,'fast_takes',False) else 'standard_take',
                    device_name=info['name'], host_api=info['host_api'], device_index=info['index'],
                    backend='PyAudio', physical_input='UM2 INST 2', captured_channels=2,
                    selected_channel_1_based=2, dtype='int16', sample_rate=48000,
                    frames_per_capture_block=self.ear.stream_reader.update_window_n_frames,
                    fft_window_ms=50, fft_window_samples=2400, feature_count=len(self.ear.fft),
                    feature_source='full FFT amplitude; NOT 512 grouped bins',
                    feature_pipeline='starter Hamming/rFFT/drop DC/pink weighting/temporal smoothing',
                    preprocessing='models.preprocess_data; currently identity',
                    smoothing_length_ms=self.ear.smoothing_length_ms, target_feature_updates_per_second=30,
                    windows_overlap=True, windows_are_not_independent_trials=True,
                    windows_input_level=100, audio_enhancements='OFF (operator must verify)',
                    library_versions={name: version(name) for name in
                                      ('numpy', 'scipy', 'pyaudio', 'dearpygui', 'scikit-learn')},
                    source_sha256={name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                                   for name in ('models.py', 'src/stream_reader.py',
                                                'src/stream_analyzer.py', 'src/utils.py', 'visualizer.py')},
                    hardware_reference='SETUP.md; photograph exact gain and mounting before final data')

    def record_callback(self):
        if self.pending_take is not None:
            self.persist_pending()
        elif self.is_recording:
            self.stop_take()
        else:
            if not self.healthy() or dpg.get_value('mode') != 'Train':
                self.message('Select a class and wait for healthy live input before recording.')
                return
            warnings=self.refresh_fast_panel()
            if warnings:
                self.message('TAKE NOT STARTED: '+' '.join(warnings))
                return
            snapshot = self.request_snapshot()
            if not snapshot['performer']:
                self.message('Enter performer before recording.')
                return
            performer = snapshot.pop('performer')
            plan = recording_plan(**snapshot)
            if plan['split'] == 'holdout':
                self.pending_holdout = dict(snapshot, performer=performer)
                dpg.set_value('holdout_message', f"Class: {plan['class_name']}\n{plan['variation']}\n"
                              'THIS TAKE WILL BE SAVED AS HOLDOUT. Excluded from training.\n' +
                              ('After confirming, wait for ACTION NOW (~0.3s).' if getattr(self,'fast_takes',False)
                               else 'After confirming, begin the action immediately.'))
                dpg.show_item('holdout_dialog')
                return
            self.start_take(plan, performer)

    def start_take(self, plan, performer):
        authorize_plan(plan)
        if not self.healthy() or dpg.get_value('mode') != 'Train':
            self.message('Wait for fresh healthy audio, then request recording again.')
            return
        self.ensure_session()
        plan = dict(plan)
        self.take_limit = plan.pop('take_limit', max(2 if getattr(self,'fast_takes',False) else 5,
                                                   min(60,dpg.get_value('take_limit'))))
        self.record_val = plan.pop('class_name')
        if getattr(self,'fast_takes',False) and plan['recording_kind']=='take':
            plan.update(event_protocol='single_action_2s',first_action_s=.3,
                        expected_events=0 if self.record_val=='neutral' and any(word in plan['variation'].lower() for word in ('quiet','still')) else 1,
                        requested_action_s=1.0 if self.record_val=='rub' else .35,
                        requested_take_s=2.0)
        elif (getattr(self, 'event_rhythm', False) and plan['recording_kind'] == 'take'
                and self.record_val in ('knock', 'rub')):
            plan.update(event_protocol='one_action_every_2s', event_period_s=2.0,
                        first_action_s=1.0, expected_events=max(0, int(np.ceil((self.take_limit-1)/2))),
                        requested_action_s=1.0 if self.record_val == 'rub' else .35)
        self.frames, self.times, self.rms, self.peaks = [], [], [], []
        self.take_notes = dict(plan, performer=performer, started_utc=utc_now())
        self.take_start = time.monotonic()
        self.status_start = self.ear.stream_reader.status_count
        self.is_recording = True
        for tag in ('recording_kind', 'split', 'performer', 'variation', 'trial_type',
                    'action_performed', 'take_limit', 'mode'):
            dpg.disable_item(tag)
        for name in self.collected_data:
            dpg.disable_item(f'select_{name}')
            dpg.disable_item(f'clear_{name}')
        dpg.configure_item('record_button', label='Stop Recording')
        if self.take_notes.get('event_protocol')=='single_action_2s':
            dpg.set_value('rhythm_status',single_action_phase(0,self.record_val))
        self.message(f"Recording {self.record_val}; SAVING AS {plan['split'].upper()}; "
                     f'auto-stop after {self.take_limit:g}s.')

    def stop_take(self, valid=True, reason=''):
        if not self.is_recording:
            return
        self.is_recording = False
        dpg.set_value('rhythm_status', '')
        for tag in ('recording_kind', 'split', 'performer', 'variation', 'trial_type',
                    'action_performed', 'take_limit', 'mode'):
            dpg.enable_item(tag)
        for name in self.collected_data:
            dpg.enable_item(f'select_{name}')
            dpg.enable_item(f'clear_{name}')
        self.split_callback()
        dpg.configure_item('record_button', label='Record Data')
        if not self.frames:
            self.message('No fresh FFT frames captured; no take saved.')
            return
        if self.ear.stream_reader.status_count != self.status_start:
            valid, reason = False, 'PortAudio reported capture status during this take'
        if self.take_notes['recording_kind'] == 'trial' and time.monotonic()-self.take_start < 7.9:
            valid, reason = False, 'Trial stopped before full 8 seconds'
        if self.take_notes.get('event_protocol')=='single_action_2s' and time.monotonic()-self.take_start < 1.9:
            valid,reason=False,'Single-action take stopped before full 2 seconds'
        self.pending_take = dict(take_id=f'take_{uuid.uuid4().hex}',
                                 class_name=self.record_val, X=np.array(self.frames, dtype=np.float32),
                                 elapsed_s=self.times, rms_fs=self.rms, peak_fs=self.peaks,
                                 duration_s=time.monotonic()-self.take_start,
                                 valid=valid, reason=reason, **self.take_notes)
        self.persist_pending()

    def persist_pending(self):
        if self.pending_take is None:
            return
        try:
            path = self.session.save_take(**self.pending_take)
        except Exception:
            self.unsaved = True
            dpg.configure_item('record_button', label='Retry Save', enabled=True)
            self.message('SAVE FAILED: take retained in memory. Check disk; click Retry Save before closing.')
            raise
        if training_eligible(self.pending_take):
            name = self.pending_take['class_name']
            self.collected_data[name].extend(self.pending_take['X'])
            dpg.set_value(f'count_{name}', f'{name}: {len(self.collected_data[name])}')
        if self.pending_take['valid'] and self.pending_take['split'] == 'trial':
            kind = self.pending_take['trial_type']
            self.trial_counts[kind] += 1
            dpg.set_value('trial_progress', 'Trials: ' + ', '.join(
                f'{key} {count}/5' for key, count in self.trial_counts.items()))
        elif self.pending_take['valid'] and self.pending_take['split'] in ('train', 'holdout'):
            split = self.pending_take['split']
            name = self.pending_take['class_name']
            self.take_counts[split][name] = self.take_counts[split].get(name, 0) + 1
            for split_name, tag, targets in [('train', 'take_progress', dict(knock=10, rub=10, neutral=16)),
                                            ('holdout', 'holdout_progress', dict(knock=2, rub=2, neutral=2))]:
                counts = self.take_counts[split_name]
                dpg.set_value(tag, split_name + ' takes: ' + ', '.join(
                    f'{key} {counts[key]}/{target}' for key, target in targets.items()))
        self.pending_take = None
        self.unsaved = False
        self.frames, self.times, self.rms, self.peaks = [], [], [], []
        dpg.configure_item('record_button', label='Record Data')
        self.message(f'Saved {path.name}' + (' (excluded: capture problem)' if '.excluded.' in path.name else ''))
        self.refresh_fast_panel()

    def export_callback(self):
        self.stop_take()
        if self.pending_take is not None:
            self.persist_pending()
        if self.session is None:
            self.message('Record at least one take first.')
            return
        if not any(self.take_counts[s].get(c, 0) for s in self.take_counts for c in self.take_counts[s]):
            self.message('Evaluation trials are autosaved individually; excluded from training exports.')
            return
        path = self.session.export()
        self.message(f'Exported {path.resolve()}')

    def mode_callback(self, sender, value):
        self.stop_take()
        self.stop_bakeoff_trial(invalid_reason='mode changed during trial')
        dpg.configure_item('train_group', show=value == 'Train')
        dpg.configure_item('infer_group', show=value == 'Infer')
        if getattr(self, 'slide_sender', None) is not None:
            self.slide_sender.reset()

    def train_callback(self):
        if getattr(self, 'event_rhythm', False) or getattr(self,'fast_takes',False):
            self.message('Event takes require offline segmentation before training; use the checkpoint trainer.')
            return
        self.stop_take()
        names = [name for name, values in self.collected_data.items() if values]
        if len(names) < 2:
            self.message('Need saved data from at least two classes to train.')
            return
        self.export_callback()
        X = np.concatenate([self.collected_data[name] for name in names])
        y = np.concatenate([np.full(len(self.collected_data[name]), i) for i, name in enumerate(names)])
        self.message('Training...')
        self.model, self.infer_classes = train_model(preprocess_data(X), y, names, dpg.get_value('model_type'))
        dpg.set_value('mode', 'Infer')
        self.mode_callback(None, 'Infer')
        self.message('Model trained. Dataset remains saved on disk.')

    def save_model_callback(self, sender, data):
        if self.model is None:
            raise ValueError('No trained model to save')
        save_model(self.model, self.infer_classes, Path(data['file_path_name']))
        self.message('Model saved.')

    def load_model_callback(self, sender, data):
        self.model, self.infer_classes = load_model(Path(data['file_path_name']))
        self.wood_predictor=None
        self.model_source=dict(model_file=str(data['file_path_name']))
        if getattr(self.model, 'n_features_in_', 1200) != 1200:
            self.model = None
            raise ValueError('Model feature count does not match this 1200-feature profile')
        if getattr(self, 'slide_sender', None) is not None:
            self.slide_sender.reset()
        self.message('Model loaded; use only models trained with this exact capture profile.')

    def update(self):
        self.refresh_fast_panel()
        if self.ear is None or self.fault:
            return
        r = self.ear.stream_reader
        if r.last_error:
            raise RuntimeError(r.last_error)
        if not r.stream.is_active():
            raise RuntimeError('Audio stream stopped. Stop collecting and reopen input.')
        previous = self.ear.num_ffts
        freqs, amps = get_audio_features(self.ear)
        fresh = self.ear.num_ffts != previous
        if fresh:
            self.last_fft_time = time.monotonic()
            dpg.set_value('fft_series', [freqs.tolist(), amps.tolist()])
            index = int(np.argmax(amps))
            dpg.set_value('fft_status', f'Peak: {freqs[index]:.1f} Hz / amplitude {amps[index]:.3g}')
            self.plot_max = max(float(np.max(amps))*1.2, self.plot_max*0.94, 1000)
            dpg.set_axis_limits('y_axis', 0, self.plot_max if dpg.get_value('auto_scale') else 500000)
        healthy = self.healthy()
        rms = getattr(self.ear, 'pcm_rms', 0)/32768
        peak = getattr(self.ear, 'pcm_peak', 0)/32768
        dpg.set_value('audio_status', f"{'LIVE' if healthy else 'WAIT / NO FRESH AUDIO'} | ch2 RMS {100*rms:.3f}% FS | "
                      f'peak {100*peak:.2f}% FS | FFT updates {self.ear.num_ffts} | capture status {r.status_count}')
        dpg.configure_item('record_button', enabled=self.pending_take is not None or
                           (healthy and (self.record_val is not None or dpg.get_value('recording_kind') == 'trial')
                            and dpg.get_value('mode') == 'Train'))
        if self.is_recording:
            if not healthy:
                self.stop_take(valid=False, reason='Audio stopped or stale')
                return
            elapsed = time.monotonic()-self.take_start
            if self.recording_tick(elapsed):
                pass
            elif fresh:
                # Copy immutable snapshots; never record cached FFT or dummy spectra.
                self.frames.append(np.array(amps, dtype=np.float32, copy=True))
                self.times.append(elapsed)
                self.rms.append(rms)
                self.peaks.append(peak)
                phase = trial_phase(elapsed) + ' | ' if self.take_notes['recording_kind'] == 'trial' else ''
                dpg.set_value('recording_status', phase + f'{self.record_val}: {elapsed:.1f}s / '
                              f'{self.take_limit:g}s | {len(self.frames)} new FFT frames')
        if self.trial.active and not healthy:
            self.stop_bakeoff_trial(invalid_reason='Audio stopped or stale')
        if fresh and healthy and dpg.get_value('mode') == 'Infer' and self.model is not None:
            if getattr(self,'wood_predictor',None) is not None:
                label=int(self.wood_predictor.predict_windows(np.asarray([amps]))[0])
            else:
                label = int(predict(self.model, preprocess_data(np.asarray([amps])))[0])
            self.publish_label(self.infer_classes[label])

    def publish_label(self, final_label):
        """One final label feeds the display, C's slide app and the bakeoff trial SET."""
        dpg.set_value('prediction', 'Prediction: ' + final_label)
        if getattr(self, 'slide_sender', None) is not None:
            self.slide_sender.update(final_label)
        if self.trial.active:
            self.trial.add(final_label)
            dpg.set_value('bakeoff_set', 'Set: {' + ', '.join(sorted(self.trial.label_set)) + '}'
                          f'   ({len(self.trial.labels)} frames)')

    def run(self, seconds=None):
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self.resize()
        start = time.monotonic()
        next_update = start
        try:
            while dpg.is_dearpygui_running():
                # Keep widget callbacks and audio/FFT UI work on one main thread.
                for job in dpg.get_callback_queue() or []:
                    try:
                        dpg.run_callbacks([job])
                    except Exception as exc:
                        traceback.print_exc()
                        self.message(f'Action failed: {exc}')
                now = time.monotonic()
                if now >= next_update:
                    try:
                        self.update()
                    except Exception as exc:
                        traceback.print_exc()
                        self.fault = str(exc)
                        self.stop_take(valid=False, reason=str(exc))
                        self.stop_bakeoff_trial(invalid_reason=str(exc))
                        self.message(f'Capture paused: {exc}. Restart after resolving the problem.')
                    next_update = now + 1/30
                dpg.render_dearpygui_frame()
                if seconds is not None and now-start >= seconds:
                    break
        finally:
            try:
                self.stop_bakeoff_trial(invalid_reason='GUI closed during trial')
                self.stop_take()
                if self.pending_take is not None:
                    self.persist_pending()
                if self.session and self.session.take_paths():
                    self.export_callback()
            finally:
                if self.ear:
                    self.ear.stream_reader.terminate()
                dpg.destroy_context()
        print(f'GUI stopped; FFT updates={self.ear.num_ffts if self.ear else 0}', flush=True)


def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=int, help='explicit PyAudio input index (normally auto-select WASAPI USB Audio CODEC)')
    parser.add_argument('--session-root', default='data_sessions')
    parser.add_argument('--final', action='store_true', help='mark a NEW session as final; holdout selected per take')
    parser.add_argument('--setup-id', default='A_paper_scratch_17x27_direct_table', help='hardware setup identifier saved with every take')
    parser.add_argument('--scratch-surface', choices=['paper', 'wood'], default='paper', help='interaction metadata only; does not change audio or features')
    parser.add_argument('--event-rhythm', action='store_true', help='silent two-second action cues for positive take recordings')
    parser.add_argument('--fast-takes',action='store_true',help='2s takes, silent action cue, R shortcut and strict preflight checks')
    parser.add_argument('--trained-model',help='joblib model to load at startup (requires matching decision parameters)')
    parser.add_argument('--decision-params',help='matching decision_params.json for startup inference')
    parser.add_argument('--slide-udp', default=DEFAULT_TARGET, help="send live Infer labels to C's slide app at HOST:PORT on change, or 'off'")
    parser.add_argument('--trial-log-root', default='trial_logs', help='folder for live bakeoff SPACE trial logs (local, not training data)')
    parser.add_argument('--smoke-seconds', type=float, help='close automatically after this many seconds (verification only)')
    args = parser.parse_args()
    if args.fast_takes and args.event_rhythm:
        parser.error('--fast-takes and --event-rhythm are different protocols; select only one')
    if bool(args.trained_model)!=bool(args.decision_params):
        parser.error('--trained-model and --decision-params must be supplied together')
    try:
        parse_target(args.slide_udp)
    except ValueError as exc:
        parser.error(f'--slide-udp: {exc}')
    App(args.session_root, args.device, final=args.final,
        setup_id=args.setup_id, scratch_surface=args.scratch_surface,
        event_rhythm=args.event_rhythm,fast_takes=args.fast_takes,
        trained_model=args.trained_model,decision_params=args.decision_params,
        slide_udp=args.slide_udp,trial_log_root=args.trial_log_root).run(args.smoke_seconds)


if __name__ == '__main__':
    main()
