from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from src.analysis import AnalysisError


@dataclass
class MergeResult:
    data: pd.DataFrame
    matched: int
    campaign_only: int
    client_only: int


@dataclass
class ClassificationBundle:
    metrics: pd.DataFrame
    predictions: pd.DataFrame
    curves: dict[str, pd.DataFrame]
    models: dict[str, Pipeline]
    train_rows: int
    test_rows: int
    positive_rate: float
    target: str
    positive_class: str
    features: list[str]


def merge_client_campaign(
    clients: pd.DataFrame,
    campaigns: pd.DataFrame,
    key: str,
    how: str = "inner",
) -> MergeResult:
    if key not in clients or key not in campaigns:
        raise AnalysisError(f"La llave {key} debe aparecer en ambas tablas.")
    if clients[key].isna().any() or campaigns[key].isna().any():
        raise AnalysisError("La llave contiene valores vacíos. Corrígelos antes de cruzar.")
    if clients[key].duplicated().any():
        raise AnalysisError("La tabla de clientes tiene llaves duplicadas.")
    if campaigns[key].duplicated().any():
        raise AnalysisError("La tabla de campañas tiene llaves duplicadas.")
    if how not in {"inner", "left"}:
        raise AnalysisError("El cruce debe ser interno o izquierdo.")

    client_keys = set(clients[key].astype(str))
    campaign_keys = set(campaigns[key].astype(str))
    matched = len(client_keys & campaign_keys)
    campaign_only = len(campaign_keys - client_keys)
    client_only = len(client_keys - campaign_keys)
    merged = campaigns.merge(
        clients,
        on=key,
        how=how,
        validate="one_to_one",
        suffixes=("_campana", "_cliente"),
    )
    return MergeResult(merged, matched, campaign_only, client_only)


def _feature_types(data: pd.DataFrame, features: list[str]) -> tuple[list[str], list[str]]:
    numeric = [column for column in features if pd.api.types.is_numeric_dtype(data[column])]
    categorical = [column for column in features if column not in numeric]
    return numeric, categorical


def _preprocessor(numeric: list[str], categorical: list[str], scale: bool, missing_as_category: bool) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    categorical_strategy = "constant" if missing_as_category else "most_frequent"
    categorical_fill = "Sin dato" if missing_as_category else None
    categorical_imputer = SimpleImputer(strategy=categorical_strategy, fill_value=categorical_fill)
    return ColumnTransformer(
        [
            ("numeric", Pipeline(numeric_steps), numeric),
            (
                "categorical",
                Pipeline([
                    ("impute", categorical_imputer),
                    ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
                ]),
                categorical,
            ),
        ],
        remainder="drop",
    )


