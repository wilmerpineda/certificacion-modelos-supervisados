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
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
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


@dataclass
class ValidationBundle:
    metrics: pd.DataFrame
    cross_validation: pd.DataFrame
    predictions: pd.DataFrame
    importance: pd.DataFrame
    model: Pipeline
    split_indices: dict[str, list[Any]]
    target: str
    positive_class: str
    features: list[str]


@dataclass
class MiniForestBundle:
    model: Pipeline
    nodes: pd.DataFrame
    importance: pd.DataFrame
    predictions: pd.DataFrame
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


def _estimator_definition(name: str, random_state: int = 42) -> tuple[Any, bool]:
    definitions: dict[str, tuple[Any, bool]] = {
        "Regresión logística": (LogisticRegression(max_iter=1500, random_state=random_state), True),
        "Árbol": (DecisionTreeClassifier(max_depth=4, min_samples_leaf=40, random_state=random_state), False),
        "k vecinos": (KNeighborsClassifier(n_neighbors=15), True),
        "Random forest": (
            RandomForestClassifier(
                n_estimators=150, min_samples_leaf=8, random_state=random_state, n_jobs=1
            ),
            False,
        ),
    }
    if name not in definitions:
        raise AnalysisError(f"Algoritmo no reconocido: {name}")
    return definitions[name]


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
        estimator, scale = _estimator_definition(name, random_state)
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


def _split_development_data(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.40, random_state=random_state, stratify=y
    )
    X_validation, X_test, y_validation, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=random_state, stratify=y_temp
    )
    return X_train, X_validation, X_test, y_train, y_validation, y_test


def _aggregate_importance(pipeline: Pipeline, features: list[str]) -> pd.DataFrame:
    prepare: ColumnTransformer = pipeline.named_steps["prepare"]
    estimator = pipeline.named_steps["model"]
    transformed_names = list(prepare.get_feature_names_out())
    raw = np.asarray(estimator.feature_importances_, dtype=float)
    totals = {feature: 0.0 for feature in features}
    for transformed, value in zip(transformed_names, raw):
        cleaned = transformed.split("__", 1)[-1]
        original = next(
            (feature for feature in features if cleaned == feature or cleaned.startswith(f"{feature}_")),
            cleaned,
        )
        totals[original] = totals.get(original, 0.0) + float(value)
    result = pd.DataFrame(
        {"Variable": list(totals), "Importancia": list(totals.values())}
    ).sort_values("Importancia", ascending=False, ignore_index=True)
    total = float(result["Importancia"].sum())
    if total:
        result["Importancia"] = result["Importancia"] / total
    return result


