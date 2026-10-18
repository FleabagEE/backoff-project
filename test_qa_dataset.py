"""Protect the final-data split and raw-file provenance during QA."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from collection import CollectionSession
from qa_dataset import audit, load_takes


class QATests(unittest.TestCase):
    def test_corrected_holdout_is_disjoint_and_raw_takes_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = CollectionSession(dict(feature_count=4, session_type='final'), tmp)
            paths = []
            for cls, offset in [('neutral', 0), ('knock', 1), ('rub', 2)]:
                for j in range(3):
                    X = np.full((5, 4), .1)
                    X[:, offset] += 10
                    paths.append(session.save_take(cls, X, [.1,.2,.3,.4,.5], [.001]*5, [.1]*5,
                                                   take_id=f'take_{cls}_{j}', split='train', duration_s=25,
                                                   variation='quiet' if cls=='neutral' else 'test'))
            hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            manifest = Path(tmp)/'splits.csv'
            manifest.write_text('take_id,split,reason\n' + ''.join(
                f'take_{cls}_2,holdout,planned holdout\n' for cls in ('neutral','knock','rub')))
            out = Path(tmp)/'review'
            result = audit(session.path, out, manifest)
            self.assertEqual(result['counts']['train'], dict(neutral=2, knock=2, rub=2))
            self.assertEqual(result['counts']['holdout'], dict(neutral=1, knock=1, rub=1))
            with np.load(out/'train.npz', allow_pickle=False) as train, np.load(out/'holdout.npz', allow_pickle=False) as test:
                self.assertFalse(set(train['take_ids']) & set(test['take_ids']))
                self.assertTrue(np.all(test['split'] == 'holdout'))
            baseline = result['baseline']
            self.assertFalse(set(baseline['fitted_take_ids']) & set(baseline['holdout_take_ids']))
            for fold in baseline['folds']:
                self.assertFalse(set(fold['fit_take_ids']) & set(fold['test_take_ids']))
            for p, digest in hashes.items():
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), digest)
                with np.load(p, allow_pickle=False) as data:
                    self.assertEqual(json.loads(str(data['metadata_json']))['split'], 'train')
            with self.assertRaises(FileExistsError):
                audit(session.path, out, manifest)
            with self.assertRaisesRegex(ValueError, 'missing/excluded'):
                load_takes(session.path, {'nonexistent': dict(split='holdout', reason='mistake')})

    def test_pilot_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = CollectionSession(dict(feature_count=4), tmp)
            with self.assertRaisesRegex(ValueError, 'pilot'):
                load_takes(session.path)


if __name__ == '__main__':
    unittest.main()
