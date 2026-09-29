"""Construye los archivos pedagógicos para validación, fuga y despliegue."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "public" / "clasificacion" / "base_modelable_referencia.csv"
PUBLIC = ROOT / "data" / "public" / "clasificacion"
PRIVATE = ROOT / "data" / "private"


def build(seed: int = 42, portfolio_size: int = 1_000) -> None:
    data = pd.read_csv(SOURCE)
    development, portfolio = train_test_split(
        data,
        test_size=portfolio_size,
        random_state=seed,
        stratify=data["acepta_deposito"],
    )
    development = development.sort_values("id_cliente").reset_index(drop=True)
    portfolio = portfolio.sort_values("id_cliente").reset_index(drop=True)

    # Fuga temporal plantada: la duración se observa solo después de la llamada.
    rng = np.random.default_rng(seed)
    accepted = development["acepta_deposito"].eq("Sí").to_numpy()
    duration = np.where(
        accepted,
        rng.lognormal(mean=np.log(470), sigma=0.38, size=len(development)),
        rng.lognormal(mean=np.log(105), sigma=0.55, size=len(development)),
    )
    development.insert(
        development.columns.get_loc("acepta_deposito"),
        "duracion_llamada",
        np.clip(np.rint(duration), 5, 1_800).astype(int),
    )

    public_portfolio = portfolio.drop(columns="acepta_deposito")
    development.to_csv(PUBLIC / "historial_validacion_con_fuga.csv", index=False, encoding="utf-8-sig")
    public_portfolio.to_csv(PUBLIC / "cartera_clientes.csv", index=False, encoding="utf-8-sig")

    PRIVATE.mkdir(parents=True, exist_ok=True)
    portfolio[["id_cliente", "acepta_deposito"]].to_csv(
        PRIVATE / "clave_cartera_clientes.csv", index=False, encoding="utf-8-sig"
    )
    print({
        "historico": len(development),
        "cartera": len(public_portfolio),
        "aceptacion_historico": round(float(development["acepta_deposito"].eq("Sí").mean()), 4),
    })


if __name__ == "__main__":
    build()
