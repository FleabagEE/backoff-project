# Original final-session captures: preserve these

NPZ data is local/cloud-archive only; GitHub tracks this session's small metadata
and reports. See HANDOFF_B.md for the cloud-link placeholder and archive details.

43 takes, all performer A. Source files have NOT been relabeled or overwritten.
GUI split was accidentally left train for the intended holdout recordings.
Do NOT train on every raw take or trust original split=train as an effective split.

Use corrected separate train/holdout NPZ files and QA in:
handoff/20261017_195725_85cb47b5_review1/

Explicit per-take corrections: docs/final_split_corrections.csv (7 held-out takes).
One extra neutral holdout and one 20.297 s neutral drag take are retained.
The GUI's training buffer also includes intended holdout: do not train from it.
The existing pilot session 20261017_013429_24eda79c is separate and not included.
