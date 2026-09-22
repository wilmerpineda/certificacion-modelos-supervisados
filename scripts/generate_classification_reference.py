from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.classification import evaluate_classifiers, tree_explanation


def build(data_path: Path, output: Path) -> None:
    data = pd.read_csv(data_path)
    target = "acepta_deposito"
    features = [column for column in data.columns if column not in {"id_cliente", target}]
    bundle = evaluate_classifiers(data, target, "Sí", features)
    importance, rules, _ = tree_explanation(bundle)
    output.mkdir(parents=True, exist_ok=True)
    bundle.predictions.to_csv(output / "predicciones_referencia.csv", index=False, encoding="utf-8-sig")
    bundle.metrics.to_csv(output / "metricas_referencia.csv", index=False, encoding="utf-8-sig")
    importance.to_csv(output / "importancia_arbol_referencia.csv", index=False, encoding="utf-8-sig")
    (output / "reglas_arbol_referencia.txt").write_text(rules, encoding="utf-8")
    print(bundle.metrics.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.data, args.output)
