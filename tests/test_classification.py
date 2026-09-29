import numpy as np
import pandas as pd

from src.classification import (
    choose_economic_threshold,
    contact_list,
    evaluate_classifiers,
    evaluate_validation,
    fit_mini_forest,
    merge_client_campaign,
    threshold_analysis,
    tree_explanation,
)


def small_classification_frame(rows: int = 240) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    age = rng.integers(18, 70, rows)
    channel = rng.choice(["Teléfono", "Celular"], rows)
    probability = 1 / (1 + np.exp(-(-5 + 0.06 * age + 1.2 * (channel == "Celular"))))
    outcome = np.where(rng.random(rows) < probability, "Sí", "No")
    frame = pd.DataFrame({"edad": age, "canal": channel, "acepta": outcome})
    frame.loc[[2, 7, 20], "canal"] = None
    return frame


def test_merge_reports_unmatched_rows():
    clients = pd.DataFrame({"id_cliente": [1, 2, 3], "edad": [30, 40, 50]})
    campaigns = pd.DataFrame({"id_cliente": [2, 3, 4], "acepta": ["No", "Sí", "No"]})
    result = merge_client_campaign(clients, campaigns, "id_cliente", "inner")
    assert len(result.data) == 2
    assert result.matched == 2
    assert result.client_only == 1
    assert result.campaign_only == 1


def test_four_models_share_evaluation_and_metrics_are_bounded():
    frame = small_classification_frame()
    bundle = evaluate_classifiers(frame, "acepta", "Sí", ["edad", "canal"])
    assert bundle.train_rows + bundle.test_rows == len(frame)
    assert set(bundle.metrics["Modelo"]) == {
        "Regla ingenua: siempre No", "Regresión logística", "Árbol", "k vecinos", "Random forest"
    }
    for column in ["Exactitud", "Precisión", "Recall", "F1", "Especificidad", "AUC"]:
        assert bundle.metrics[column].between(0, 1).all()
    assert len(bundle.predictions) == bundle.test_rows


def test_tree_importance_is_aggregated_to_original_features():
    frame = small_classification_frame()
    bundle = evaluate_classifiers(frame, "acepta", "Sí", ["edad", "canal"], algorithms=["Árbol"])
    importance, rules, transformed = tree_explanation(bundle)
    assert set(importance["Variable"]) == {"edad", "canal"}
    assert np.isclose(importance["Importancia"].sum(), 1.0)
    assert "|---" in rules
    assert transformed


def test_public_bank_data_excludes_post_contact_duration():
    clients = pd.read_csv("data/public/clasificacion/clientes.csv")
    campaigns = pd.read_csv("data/public/clasificacion/campanas.csv")
    reference = pd.read_csv("data/public/clasificacion/base_modelable_referencia.csv")
    assert "duration" not in clients.columns
    assert "duration" not in campaigns.columns
    assert "duration" not in reference.columns
    assert len(reference) == 7940
    assert reference["acepta_deposito"].eq("Sí").mean() < 0.15


def test_validation_splits_are_disjoint_and_cover_all_rows():
    frame = small_classification_frame(360)
    result = evaluate_validation(frame, "acepta", "Sí", ["edad", "canal"], model_name="Árbol")
    sets = [set(values) for values in result.split_indices.values()]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert set.union(*sets) == set(frame.index)
    assert set(result.metrics["Partición"]) == {"Entrenamiento", "Validación", "Prueba"}
    assert len(result.cross_validation) == 5


def test_threshold_value_and_tie_break_use_highest_cut():
    actual = np.array([1, 1, 0, 0])
    probability = np.array([0.9, 0.6, 0.4, 0.1])
    table = threshold_analysis(actual, probability, contribution=100, contact_cost=20, thresholds=np.array([0.4, 0.5]))
    chosen = choose_economic_threshold(table)
    assert chosen["Corte"] == 0.5
    assert chosen["Valor"] == 160


def test_contact_list_is_ranked_and_contains_no_outcome():
    result = contact_list(pd.Series(["C1", "C2", "C3"]), np.array([0.1, 0.8, 0.4]), 0.3, 100, 20)
    assert result["id_cliente"].tolist() == ["C2", "C3", "C1"]
    assert result["contactar"].tolist() == ["Sí", "Sí", "No"]
    assert "clase_real" not in result


def test_mini_forest_exports_seven_shallow_trees_and_importance():
    frame = small_classification_frame(420)
    frame["celular"] = frame["canal"].eq("Celular").astype(int)
    result = fit_mini_forest(frame, "acepta", "Sí", ["edad", "celular"])
    assert result.nodes["Arbol"].nunique() == 7
    assert result.nodes.groupby("Arbol")["Nodo"].max().max() <= 6
    assert np.isclose(result.importance["Importancia"].sum(), 1.0)
    assert len([column for column in result.predictions if column.startswith("arbol_")]) == 7


def test_public_validation_files_separate_future_information():
    history = pd.read_csv("data/public/clasificacion/historial_validacion_con_fuga.csv")
    portfolio = pd.read_csv("data/public/clasificacion/cartera_clientes.csv")
    assert "duracion_llamada" in history
    assert "duracion_llamada" not in portfolio
    assert "acepta_deposito" not in portfolio
    assert history["id_cliente"].is_unique and portfolio["id_cliente"].is_unique
    assert set(history["id_cliente"]).isdisjoint(portfolio["id_cliente"])
