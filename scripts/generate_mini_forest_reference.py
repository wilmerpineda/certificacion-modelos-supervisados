"""Exporta el bosque pedagógico de siete árboles para auditoría en Excel."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.classification import fit_mini_forest


DATA = ROOT / "data" / "public" / "clasificacion" / "historial_validacion_con_fuga.csv"
OUTPUT = ROOT / "data" / "public" / "clasificacion"


def build() -> None:
    source = pd.read_csv(DATA)
    frame = source[[
        "id_cliente", "acepta_deposito", "edad", "contactos_campana",
        "contactos_previos", "tipo_contacto", "resultado_previo",
    ]].copy()
    frame["contacto_celular"] = frame["tipo_contacto"].eq("cellular").astype(int)
    frame["resultado_previo_exitoso"] = frame["resultado_previo"].eq("success").astype(int)
    number = frame["id_cliente"].str.extract(r"(\d+)$", expand=False).astype(int)
    frame["particion"] = number.mod(4).eq(0).map({True: "Prueba", False: "Entrenamiento"})
    features = [
        "edad", "contactos_campana", "contactos_previos",
        "contacto_celular", "resultado_previo_exitoso",
    ]
    forest = fit_mini_forest(
        frame,
        "acepta_deposito",
        "Sí",
        features,
        train_mask=frame["particion"].eq("Entrenamiento"),
    )
    data_export = frame[["id_cliente", "particion", "acepta_deposito"] + features].copy()
    predictions = forest.predictions.copy()
    predictions.insert(1, "id_cliente", frame.loc[predictions["fila_original"], "id_cliente"].to_numpy())
    predictions.insert(2, "particion", frame.loc[predictions["fila_original"], "particion"].to_numpy())
    data_export.to_csv(OUTPUT / "bosque_datos_referencia.csv", index=False, encoding="utf-8-sig")
    forest.nodes.to_csv(OUTPUT / "bosque_nodos_referencia.csv", index=False, encoding="utf-8-sig")
    forest.importance.to_csv(OUTPUT / "bosque_importancia_referencia.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(OUTPUT / "bosque_predicciones_referencia.csv", index=False, encoding="utf-8-sig")
    print({"arboles": forest.nodes["Arbol"].nunique(), "nodos": len(forest.nodes), "filas": len(data_export)})


if __name__ == "__main__":
    build()
