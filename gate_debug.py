"""Opt-in observer for B's event buffer. No capture or decision changes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
from models import EventDecoder


class TracedEventDecoder(EventDecoder):
    def __init__(self, config, class_names, path):
        self.debug_path = Path(path).resolve()
        self.debug_path.parent.mkdir(parents=True, exist_ok=True)
        self.debug_file = self.debug_path.open('x', encoding='utf-8', buffering=1)
        self.frame_number = 0
        super().__init__(config, class_names)

    def emit(self, kind, **values):
        row = dict(kind=kind, utc=datetime.now(timezone.utc).isoformat(), **values)
        self.debug_file.write(json.dumps(row, allow_nan=False)+'\n')
        return row

    def snapshot(self):
        scores = [np.asarray(s).tolist() for s in self.votes]
        labels = [self.class_names[int(np.argmax(s))] for s in self.votes]
        return dict(labels=labels, scores=scores, counts=dict(zip(self.class_names,self.vote_counts().tolist())))

    def _close(self, t, reason):
        # Read buffer BEFORE B clears it; includes the final voting frame.
        buffer = self.snapshot()
        result = super()._close(t, reason)
        self.emit('event_end', monotonic_s=float(t), reason=reason, final=result,
                  decision=dict(self.last_decision), buffer=buffer)
        print('[BUFFER END] '+str(buffer['labels']), flush=True)
        return result

    def step(self, t, energy, scores, features=None):
        self.frame_number += 1
        collecting_before, armed_before = self.collecting, self.armed
        previous = self.last_decision
        passed = energy > self.config.vote_energy
        # Exact admission condition from B's decoder, including trigger > vote cases.
        admitted = bool(passed and (collecting_before or
                        (armed_before and energy > self.config.trigger_energy)))
        output = super().step(t, energy, scores)
        if passed:
            raw = self.class_names[int(np.argmax(scores))]
            buffer = self.snapshot()
            self.emit('gate_pass', frame=self.frame_number, monotonic_s=float(t),
                energy=float(energy), threshold=float(self.config.vote_energy),
                ratio=float(energy/self.config.vote_energy), raw=raw,
                scores=dict(zip(self.class_names,np.asarray(scores).tolist())),
                admitted=admitted, armed_before=armed_before, collecting=self.collecting,
                event_closed=self.last_decision is not previous, output=output, buffer=buffer,
                fft_features=None if features is None else np.asarray(features).tolist())
            if self.last_decision is previous:
                print('[BUFFER] '+str(buffer['labels']), flush=True)
        return output

    def close_debug(self):
        self.debug_file.close()
