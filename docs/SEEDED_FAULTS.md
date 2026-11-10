# Seeded faults

Exercise 2, DSC 180A Methodology Assignment 7. Each section documents a fault
that was deliberately introduced to check the leakage tests and the
PostToolUse hook (`.claude/hooks/check_leakage.sh`). Output below was pasted
from the Claude Code session in which the fault was seeded; where something was
not available, that is stated.

## Fault 1 — Forbidden casual feature

### 1. The change

Fault commit `20660ca` ("test: seed fault 1 - allow forbidden casual feature")
changed `feature_columns()` in `src/features.py` from excluding `FORBIDDEN` to
excluding `FORBIDDEN - {"casual"}`, so `casual` (which satisfies
`casual + registered == cnt`) reached the feature set. `FORBIDDEN` in
`src/config.py` was not touched.

```diff
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in (FORBIDDEN - {"casual"})]
```

### 2. Failing pytest output

Command: `python -m pytest tests/test_leakage.py -k "forbidden"`. This was run by
the agent by hand after the Edit; it is not the hook's output.

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.7.0
rootdir: /home/vaugh/bikeshare-starter
plugins: anyio-4.16.0
collected 8 items / 7 deselected / 1 selected

tests/test_leakage.py F                                                  [100%]

=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7   cnt_roll_3
0   2011-01-10     10.0  WINTER  ...     134....142857  2183.333333
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  2077.333333

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_3', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
======================= 1 failed, 7 deselected in 0.81s ========================
```

### 3. PostToolUse hook observation

No automatic PostToolUse hook stderr was observed during the original fault
introduction. The hook's output is **unavailable** for this fault: nothing from
`check_leakage.sh` appeared after the Edit, so none is pasted here.

Investigation found that `.claude/hooks/check_leakage.sh` lacked executable
permissions (`ls -l` showed `-rw-r--r--` during the session). The hook is
configured in `.claude/settings.json` (`PostToolUse`, matcher `Edit|Write`), so
the missing execute bit is the explanation recorded for the hook not firing. This
session did not separately re-run Fault 1 with the hook disabled to prove it;
the later Fault 2 run, with the script executable, is where the hook did fire.

### 4. The permission fix

Commit `3401393` ("fix: make leakage verification hook executable") changed the
file mode of `.claude/hooks/check_leakage.sh` from `100644` to `100755`
(`old mode 100644`, `new mode 100755`). No content change.

### 5. Repair

Commit `168dab0` ("fix: restore forbidden-column exclusion after fault 1")
restored the correct filter:

```diff
-    return [c for c in numeric if c not in (FORBIDDEN - {"casual"})]
+    return [c for c in numeric if c not in FORBIDDEN]
```

`make test` afterwards: 18 passed.

### 6. Detection

- **Did the test fail?** Yes. `test_no_forbidden_features` failed with
  `AssertionError: forbidden columns in feature set: {'casual'}`.
- **Did the hook detect the fault?** No. It produced no output at the time,
  consistent with the missing executable bit (see section 3).

### 7. Agent turns to identify and fix

1 agent repair turn.

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