def evaluate_validation(
    data: pd.DataFrame,
    target: str,
    positive_class: str,
    features: list[str],
    model_name: str = "Random forest",
    missing_as_category: bool = True,
    random_state: int = 42,
    cv_folds: int = 5,
) -> ValidationBundle:
    if target not in data or not features:
        raise AnalysisError("Selecciona una respuesta y al menos un predictor.")
    frame = data[[target] + features].dropna(subset=[target]).copy()
    levels = frame[target].astype(str).unique().tolist()
    if len(levels) != 2 or positive_class not in levels:
        raise AnalysisError("La validación requiere dos clases y una clase positiva válida.")
    y = (frame[target].astype(str) == positive_class).astype(int)
    if y.value_counts().min() < max(20, cv_folds):
        raise AnalysisError("Cada clase necesita suficientes casos para partición y validación cruzada.")
    X = frame[features]
    numeric, categorical = _feature_types(X, features)
    estimator, scale = _estimator_definition(model_name, random_state)
    pipeline = Pipeline([
        ("prepare", _preprocessor(numeric, categorical, scale, missing_as_category)),
        ("model", estimator),
    ])
    X_train, X_validation, X_test, y_train, y_validation, y_test = _split_development_data(
        X, y, random_state
    )
    pipeline.fit(X_train, y_train)

    rows: list[dict[str, Any]] = []
    predictions = pd.DataFrame(index=frame.index)
    predictions["particion"] = ""
    predictions["clase_real"] = np.where(y.to_numpy() == 1, positive_class, "No")
    for partition, X_part, y_part in [
        ("Entrenamiento", X_train, y_train),
        ("Validación", X_validation, y_validation),
        ("Prueba", X_test, y_test),
    ]:
        probability = pipeline.predict_proba(X_part)[:, 1]
        predicted = (probability >= 0.5).astype(int)
        row = _metric_row(partition, y_part.to_numpy(), predicted, probability)
        row["Partición"] = partition
        row["Filas"] = len(y_part)
        rows.append(row)
        predictions.loc[X_part.index, "particion"] = partition
        predictions.loc[X_part.index, "probabilidad"] = probability
        predictions.loc[X_part.index, "prediccion"] = np.where(predicted == 1, positive_class, "No")

    metrics = pd.DataFrame(rows).drop(columns="Modelo")
    train_accuracy = float(metrics.loc[metrics["Partición"] == "Entrenamiento", "Exactitud"].iloc[0])
    metrics["Brecha exactitud"] = train_accuracy - metrics["Exactitud"]

    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cv_result = cross_validate(
        pipeline,
        X_train,
        y_train,
        cv=cv,
        scoring={"Exactitud": "accuracy", "Recall": "recall", "AUC": "roc_auc"},
        return_train_score=False,
    )
    cross_validation = pd.DataFrame({
        "Pliegue": np.arange(1, cv_folds + 1),
        "Exactitud": cv_result["test_Exactitud"],
        "Recall": cv_result["test_Recall"],
        "AUC": cv_result["test_AUC"],
    })
    importance = (
        _aggregate_importance(pipeline, features)
        if hasattr(pipeline.named_steps["model"], "feature_importances_")
        else pd.DataFrame(columns=["Variable", "Importancia"])
    )
    return ValidationBundle(
        metrics=metrics,
        cross_validation=cross_validation,
        predictions=predictions.reset_index(names="fila_original"),
        importance=importance,
        model=pipeline,
        split_indices={
            "Entrenamiento": X_train.index.tolist(),
            "Validación": X_validation.index.tolist(),
            "Prueba": X_test.index.tolist(),
        },
        target=target,
        positive_class=positive_class,
        features=features,
    )


def threshold_analysis(
    actual: np.ndarray | pd.Series,
    probabilities: np.ndarray | pd.Series,
    contribution: float = 100_000,
    contact_cost: float = 20_000,
    thresholds: np.ndarray | None = None,
) -> pd.DataFrame:
    y = np.asarray(actual, dtype=int)
    probability = np.asarray(probabilities, dtype=float)
    if len(y) != len(probability) or not len(y):
        raise AnalysisError("Respuesta y probabilidades deben tener igual longitud y no estar vacías.")
    grid = thresholds if thresholds is not None else np.round(np.arange(0.05, 0.81, 0.01), 2)
    rows = []
    for threshold in grid:
        predicted = (probability >= float(threshold)).astype(int)
        row = _metric_row("corte", y, predicted, probability)
        contacts = int(predicted.sum())
        row.update({
            "Corte": float(threshold),
            "Contactos": contacts,
            "Valor": float(contribution * row["TP"] - contact_cost * contacts),
        })
        rows.append(row)
    return pd.DataFrame(rows).drop(columns="Modelo")


def choose_economic_threshold(table: pd.DataFrame) -> pd.Series:
    required = {"Corte", "Valor"}
    if not required.issubset(table.columns) or table.empty:
        raise AnalysisError("La tabla de cortes no contiene Corte y Valor.")
    return table.sort_values(["Valor", "Corte"], ascending=[False, False]).iloc[0]


def contact_list(
    identifiers: pd.Series,
    probabilities: np.ndarray | pd.Series,
    threshold: float,
    contribution: float = 100_000,
    contact_cost: float = 20_000,
) -> pd.DataFrame:
    probability = np.asarray(probabilities, dtype=float)
    if len(identifiers) != len(probability):
        raise AnalysisError("Los identificadores y las probabilidades no tienen igual longitud.")
    result = pd.DataFrame({
        "id_cliente": identifiers.astype(str).to_numpy(),
        "probabilidad": probability,
    })
    result["valor_esperado"] = result["probabilidad"] * contribution - contact_cost
    result["punto_corte"] = float(threshold)
    result["contactar"] = np.where(result["probabilidad"] >= threshold, "Sí", "No")
    result = result.sort_values("probabilidad", ascending=False, ignore_index=True)
    result["prioridad"] = np.arange(1, len(result) + 1)
    return result[["id_cliente", "probabilidad", "valor_esperado", "punto_corte", "contactar", "prioridad"]]


