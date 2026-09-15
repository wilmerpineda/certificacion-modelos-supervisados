import numpy as np
import pandas as pd
from scipy import stats

from src.analysis import (
    AnalysisError,
    coefficient_table,
    fit_regression,
    model_summary,
    predict_profile,
    vif_table,
    welch_t_test,
)


def test_welch_matches_scipy_and_difference_direction():
    frame = pd.DataFrame({"score": [10, 12, 14, 16, 2, 4, 6, 8], "group": ["A"] * 4 + ["B"] * 4})
    result = welch_t_test(frame, "score", "group", ["A", "B"])
    expected = stats.ttest_ind(frame.loc[frame.group == "A", "score"], frame.loc[frame.group == "B", "score"], equal_var=False)
    assert np.isclose(result["pvalue"], expected.pvalue)
    assert np.isclose(result["difference"], 8.0)


def test_simple_regression_recovers_known_line():
    x = np.arange(1, 21, dtype=float)
    frame = pd.DataFrame({"x": x, "y": 5 + 2.5 * x})
    bundle = fit_regression(frame, "y", ["x"])
    assert np.isclose(bundle.model.params["const"], 5.0)
    assert np.isclose(bundle.model.params["x"], 2.5)
    assert np.isclose(model_summary(bundle)["r2"], 1.0)


def test_categorical_reference_and_prediction():
    frame = pd.DataFrame({
        "x": [1, 2, 3, 4, 5, 6],
        "group": ["base", "other", "base", "other", "base", "other"],
    })
    frame["y"] = 10 + 2 * frame["x"] + (frame["group"] == "other") * 4
    bundle = fit_regression(frame, "y", ["x"], ["group"], {"group": "base"})
    table = coefficient_table(bundle)
    assert "group = other" in table["Variable"].tolist()
    assert np.isclose(bundle.model.params["group = other"], 4.0)
    assert np.isclose(predict_profile(bundle, {"x": 7, "group": "other"}), 28.0)


def test_vif_is_available_for_multiple_predictors():
    rng = np.random.default_rng(11)
    frame = pd.DataFrame({"x1": rng.normal(size=100), "x2": rng.normal(size=100)})
    frame["y"] = 3 + frame.x1 - 2 * frame.x2 + rng.normal(scale=.2, size=100)
    bundle = fit_regression(frame, "y", ["x1", "x2"])
    result = vif_table(bundle)
    assert set(result["Variable"]) == {"x1", "x2"}
    assert np.isfinite(result["VIF"]).all()


def test_perfect_collinearity_is_blocked():
    frame = pd.DataFrame({"x1": range(1, 10), "x2": range(2, 20, 2), "y": range(3, 12)})
    try:
        fit_regression(frame, "y", ["x1", "x2"])
    except AnalysisError as exc:
        assert "redundante" in str(exc)
    else:
        raise AssertionError("La colinealidad perfecta debía bloquear el modelo")


def test_missing_values_are_dropped_only_for_selected_columns():
    frame = pd.DataFrame({
        "x": [1.0, 2.0, np.nan, 4.0, 5.0],
        "y": [2.0, 4.0, 6.0, 8.0, 10.0],
        "unused": [np.nan] * 5,
    })
    bundle = fit_regression(frame, "y", ["x"])
    assert int(bundle.model.nobs) == 4


def test_high_cardinality_category_is_blocked():
    frame = pd.DataFrame({
        "x": np.arange(25, dtype=float),
        "category": [f"nivel_{index}" for index in range(25)],
        "y": np.arange(25, dtype=float) * 2 + 1,
    })
    try:
        fit_regression(frame, "y", ["x"], ["category"])
    except AnalysisError as exc:
        assert "20 o menos" in str(exc)
    else:
        raise AssertionError("La variable de alta cardinalidad debía bloquearse")
