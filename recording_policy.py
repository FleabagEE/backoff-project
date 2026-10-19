"""Recording labels and trial protocol only; no audio/feature processing."""
TRIAL_TYPES = ('knock_pos', 'rub_pos', 'knock_neg', 'rub_neg')


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
    if class_name == 'rub' and 'scratch_nail_paper' not in variation:
        raise ValueError('rub now means nail scratch on paper: include scratch_nail_paper in notes.')
    return dict(recording_kind='take', split=split, class_name=class_name,
                variation=variation.strip(), holdout_confirmed=bool(holdout_confirmed))


def authorize_plan(plan):
    if plan['split'] == 'holdout' and not plan['holdout_confirmed']:
        raise ValueError('Confirm THIS holdout take before starting.')


def trial_phase(elapsed):
    return 'STAY STILL' if elapsed < 2 else ('ACTION ONCE NOW (~1s)' if elapsed < 3 else 'STAY STILL UNTIL STOP')
