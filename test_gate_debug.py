import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from models import EventDecoder, EventDecisionConfig
from gate_debug import TracedEventDecoder


class GateDebugTests(unittest.TestCase):
    def test_trace_matches_original_and_preserves_closing_buffer(self):
        cfg=EventDecisionConfig(trigger_energy=1,vote_energy=1,max_s=.2)
        frames=[(i*.05,2.,[0.,3.,0.]) for i in range(16)]
        frames += [(i*.05,0.,[3.,0.,0.]) for i in range(16,30)]
        frames += [(i*.05,2.,[0.,0.,3.]) for i in range(30,33)]
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            path=Path(folder)/'debug.jsonl'
            trace=TracedEventDecoder(cfg,['neutral','knock','rub'],path)
            original=EventDecoder(cfg)
            for t,energy,scores in frames:
                self.assertEqual(trace.step(t,energy,scores,features=np.zeros(1200)),original.step(t,energy,scores))
                self.assertEqual(trace.last_decision,original.last_decision)
                np.testing.assert_array_equal(trace.votes,original.votes)
            self.assertEqual(trace.flush(frames[-1][0]),original.flush(frames[-1][0]))
            trace.close_debug()
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            passed=[r for r in rows if r['kind']=='gate_pass']
            self.assertEqual(len(passed),19)
            self.assertTrue(any(not r['admitted'] for r in passed))
            self.assertEqual(len(passed[0]['fft_features']),1200)
            end=[r for r in rows if r['kind']=='event_end']
            self.assertEqual(end[0]['buffer']['labels'],['knock']*5)
            self.assertEqual(end[-1]['buffer']['labels'],['rub']*3)
            self.assertEqual(end[-1]['reason'],'flush')

    def test_existing_log_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'debug.jsonl';path.write_text('preserve')
            with self.assertRaises(FileExistsError):
                TracedEventDecoder(EventDecisionConfig(1,1),['neutral','knock','rub'],path)
            self.assertEqual(path.read_text(),'preserve')


if __name__=='__main__':
    unittest.main()
