from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor


class AnalysisError(ValueError):
    """Error que puede explicarse al estudiante sin una traza técnica."""


@dataclass
class RegressionBundle:
    model: Any
    clean_data: pd.DataFrame
    design_matrix: pd.DataFrame
    response: pd.Series
    numeric_predictors: list[str]
    categorical_predictors: list[str]
    references: dict[str, str]
    encoded_columns: dict[str, list[str]]


def _numeric(series: pd.Series, name: str) -> pd.Series:
    converted = pd.to_numeric(series, errors="coerce")
    if converted.notna().sum() < 3:
        raise AnalysisError(f"{name} no contiene suficientes valores numéricos válidos.")
    return converted


def welch_t_test(
    data: pd.DataFrame,
    outcome: str,
    group: str,
    levels: list[Any],
    alpha: float = 0.05,
) -> dict[str, Any]:
    if len(levels) != 2:
        raise AnalysisError("Selecciona exactamente dos grupos para la prueba t.")
    frame = data[[outcome, group]].copy()
    frame[outcome] = _numeric(frame[outcome], outcome)
    frame = frame.dropna()
    samples = [frame.loc[frame[group] == level, outcome].astype(float) for level in levels]
    if any(len(sample) < 2 for sample in samples):
        raise AnalysisError("Cada grupo necesita al menos dos observaciones válidas.")
    if any(np.isclose(sample.var(ddof=1), 0) for sample in samples):
        raise AnalysisError("La prueba requiere variación dentro de ambos grupos.")

    result = stats.ttest_ind(samples[0], samples[1], equal_var=False, nan_policy="omit")
    n1, n2 = len(samples[0]), len(samples[1])
    mean1, mean2 = float(samples[0].mean()), float(samples[1].mean())
    var1, var2 = float(samples[0].var(ddof=1)), float(samples[1].var(ddof=1))
    se = np.sqrt(var1 / n1 + var2 / n2)
    df_num = (var1 / n1 + var2 / n2) ** 2
    df_den = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = df_num / df_den
    difference = mean1 - mean2
    critical = stats.t.ppf(1 - alpha / 2, df)
    ci = (difference - critical * se, difference + critical * se)

    return {
        "outcome": outcome,
        "group": group,
        "levels": [str(levels[0]), str(levels[1])],
        "n": [n1, n2],
        "means": [mean1, mean2],
        "difference": difference,
        "statistic": float(result.statistic),
        "pvalue": float(result.pvalue),
        "df": float(df),
        "ci": (float(ci[0]), float(ci[1])),
        "alpha": alpha,
        "significant": bool(result.pvalue < alpha),
        "used_rows": n1 + n2,
        "dropped_rows": int(len(data) - n1 - n2),
        "samples": samples,
    }


