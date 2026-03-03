# TPM Scientific Validation Report

Generated (UTC): `2026-03-03T16:06:00.150731`

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
| classification_f1 | 0.5811 | 0.0025 | ✅ | precision=0.646, recall=0.528, chi2_p=0.0000 |
| lead_time_ticks | 29.6667 | 0.0025 | ✅ | lead_events=6 |
| alpha_separation_cohens_d | 3.1332 | 0.0025 | ✅ | frozen vs normal alpha separation |
| false_positive_rate | 0.0287 | 0.0000 | ✅ | fp_rate=0.029 |
| strategy_sharpe | 30.8603 | 0.0025 | ✅ | simple short-on-alert proxy |

**Passed:** 5/5

## Notes

- Chi² uses zero-cell guards to avoid contingency crashes.
- Detector includes cooldown + alpha delta gate to reduce alert spam clusters.
- This is synthetic validation; out-of-sample real-market checks remain mandatory.