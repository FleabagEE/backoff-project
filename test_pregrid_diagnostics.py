import unittest
from pregrid_diagnostics import active_runs,gate_statistics


class PregridTests(unittest.TestCase):
    def test_gate_or_not_two_independent_rejections(self):
        result=gate_statistics([.1,.4,.1,.4],[.2,.2,.8,.8],.3,.7)
        self.assertEqual(result['rms_fail_fraction'],.5)
        self.assertEqual(result['peak_fail_fraction'],.5)
        self.assertEqual(result['both_fail_gate_inactive_fraction'],.25)

    def test_single_window_knock_and_separated_events_not_combined(self):
        self.assertEqual(active_runs([False,True,False,True,True,False]),[1,2])
        self.assertEqual(active_runs([False,False]),[])
        self.assertEqual(active_runs([True]),[1])


if __name__=='__main__':
    unittest.main()
