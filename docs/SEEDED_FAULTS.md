# Seeded faults

Exercise 2, DSC 180A Methodology Assignment 7. Each section documents a fault
that was deliberately introduced to check the leakage tests and the
PostToolUse hook (`.claude/hooks/check_leakage.sh`). Output below was pasted
from the Claude Code session in which the fault was seeded; where something was
not available, that is stated.

## Fault 2 — Missing shift in cnt_roll_7

### 1. The change

One line in `src/features.py`, made with the Edit tool. `.shift(1)` was removed,
so the 7-day window includes today's count.

```diff
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
```

### 2. Failing pytest output

Command: `python -m pytest tests/test_leakage.py -q`

```
....F...                                                                 [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7   cnt_roll_3
0   2011-01-10     10.0  WINTER  ...     134....428571  2183.333333
713 2012-12-31    731.0  WINTER  ...      920.0  1789.857143  2077.333333

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.37s
```

Obtained 4389.0, expected 4414.857142857143. The other seven leakage tests
passed.

### 3. PostToolUse hook output

This message was delivered automatically to the agent after the Edit operation;
nobody ran the hook by hand. It is the hook's stderr as received, including the
hook's own `tail -20` truncation (the first lines of the pytest output are
absent because the script keeps only the last 20 lines):

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /home/vaugh/bikeshare-starter/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=============================================== short test summary info ================================================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.0) == 4414.857142857143 ± 0.0...
1 failed, 7 passed in 0.36s
```

Unavailable output:

- The literal text "exit code 2" does not appear in what the agent received.
  The message is labelled "blocking error". That it was exit 2 is known from
  the script (`check_leakage.sh` ends the failure branch with `exit 2`), not
  from the displayed output.
- The Edit tool's own result contained only "The file ... has been updated
  successfully". The hook message did not appear inline with it; it appeared
  later, after the agent's next tool call. The exact delay is not known.

### 4. Detection

- **Did the test fail?** Yes. `test_rolling_mean_excludes_today` failed
  (obtained 4389.0, expected 4414.857142857143).
- **Did the hook detect the fault?** Yes. It fired automatically on the Edit of
  `src/features.py`, re-ran `tests/test_leakage.py`, and reported the same
  failure as a blocking error.

### 5. Agent turns to identify and fix

1 agent repair turn. Claude restored .shift(1) in src/features.py, and make test passed with 18 tests.
