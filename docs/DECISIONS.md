# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-10 (Exercise 1): Tested `cnt_roll_3`, the mean ridership over calendar days d-1 through d-3, built after `reindex_to_calendar` with `.shift(1)` before `.rolling(3)`; every input is known before prediction time, so there is no target leakage. Validation R^2 ridge 0.6475 -> 0.6439 (delta -0.0036), hgb 0.2185 -> 0.1983 (delta -0.0202): no improvement (below the 0.01 threshold, and both moved down), so it would be rejected for deployment. The working implementation and its test are retained in this assignment repository as evidence of Exercise 1.
