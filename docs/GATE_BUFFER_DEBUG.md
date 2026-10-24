# Energy-gate / event-buffer diagnosis

Use the existing v1 (or matched v2) launch command with `--decision event --gate-debug`.
This is opt-in logging only: no retraining, capture/FFT changes, threshold changes or vote-rule changes.

- Terminal `[BUFFER]` contains only the current label sequence. Numeric fields and
  admission status are saved to JSONL `gate_pass` records, not printed.
- `admitted=False`: passed the energy gate but was not buffered (e.g. waiting for quiet rearm).
  Passing the gate never implies the model must predict knock/rub: neutral can win.
- Terminal `[BUFFER END]` contains the complete pre-clear label sequence. JSONL
  `event_end` records also contain score vectors/counts and the final decision.
  Includes the last voting window and explicit trial-stop flush.
- The per-window buffer is empty after an event closes; its full contents are in BUFFER END.
- JSONL auto-saves under `trial_logs/gate_debug_<timestamp>_<unique>.jsonl`, never overwriting
  existing files. The startup JSONL record stores absolute model/parameter paths, SHA256s and decoder config.
- JSONL additionally contains the existing full1200 processed FFT features for every gate-passing
  window (including unbuffered ones). These are NOT raw PCM and are not training takes.
- Quiet/below-gate windows are not logged individually; their effect is observed at event closure.
- Logging is synchronous and verbose; console/file I/O adds overhead. Use for short diagnostic
  runs, then omit the flag for normal live latency testing. No sensor test was performed by
  automated regression tests. Actual microphone/sensor actions must be supplied by A.

Close the current inference GUI, restart with the added flag, keep the CMD terminal visible.
First wait quietly2s, do one knuckle knock, wait2s, then one ~1s nail scratch and wait2s.
The slide receiver may stay open; only one inference process should use the audio device.
95 repository tests passed, including decoder equality and final-buffer preservation tests.
