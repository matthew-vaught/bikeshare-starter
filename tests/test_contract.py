"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import FORBIDDEN, LAG_WARMUP, TARGET
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7; their
    union is 7 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS


# --- Every raw column must be classified ---------------------------------
# A column that is neither forbidden, permitted, nor the date was never
# reviewed for leakage. Adding one to the CSV must force a decision here.
DATE_COL = "dteday"

# Permitted raw columns, spelled out on purpose (not derived from
# feature_columns(), which only sees engineered numeric columns).
PERMITTED_RAW = {
    # used directly as model features
    "temp", "atemp", "hum", "windspeed",
    # encoded into is_holiday / is_workday / weather_severity
    "holiday", "workday", "weather",
    # calendar duplicates of dteday; not model inputs (dayofweek and the
    # month encodings are rebuilt from dteday), but reviewed and harmless
    "season", "mnth", "weekday",
}


def unclassified_columns(columns) -> set[str]:
    """Columns that are not FORBIDDEN, not permitted, and not the date."""
    return set(columns) - FORBIDDEN - PERMITTED_RAW - {DATE_COL}


def test_every_raw_column_is_classified(raw):
    extra = unclassified_columns(raw.columns)
    assert not extra, (
        f"unclassified raw columns {sorted(extra)}: add each to FORBIDDEN in "
        "src/config.py or to PERMITTED_RAW here, after checking it for leakage"
    )


def test_unclassified_check_can_fail(raw):
    """Proves the check bites, using a synthetic column; the CSV is untouched."""
    assert unclassified_columns(raw.columns) == set()
    assert unclassified_columns([*raw.columns, "surprise_col"]) == {"surprise_col"}
    # and a renamed leak is not waved through just because casual is forbidden
    assert unclassified_columns([*raw.columns, "casual_2"]) == {"casual_2"}


def test_permitted_and_forbidden_do_not_overlap():
    assert not (PERMITTED_RAW & FORBIDDEN), PERMITTED_RAW & FORBIDDEN
