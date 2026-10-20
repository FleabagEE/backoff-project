"""Live event-level decisions: collect first, decide once."""
import unittest

from models import EventDecisionConfig, EventDecoder

GATE = 100.0
FRAME_S = 0.047  # ~21 GUI frames per second
SCORES = {'N': [1.0, -1.0, -1.0], 'K': [-1.0, 1.0, -1.0], 'R': [-1.0, -1.0, 1.0]}


def run(frames, decoder=None, start=0.0):
    """frames: string of Q (quiet, below gate) or N/K/R (above gate, model label).
    Returns the decoder and the output label of every frame."""
    decoder = decoder or EventDecoder(EventDecisionConfig(trigger_energy=GATE, vote_energy=GATE))
    out = []
    for i, f in enumerate(frames):
        energy = 0.0 if f == 'Q' else 500.0
        out.append(decoder.step(start + i * FRAME_S, energy, SCORES.get(f, SCORES['N'])))
    return decoder, out


def emitted(out):
    """Non-neutral labels in order, collapsing repeats (what C / the trial set sees change to)."""
    result = []
    for label in out:
        if label != 'neutral' and (not result or result[-1] != label):
            result.append(label)
    return result


class EventDecoderTests(unittest.TestCase):
    def test_knock_ends_early_and_is_held(self):
        decoder, out = run('Q' * 10 + 'KKKK' + 'Q' * 30)
        self.assertEqual(emitted(out), ['knock'])
        self.assertEqual(out[:14], ['neutral'] * 14)  # nothing leaks while collecting
        first = out.index('knock')
        latency = (first - 10) * FRAME_S  # from the first knock frame
        self.assertLess(latency, 0.6)
        held = out.count('knock')
        self.assertGreaterEqual(held * FRAME_S, 0.2)
        self.assertEqual(out[-1], 'neutral')
        self.assertEqual(decoder.last_decision['reason'], 'end_quiet')

    def test_scratch_onset_knocks_never_leak(self):
        # A's live scratch #1: K x5 -> R x20 -> K x1, continuous
        _, out = run('Q' * 10 + 'K' * 5 + 'R' * 20 + 'K' + 'Q' * 30)
        self.assertEqual(emitted(out), ['rub'])
        self.assertNotIn('knock', out)

    def test_continuous_scratch_decides_at_max_and_triggers_once(self):
        decoder, out = run('Q' * 5 + 'R' * 60 + 'Q' * 30)  # ~2.8 s of scratching
        self.assertEqual(emitted(out), ['rub'])
        self.assertEqual(decoder.last_decision['reason'], 'max_s')
        first = out.index('rub')
        self.assertAlmostEqual((first - 5) * FRAME_S, 1.0, delta=FRAME_S)
        # still scratching ~1.8 s after the decision: no second event until quiet re-arm,
        # so rub is output only during one 0.25 s hold
        self.assertFalse(decoder.collecting)
        self.assertLessEqual(out.count('rub') * FRAME_S, 0.25 + FRAME_S)

    def test_isolated_frame_is_rejected_by_min_votes(self):
        # A's scratch #5 onset: one K, ~1.3 s quiet, then the real scratch
        decoder, out = run('Q' * 5 + 'K' + 'Q' * 28 + 'R' * 22 + 'Q' * 30)
        self.assertEqual(emitted(out), ['rub'])

    def test_quiet_noise_frames_emit_nothing(self):
        _, out = run('Q' * 10 + 'N' + 'Q' * 10 + 'NN' + 'Q' * 20)
        self.assertEqual(emitted(out), [])

    def test_neutral_majority_emits_nothing(self):
        _, out = run('Q' * 5 + 'NNNK' + 'Q' * 20)
        self.assertEqual(emitted(out), [])

    def test_tie_goes_to_higher_mean_score(self):
        decoder = EventDecoder(EventDecisionConfig(trigger_energy=GATE, vote_energy=GATE))
        decoder.step(0.0, 500, [-1.5, 1.2, -0.8])
        decoder.step(0.05, 500, [-1.1, 0.8, -0.6])
        decoder.step(0.10, 500, [-0.6, -0.1, 0.1])
        decoder.step(0.15, 500, [-0.5, -0.2, 0.05])
        self.assertEqual(decoder.decide(), 'knock')  # 2-2 tie, knock mean 0.43 > rub -0.31

    def test_two_actions_after_quiet_are_two_events(self):
        _, out = run('Q' * 5 + 'KKKK' + 'Q' * 25 + 'R' * 22 + 'Q' * 30)
        self.assertEqual(emitted(out), ['knock', 'rub'])

    def test_flush_decides_open_event(self):
        decoder, out = run('Q' * 5 + 'R' * 8)  # SPACE pressed mid-scratch
        self.assertTrue(decoder.collecting)
        self.assertEqual(decoder.flush(1.0), 'rub')
        self.assertEqual(decoder.last_decision['reason'], 'flush')
        self.assertIsNone(decoder.flush(1.1))
        decoder.reset()
        self.assertFalse(decoder.collecting)

    def test_trigger_can_be_higher_than_vote_gate(self):
        decoder = EventDecoder(EventDecisionConfig(trigger_energy=1000.0, vote_energy=GATE))
        _, out = run('Q' * 5 + 'KKKK' + 'Q' * 30, decoder)  # energy 500 < trigger
        self.assertEqual(emitted(out), [])


if __name__ == '__main__':
    unittest.main()