def fit_regression(
    data: pd.DataFrame,
    outcome: str,
    numeric_predictors: list[str],
    categorical_predictors: list[str] | None = None,
    references: dict[str, Any] | None = None,
) -> RegressionBundle:
    categorical_predictors = categorical_predictors or []
    references = {key: str(value) for key, value in (references or {}).items()}
    predictors = numeric_predictors + categorical_predictors
    if not predictors:
        raise AnalysisError("Selecciona al menos una variable explicativa.")
    if outcome in predictors:
        raise AnalysisError("La variable respuesta no puede usarse también como explicativa.")

    frame = data[[outcome] + predictors].copy()
    frame[outcome] = pd.to_numeric(frame[outcome], errors="coerce")
    for column in numeric_predictors:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna()
    if len(frame) < len(predictors) + 3:
        raise AnalysisError("Hay muy pocas filas completas para la cantidad de variables elegidas.")
    if frame[outcome].nunique() < 2:
        raise AnalysisError("La variable respuesta necesita variación.")

    parts: list[pd.DataFrame] = []
    if numeric_predictors:
        numeric = frame[numeric_predictors].astype(float)
        constants = [column for column in numeric.columns if numeric[column].nunique() < 2]
        if constants:
            raise AnalysisError("Estas variables no cambian: " + ", ".join(constants))
        parts.append(numeric)

    encoded_columns: dict[str, list[str]] = {}
    normalized_references: dict[str, str] = {}
    for column in categorical_predictors:
        values = frame[column].astype(str)
        levels = sorted(values.unique().tolist())
        if len(levels) < 2:
            raise AnalysisError(f"{column} necesita al menos dos categorías.")
        if len(levels) > 20:
            raise AnalysisError(
                f"{column} tiene {len(levels)} categorías. Para este laboratorio usa una variable con 20 o menos."
            )
        reference = references.get(column, levels[0])
        if reference not in levels:
            raise AnalysisError(f"La categoría de referencia de {column} no aparece en los datos válidos.")
        ordered = [reference] + [level for level in levels if level != reference]
        categorical = pd.Categorical(values, categories=ordered)
        dummies = pd.get_dummies(categorical, prefix=column, prefix_sep=" = ", drop_first=True, dtype=float)
        dummies.index = frame.index
        encoded_columns[column] = dummies.columns.tolist()
        normalized_references[column] = reference
        parts.append(dummies)

    matrix = pd.concat(parts, axis=1).astype(float)
    design = sm.add_constant(matrix, has_constant="add")
    if np.linalg.matrix_rank(design.to_numpy()) < design.shape[1]:
        raise AnalysisError(
            "El modelo contiene información redundante (colinealidad perfecta). Retira una variable relacionada."
        )

    response = frame[outcome].astype(float)
    model = sm.OLS(response, design).fit()
    return RegressionBundle(
        model=model,
        clean_data=frame,
        design_matrix=design,
        response=response,
        numeric_predictors=numeric_predictors,
        categorical_predictors=categorical_predictors,
        references=normalized_references,
        encoded_columns=encoded_columns,
    )


def coefficient_table(bundle: RegressionBundle) -> pd.DataFrame:
    model = bundle.model
    ci = model.conf_int(alpha=0.05)
    table = pd.DataFrame(
        {
            "Coeficiente": model.params,
            "Error estándar": model.bse,
            "t": model.tvalues,
            "p-value": model.pvalues,
            "IC 95% inferior": ci[0],
            "IC 95% superior": ci[1],
        }
    )
    table.index.name = "Variable"
    return table.reset_index()


def model_summary(bundle: RegressionBundle) -> dict[str, float]:
    model = bundle.model
    return {
        "n": int(model.nobs),
        "r2": float(model.rsquared),
        "r2_adj": float(model.rsquared_adj),
        "f": float(model.fvalue) if model.fvalue is not None else np.nan,
        "f_pvalue": float(model.f_pvalue) if model.f_pvalue is not None else np.nan,
        "rmse": float(np.sqrt(np.mean(model.resid**2))),
        "aic": float(model.aic),
    }


def vif_table(bundle: RegressionBundle) -> pd.DataFrame:
    matrix = bundle.design_matrix.drop(columns="const", errors="ignore")
    if matrix.shape[1] < 2:
        return pd.DataFrame(columns=["Variable", "VIF", "Lectura"])
    rows = []
    values = matrix.to_numpy(dtype=float)
    for index, column in enumerate(matrix.columns):
        value = float(variance_inflation_factor(values, index))
        if not np.isfinite(value):
            reading = "Redundancia severa"
        elif value >= 10:
            reading = "Señal fuerte: investigar"
        elif value >= 5:
            reading = "Señal moderada: revisar"
        else:
            reading = "Sin alerta importante"
        rows.append({"Variable": column, "VIF": value, "Lectura": reading})
    return pd.DataFrame(rows)


def predict_profile(bundle: RegressionBundle, profile: dict[str, Any]) -> float:
    row = {column: 0.0 for column in bundle.design_matrix.columns}
    row["const"] = 1.0
    for column in bundle.numeric_predictors:
        row[column] = float(profile[column])
    for column in bundle.categorical_predictors:
        selected = str(profile[column])
        reference = bundle.references[column]
        if selected != reference:
            encoded = f"{column} = {selected}"
            if encoded not in row:
                raise AnalysisError(f"La categoría {selected} no fue observada al entrenar el modelo.")
            row[encoded] = 1.0
    frame = pd.DataFrame([row], columns=bundle.design_matrix.columns)
    return float(bundle.model.predict(frame).iloc[0])
