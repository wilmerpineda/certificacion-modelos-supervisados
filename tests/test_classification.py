import numpy as np
import pandas as pd

from src.classification import evaluate_classifiers, merge_client_campaign, tree_explanation


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