def fit_mini_forest(
    data: pd.DataFrame,
    target: str,
    positive_class: str,
    features: list[str],
    random_state: int = 42,
    train_mask: pd.Series | np.ndarray | None = None,
) -> MiniForestBundle:
    frame = data[[target] + features].dropna().copy()
    if not features or not all(pd.api.types.is_numeric_dtype(frame[column]) for column in features):
        raise AnalysisError("El mini bosque requiere predictores numéricos o indicadores 0/1 sin blancos.")
    y = (frame[target].astype(str) == positive_class).astype(int)
    X = frame[features]
    forest = RandomForestClassifier(
        n_estimators=7,
        max_depth=2,
        max_features=min(2, len(features)),
        min_samples_leaf=40,
        bootstrap=True,
        random_state=random_state,
        n_jobs=1,
    )
    pipeline = Pipeline([
        ("prepare", _preprocessor(features, [], False, True)),
        ("model", forest),
    ])
    if train_mask is None:
        training_mask = np.ones(len(frame), dtype=bool)
    else:
        aligned = pd.Series(train_mask, index=data.index).reindex(frame.index)
        if aligned.isna().any():
            raise AnalysisError("La máscara de entrenamiento no coincide con las filas del mini bosque.")
        training_mask = aligned.astype(bool).to_numpy()
    if training_mask.sum() < 100 or np.unique(y.to_numpy()[training_mask]).size != 2:
        raise AnalysisError("El entrenamiento del mini bosque necesita al menos 100 filas y ambas clases.")
    pipeline.fit(X.loc[training_mask], y.loc[training_mask])
    transformed = [name.split("__", 1)[-1] for name in pipeline.named_steps["prepare"].get_feature_names_out()]
    model: RandomForestClassifier = pipeline.named_steps["model"]
    node_rows: list[dict[str, Any]] = []
    for tree_number, estimator in enumerate(model.estimators_, start=1):
        tree = estimator.tree_
        root_weight = float(tree.weighted_n_node_samples[0])
        for node in range(tree.node_count):
            left = int(tree.children_left[node])
            right = int(tree.children_right[node])
            is_leaf = left == right
            weighted = float(tree.weighted_n_node_samples[node])
            value = np.asarray(tree.value[node][0], dtype=float)
            proportions = value / value.sum() if value.sum() else np.array([0.0, 0.0])
            reduction = 0.0
            if not is_leaf:
                reduction = (
                    weighted * float(tree.impurity[node])
                    - float(tree.weighted_n_node_samples[left]) * float(tree.impurity[left])
                    - float(tree.weighted_n_node_samples[right]) * float(tree.impurity[right])
                ) / root_weight
            feature_name = "Hoja" if is_leaf else transformed[int(tree.feature[node])]
            node_rows.append({
                "Arbol": tree_number,
                "Nodo": node,
                "Es_hoja": "Sí" if is_leaf else "No",
                "Variable": feature_name,
                "Umbral": np.nan if is_leaf else float(tree.threshold[node]),
                "Hijo_izquierdo": "" if is_leaf else left,
                "Hijo_derecho": "" if is_leaf else right,
                "N_ponderado": weighted,
                "Clase_0": float(proportions[0] * weighted),
                "Clase_1": float(proportions[1] * weighted),
                "Gini": float(tree.impurity[node]),
                "Reduccion_Gini": reduction,
                "Probabilidad_hoja": float(proportions[1]) if is_leaf else np.nan,
            })
    nodes = pd.DataFrame(node_rows)
    importance = pd.DataFrame({
        "Variable": features,
        "Importancia": np.mean([tree.feature_importances_ for tree in model.estimators_], axis=0),
    }).sort_values("Importancia", ascending=False, ignore_index=True)
    total = float(importance["Importancia"].sum())
    if total:
        importance["Importancia"] /= total
    transformed_X = pipeline.named_steps["prepare"].transform(X)
    tree_probability = [tree.predict_proba(transformed_X)[:, 1] for tree in model.estimators_]
    predictions = pd.DataFrame({"fila_original": frame.index, "clase_real": y.to_numpy()})
    for index, probability in enumerate(tree_probability, start=1):
        predictions[f"arbol_{index}"] = probability
    predictions["probabilidad_bosque"] = np.mean(tree_probability, axis=0)
    predictions["prediccion_bosque"] = (predictions["probabilidad_bosque"] >= 0.5).astype(int)
    return MiniForestBundle(pipeline, nodes, importance, predictions, features)
