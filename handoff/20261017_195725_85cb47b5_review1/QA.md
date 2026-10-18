# Final dataset QA

Source: `data_sessions/20261017_195725_85cb47b5`

Takes: {'train': {'neutral': 16, 'rub': 10, 'knock': 10}, 'holdout': {'neutral': 3, 'knock': 2, 'rub': 2}}
Total feature rows: 22827
Quiet P95 RMS: 0.2223% FS (descriptive, not an energy gate)
Short takes (<24 s): ['take_425ba9f565b8400fb2d3162491a16836']
Takes reaching 70% FS: ['take_5b79be1ac4df4a498034ad5e5ec65641', 'take_74408b77ab0b49859525b0e326fcfa93']
Rub takes with median at/below quiet P95: ['take_0bf7c3ade0e144e0bfccd39628288b26', 'take_0eadc71ca74342919d96c827bf099ec3', 'take_39043f99b8ff4f1eb49bafa77454c3a9', 'take_4ce894748a284e519f28320ba24f9cd2', 'take_5d3c2641ccbb4c14b673485df74ca119', 'take_a439107c6f3044aa85516de7aa94d8a4', 'take_b6d9515fb51e4804b72f4020c7145aa7', 'take_ca75d71230b84a0988de718078d8c069', 'take_d14b0de5882e4dc48ad4f09fa37c7c65', 'take_d1cfff40ee8940fe8321b8cf06801d31']

Recipe: log1p amplitudes, StandardScaler, LinearSVC. GroupKFold by take;
all preprocessing fits inside training folds. Holdout excluded from fitting/tuning.
Full confusion matrices, per-class metrics and fold IDs: qa_report.json.

Single performer A, one table, correlated windows. This is not a bakeoff trial-set test.
Raw takes are untouched. Effective split corrections are recorded in the manifest.
Use train.npz for fitting; holdout.npz for one final evaluation only.

grouped_cv window accuracy: 0.5151
Confusion matrix rows=actual, columns=predicted; neutral, knock, rub:
```
[[5381 1458 1593]
 [2084 2264  983]
 [2154  988 2190]]
```

holdout window accuracy: 0.7018
Confusion matrix rows=actual, columns=predicted; neutral, knock, rub:
```
[[1268  146  185]
 [ 357  612   97]
 [ 219  109  739]]
```
