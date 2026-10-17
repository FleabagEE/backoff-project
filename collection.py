"""Portable, non-pickle FFT takes and dataset export for teammate B."""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import uuid

import numpy as np


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_npz(path, **arrays):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    try:
        with temporary.open('wb') as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class CollectionSession:
    def __init__(self, config, root='data_sessions'):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.path = Path(root) / f'{stamp}_{uuid.uuid4().hex[:8]}'
        self.path.mkdir(parents=True, exist_ok=False)
        self.config = dict(config, schema_version=1, created_utc=utc_now())
        (self.path / 'config.json').write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False), encoding='utf-8')
        if Path('SETUP.md').exists():
            shutil.copy2('SETUP.md', self.path / 'SETUP_snapshot.md')

    def take_paths(self, include_excluded=False):
        return [p for p in sorted(self.path.glob('take_*.npz'))
                if include_excluded or '.excluded.' not in p.name]

    def save_take(self, class_name, X, elapsed_s, rms_fs, peak_fs, take_id=None, **notes):
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 2 or X.shape[1] != self.config['feature_count'] or not len(X):
            raise ValueError('Take must contain nonempty N x feature_count FFT amplitudes')
        if not np.isfinite(X).all():
            raise ValueError('Take contains non-finite features')
        vectors = [np.asarray(v, dtype=np.float64) for v in (elapsed_s, rms_fs, peak_fs)]
        if any(v.shape != (len(X),) for v in vectors):
            raise ValueError('One timestamp/RMS/peak is required per feature vector')
        take_id = take_id or f'take_{uuid.uuid4().hex}'
        info = dict(notes, take_id=take_id, class_name=class_name,
                    sample_count=len(X), saved_utc=utc_now())
        valid = info.get('valid', True)
        path = self.path / (take_id + ('.npz' if valid else '.excluded.npz'))
        atomic_npz(path, X=X, elapsed_s=vectors[0], rms_fs=vectors[1], peak_fs=vectors[2],
                   metadata_json=np.array(json.dumps(info, ensure_ascii=False)),
                   config_json=np.array(json.dumps(self.config, ensure_ascii=False)))
        self.write_log()
        return path

    def write_log(self):
        fields = ['take_id', 'class_name', 'performer', 'variation', 'started_utc',
                  'duration_s', 'sample_count', 'valid', 'reason', 'saved_utc', 'file']
        path = self.path / 'takes.csv'
        temporary = path.with_suffix('.csv.tmp')
        with temporary.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for p in self.take_paths(include_excluded=True):
                with np.load(p, allow_pickle=False) as data:
                    info = json.loads(str(data['metadata_json']))
                writer.writerow(dict(info, valid='.excluded.' not in p.name, file=p.name))
        os.replace(temporary, path)

    def exclude_class(self, class_name):
        """Keep originals for recovery, but omit cleared/deleted data from exports."""
        for path in self.take_paths():
            with np.load(path, allow_pickle=False) as data:
                info = json.loads(str(data['metadata_json']))
            if info['class_name'] == class_name:
                path.rename(path.with_name(path.stem + '.excluded.npz'))
        self.write_log()
        # An older aggregate must never silently survive a Clear operation.
        (self.path / 'dataset.npz').unlink(missing_ok=True)

    def export(self):
        return export_session(self.path)


def export_session(folder):
    """Rebuild dataset.npz from saved valid takes, including after restarting Python."""
    folder = Path(folder)
    config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
    features, labels, ids, times, rms, peaks, notes = [], [], [], [], [], [], []
    classes = []
    for path in sorted(folder.glob('take_*.npz')):
        if '.excluded.' in path.name:
            continue
        with np.load(path, allow_pickle=False) as data:
            info = json.loads(str(data['metadata_json']))
            if not info.get('valid', True):
                continue
            if json.loads(str(data['config_json'])) != config:
                raise ValueError(f'Capture configuration mismatch: {path}')
            X = data['X']
            if X.ndim != 2 or X.shape[1] != config['feature_count']:
                raise ValueError(f'Feature shape mismatch: {path}')
            name = info['class_name']
            if name not in classes:
                classes.append(name)
            features.append(X)
            labels.extend([classes.index(name)] * len(X))
            ids.extend([info['take_id']] * len(X))
            times.append(data['elapsed_s'])
            rms.append(data['rms_fs'])
            peaks.append(data['peak_fs'])
            notes.append(info)
    if not features:
        raise ValueError('No valid saved takes to export')
    target = folder / 'dataset.npz'
    atomic_npz(target, X=np.concatenate(features), y=np.asarray(labels, dtype=np.int64),
               class_names=np.asarray(classes), take_ids=np.asarray(ids),
               elapsed_s=np.concatenate(times), rms_fs=np.concatenate(rms), peak_fs=np.concatenate(peaks),
               config_json=np.array(json.dumps(config, ensure_ascii=False)),
               takes_json=np.array(json.dumps(notes, ensure_ascii=False)))
    return target


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Rebuild a dataset from autosaved FFT takes')
    parser.add_argument('session_folder')
    print(export_session(parser.parse_args().session_folder))