def _metric_row(name: str, actual: np.ndarray, predicted: np.ndarray, probability: np.ndarray) -> dict[str, float | str | int]:
    tn, fp, fn, tp = confusion_matrix(actual, predicted, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {
        "Modelo": name,
        "Exactitud": accuracy_score(actual, predicted),
        "Precisión": precision_score(actual, predicted, zero_division=0),
        "Recall": recall_score(actual, predicted, zero_division=0),
        "F1": f1_score(actual, predicted, zero_division=0),
        "Especificidad": specificity,
        "AUC": roc_auc_score(actual, probability),
        "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
    }


def evaluate_classifiers(
    data: pd.DataFrame,
    target: str,
    positive_class: str,
    features: list[str],
    missing_as_category: bool = True,
    drop_incomplete: bool = False,
    test_size: float = 0.25,
    random_state: int = 42,
    algorithms: list[str] | None = None,
) -> ClassificationBundle:
    algorithms = algorithms or ["Regresión logística", "Árbol", "k vecinos", "Random forest"]
    if target not in data:
        raise AnalysisError("La variable respuesta no aparece en la base.")
    if not features:
        raise AnalysisError("Selecciona al menos una variable predictora.")
    missing_features = [column for column in features if column not in data]
    if missing_features:
        raise AnalysisError("No aparecen estas variables: " + ", ".join(missing_features))

    frame = data[[target] + features].copy()
    frame = frame.dropna(subset=[target])
    if drop_incomplete:
        frame = frame.dropna(subset=features)
    levels = frame[target].astype(str).unique().tolist()
    if len(levels) != 2 or positive_class not in levels:
        raise AnalysisError("La clasificación requiere dos clases y una clase positiva válida.")
    negative_class = next(level for level in levels if level != positive_class)
    y = (frame[target].astype(str) == positive_class).astype(int)
    if y.value_counts().min() < 10:
        raise AnalysisError("Cada clase necesita al menos diez casos.")

    X = frame[features]
    numeric, categorical = _feature_types(X, features)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    definitions: dict[str, tuple[Any, bool]] = {
        "Regresión logística": (LogisticRegression(max_iter=1500, random_state=random_state), True),
        "Árbol": (DecisionTreeClassifier(max_depth=4, min_samples_leaf=40, random_state=random_state), False),
        "k vecinos": (KNeighborsClassifier(n_neighbors=15), True),
        "Random forest": (RandomForestClassifier(n_estimators=150, min_samples_leaf=8, random_state=random_state, n_jobs=1), False),
    }
    models: dict[str, Pipeline] = {}
    rows: list[dict[str, Any]] = []
    curves: dict[str, pd.DataFrame] = {}
    predictions = pd.DataFrame({
        "fila_original": X_test.index,
        "clase_real": np.where(y_test.to_numpy() == 1, positive_class, negative_class),
    }).reset_index(drop=True)

    baseline_probability = np.zeros(len(y_test))
    rows.append(_metric_row("Regla ingenua: siempre No", y_test.to_numpy(), baseline_probability.astype(int), baseline_probability))

    for name in algorithms:
        if name not in definitions:
            raise AnalysisError(f"Algoritmo no reconocido: {name}")
        estimator, scale = definitions[name]
        pipeline = Pipeline([
            ("prepare", _preprocessor(numeric, categorical, scale, missing_as_category)),
            ("model", estimator),
        ])
        pipeline.fit(X_train, y_train)
        probability = pipeline.predict_proba(X_test)[:, 1]
        predicted = (probability >= 0.5).astype(int)
        rows.append(_metric_row(name, y_test.to_numpy(), predicted, probability))
        fpr, tpr, thresholds = roc_curve(y_test, probability)
        curves[name] = pd.DataFrame({"FPR": fpr, "TPR": tpr, "Umbral": thresholds, "Modelo": name})
        predictions[f"probabilidad_{name}"] = probability
        predictions[f"prediccion_{name}"] = np.where(predicted == 1, positive_class, negative_class)
        models[name] = pipeline

    return ClassificationBundle(
        metrics=pd.DataFrame(rows),
        predictions=predictions,
        curves=curves,
        models=models,
        train_rows=len(X_train),
        test_rows=len(X_test),
        positive_rate=float(y.mean()),
        target=target,
        positive_class=positive_class,
        features=features,
    )


def tree_explanation(bundle: ClassificationBundle) -> tuple[pd.DataFrame, str, list[str]]:
    if "Árbol" not in bundle.models:
        raise AnalysisError("El modelo de árbol no fue ajustado.")
    pipeline = bundle.models["Árbol"]
    prepare: ColumnTransformer = pipeline.named_steps["prepare"]
    tree: DecisionTreeClassifier = pipeline.named_steps["model"]
    numeric = list(prepare.transformers_[0][2])
    categorical = list(prepare.transformers_[1][2])
    encoded = prepare.named_transformers_["categorical"].named_steps["encode"]
    transformed_names = list(prepare.get_feature_names_out())

    importances = tree.feature_importances_
    rows: list[dict[str, Any]] = []
    position = 0
    for column in numeric:
        rows.append({"Variable": column, "Importancia": float(importances[position])})
        position += 1
    for column, categories in zip(categorical, encoded.categories_):
        width = len(categories)
        rows.append({"Variable": column, "Importancia": float(importances[position:position + width].sum())})
        position += width
    importance = pd.DataFrame(rows).sort_values("Importancia", ascending=False).reset_index(drop=True)
    rules = export_text(tree, feature_names=transformed_names, max_depth=3)
    return importance, rules, transformed_names
