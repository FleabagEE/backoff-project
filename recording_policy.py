"""Recording labels and trial protocol only; no audio/feature processing."""
import math
import re

TRIAL_TYPES = ('knock_pos', 'rub_pos', 'knock_neg', 'rub_neg')


def fast_take_warnings(kind, class_name, notes, seconds):
    warnings=[]
    if kind != 'take':
        warnings.append(f'Recording kind is {kind}; select take for the 2s collection.')
    if not math.isclose(float(seconds), 2.0, abs_tol=1e-6):
        warnings.append(f'Take length is {seconds:g}s; set 2s.')
    words=re.split(r'[^a-z0-9]+', notes.lower())
    if not class_name:
        warnings.append('Select a class.')
    elif class_name.lower() not in words:
        warnings.append(f'Notes must mention selected class: {class_name}.')
    return warnings


def single_action_phase(elapsed, class_name):
    if elapsed < .3:
        return f'READY ... {max(0,.3-elapsed):.1f}s'
    if elapsed < 1.4:
        return 'QUIET / ONE NEUTRAL ACTION NOW' if class_name=='neutral' else (
            'SCRATCH ONCE NOW (~1s)' if class_name=='rub' else 'KNOCK ONCE NOW')
    return 'STAY STILL UNTIL SAVED'


def recording_plan(kind, split, class_name, variation, trial_type='', action_performed='',
                   holdout_confirmed=False):
    if kind == 'diagnostic':
        if not class_name or not variation.strip():
            raise ValueError('Select a diagnostic class and descriptive variation.')
        return dict(recording_kind='diagnostic', split='diagnostic', class_name=class_name,
                    variation=variation.strip(), holdout_confirmed=False)
    if kind == 'trial':
        if trial_type not in TRIAL_TYPES or not action_performed.strip():
            raise ValueError('Select a trial type and describe action_performed.')
        return dict(recording_kind='trial', split='trial', trial_type=trial_type,
                    action_performed=action_performed.strip(),
                    class_name=trial_type.split('_')[0] if trial_type.endswith('_pos') else 'neutral',
                    variation=variation.strip(), take_limit=8.0, holdout_confirmed=False)
    if kind != 'take' or split not in ('train', 'holdout') or not class_name or not variation.strip():
        raise ValueError('Select take class, train/holdout split and descriptive variation.')
    if 'holdout' in variation.lower() and split != 'holdout':
        raise ValueError('Notes say holdout but DATA SPLIT is train. Select holdout first.')
    if class_name == 'rub' and not any(tag in variation for tag in ('scratch_nail_paper', 'scratch_nail_wood')):
        raise ValueError('rub means nail scratch: include scratch_nail_paper or scratch_nail_wood in notes.')
    return dict(recording_kind='take', split=split, class_name=class_name,
                variation=variation.strip(), holdout_confirmed=bool(holdout_confirmed))


def authorize_plan(plan):
    if plan['split'] == 'holdout' and not plan['holdout_confirmed']:
        raise ValueError('Confirm THIS holdout take before starting.')


def trial_phase(elapsed):
    return 'STAY STILL' if elapsed < 2 else ('ACTION ONCE NOW (~1s)' if elapsed < 3 else 'STAY STILL UNTIL STOP')


def rhythm_phase(elapsed, class_name, duration=25.0):
    """Visual cues only: actions at 1,3,...,23s, no audio-path changes."""
    expected = max(0, math.ceil((duration - 1) / 2))
    if elapsed < 1:
        return f'GET READY - first action in {1-elapsed:.1f}s'
    number = int((elapsed - 1) // 2) + 1
    if number > expected:
        return 'STAY STILL UNTIL STOP'
    phase = (elapsed - 1) % 2
    action_s = 1.0 if class_name == 'rub' else .35
    if phase < action_s:
        action = 'SCRATCH NOW (~1s)' if class_name == 'rub' else 'KNOCK ONCE NOW'
        return f'{number}/{expected}: {action}'
    return f'{number}/{expected}: STAY STILL - next action in {2-phase:.1f}s'
