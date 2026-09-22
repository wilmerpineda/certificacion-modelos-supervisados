from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


RENAME = {
    "age": "edad",
    "job": "ocupacion",
    "marital": "estado_civil",
    "education": "educacion",
    "default": "incumplimiento_credito",
    "housing": "credito_vivienda",
    "loan": "prestamo_personal",
    "contact": "tipo_contacto",
    "month": "mes",
    "day_of_week": "dia_semana",
    "campaign": "contactos_campana",
    "pdays": "dias_desde_contacto_previo",
    "previous": "contactos_previos",
    "poutcome": "resultado_previo",
    "emp.var.rate": "variacion_empleo",
    "cons.price.idx": "indice_precios",
    "cons.conf.idx": "confianza_consumidor",
    "euribor3m": "euribor_3m",
    "nr.employed": "numero_empleados",
    "y": "acepta_deposito",
}

CLIENT_COLUMNS = [
    "id_cliente", "edad", "ocupacion", "estado_civil", "educacion",
    "incumplimiento_credito", "credito_vivienda", "prestamo_personal",
]
CAMPAIGN_COLUMNS = [
    "id_cliente", "tipo_contacto", "mes", "dia_semana", "contactos_campana",
    "dias_desde_contacto_previo", "contactos_previos", "resultado_previo",
    "variacion_empleo", "indice_precios", "confianza_consumidor", "euribor_3m",
    "numero_empleados", "acepta_deposito",
]


def stratified_sample(data: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    rate = float((data["y"] == "yes").mean())
    yes_n = round(size * rate)
    no_n = size - yes_n
    yes = data.loc[data["y"] == "yes"].sample(yes_n, random_state=seed)
    no = data.loc[data["y"] == "no"].sample(no_n, random_state=seed)
    return pd.concat([yes, no]).sample(frac=1, random_state=seed).reset_index(drop=True)


def build(source: Path, output: Path, size: int = 8000, seed: int = 42) -> None:
    raw = pd.read_csv(source, sep=";")
    required = set(RENAME) | {"duration"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"La fuente no contiene: {sorted(missing)}")

    # duration se excluye porque solo existe después de la llamada.
    sample = stratified_sample(raw.drop(columns="duration"), size, seed).rename(columns=RENAME)
    sample.insert(0, "id_cliente", [f"CLI{index:06d}" for index in range(1, size + 1)])
    sample = sample.replace({"unknown": "Desconocido", "yes": "Sí", "no": "No"})

    clients = sample[CLIENT_COLUMNS].copy()
    campaigns = sample[CAMPAIGN_COLUMNS].copy()

    rng = np.random.default_rng(seed)
    available = np.arange(size)
    blank_sets = np.array_split(rng.choice(available, size=480, replace=False), 3)
    for column, indices in zip(["educacion", "credito_vivienda", "prestamo_personal"], blank_sets):
        clients.loc[indices, column] = pd.NA

    # 20 campañas quedan sin perfil y 40 perfiles sin campaña.
    no_profile = set(rng.choice(available, size=20, replace=False))
    remaining = np.array(sorted(set(available) - no_profile))
    no_campaign = set(rng.choice(remaining, size=40, replace=False))
    clients = clients.drop(index=list(no_profile)).reset_index(drop=True)
    campaigns = campaigns.drop(index=list(no_campaign)).reset_index(drop=True)

    reference = campaigns.merge(clients, on="id_cliente", how="inner", validate="one_to_one")
    dictionary_rows = [
        ("id_cliente", "—", "Identificador sintético para el ejercicio; nunca es predictor.", "Identificador"),
        ("edad", "age", "Edad del cliente.", "Predictor numérico"),
        ("ocupacion", "job", "Ocupación declarada.", "Predictor categórico"),
        ("estado_civil", "marital", "Estado civil.", "Predictor categórico"),
        ("educacion", "education", "Nivel educativo; contiene blancos controlados.", "Predictor categórico"),
        ("incumplimiento_credito", "default", "Antecedente de incumplimiento.", "Predictor categórico"),
        ("credito_vivienda", "housing", "Tiene crédito de vivienda; contiene blancos controlados.", "Predictor categórico"),
        ("prestamo_personal", "loan", "Tiene préstamo personal; contiene blancos controlados.", "Predictor categórico"),
        ("tipo_contacto", "contact", "Canal de contacto.", "Predictor categórico"),
        ("mes", "month", "Mes del contacto.", "Predictor categórico"),
        ("dia_semana", "day_of_week", "Día de la semana del contacto.", "Predictor categórico"),
        ("contactos_campana", "campaign", "Contactos realizados durante la campaña.", "Predictor numérico"),
        ("dias_desde_contacto_previo", "pdays", "Días desde el contacto previo; 999 indica que no hubo contacto.", "Predictor numérico"),
        ("contactos_previos", "previous", "Número de contactos previos.", "Predictor numérico"),
        ("resultado_previo", "poutcome", "Resultado de la campaña anterior.", "Predictor categórico"),
        ("variacion_empleo", "emp.var.rate", "Tasa de variación del empleo.", "Predictor numérico"),
        ("indice_precios", "cons.price.idx", "Índice de precios al consumidor.", "Predictor numérico"),
        ("confianza_consumidor", "cons.conf.idx", "Índice de confianza del consumidor.", "Predictor numérico"),
        ("euribor_3m", "euribor3m", "Tasa Euribor a tres meses.", "Predictor numérico"),
        ("numero_empleados", "nr.employed", "Número de empleados del indicador macroeconómico.", "Predictor numérico"),
        ("acepta_deposito", "y", "Aceptó el depósito a plazo.", "Variable respuesta"),
    ]
    dictionary = pd.DataFrame(dictionary_rows, columns=["variable", "nombre_uci", "descripcion", "rol_sugerido"])
    dictionary["fuente"] = "https://archive.ics.uci.edu/dataset/222/bank+marketing"
    dictionary["nota"] = "Versión pedagógica derivada: muestra, ID, blancos y filas sin pareja son modificaciones documentadas."

    output.mkdir(parents=True, exist_ok=True)
    clients.to_csv(output / "clientes.csv", index=False, encoding="utf-8-sig")
    campaigns.to_csv(output / "campanas.csv", index=False, encoding="utf-8-sig")
    reference.to_csv(output / "base_modelable_referencia.csv", index=False, encoding="utf-8-sig")
    dictionary.to_csv(output / "diccionario_clasificacion.csv", index=False, encoding="utf-8-sig")

    print({
        "clientes": len(clients),
        "campanas": len(campaigns),
        "referencia": len(reference),
        "aceptacion": round(float((reference["acepta_deposito"] == "Sí").mean()), 4),
        "faltantes": int(clients.isna().sum().sum()),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--size", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    build(args.source, args.output, args.size, args.seed)
