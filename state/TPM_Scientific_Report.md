# TPM Scientific Validation Report

Generated (UTC): `2026-03-03T15:42:45.295161`

## Configuration

- n_ticks: 9000
- window_size: 30
- percentile: 85.0
- safety_floor: 0.2
- min_alpha_delta: 0.001
- alert_cooldown_ticks: 8
- pre_event_window: 30

## Test Results

| Test | Metric | p-value | Pass | Notes |
|---|---:|---:|:---:|---|
| classification_f1 | 0.0296 | 1.0000 | ❌ | precision=0.191, recall=0.016, chi2_p=0.0034 |
| lead_time_ticks | 14.5000 | 0.5711 | ❌ | lead_events=2 |
| alpha_separation_cohens_d | 0.7268 | 0.0025 | ❌ | frozen vs normal alpha separation |
| false_positive_rate | 0.0067 | 0.0000 | ✅ | fp_rate=0.007 |
| strategy_sharpe | 2.9286 | 0.6933 | ❌ | simple short-on-alert proxy |

**Passed:** 1/5

## Notes

- Chi² uses zero-cell guards to avoid contingency crashes.
- Detector includes cooldown + alpha delta gate to reduce alert spam clusters.
- This is synthetic validation; out-of-sample real-market checks remain mandatory.