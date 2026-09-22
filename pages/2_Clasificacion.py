from __future__ import annotations

import html
from io import BytesIO
from pathlib import Path

import altair as alt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.tree import plot_tree

from src.analysis import AnalysisError
from src.classification import evaluate_classifiers, merge_client_campaign, tree_explanation


ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "data" / "public" / "clasificacion"
LOGO_PATH = ROOT / "assets" / "brand" / "logo-externado.png"

st.set_page_config(page_title="Clasificación · Modelos Supervisados", page_icon=str(LOGO_PATH), layout="wide")
if LOGO_PATH.exists():
    st.logo(str(LOGO_PATH), size="large")

st.markdown(
    """
    <style>
    :root { --amber:#FBBF24; --teal:#2DD4BF; --paper:#FFF7E8; }
    [data-testid="stAppViewContainer"] { background:radial-gradient(circle at 92% 5%,rgba(45,212,191,.10),transparent 24%),#0B1220; }
    [data-testid="stSidebar"] { background:#111C31; border-right:1px solid rgba(251,191,36,.25); }
    [data-testid="stLogo"] { background:#FFF7E8; border-radius:10px; padding:6px 10px; }
    .block-container { max-width:1180px; padding-top:2.2rem; }
    h1 { color:#FFF7E8; } h2 { color:var(--amber); } h3 { color:var(--teal); }
    .hero { border-left:5px solid var(--amber); padding:.25rem 0 .25rem 1.1rem; margin-bottom:1.4rem; }
    .hero p { color:#CBD5E1; max-width:75ch; }
    .decision { background:#FFF7E8; color:#172029; border-left:5px solid #0F766E; border-radius:12px; padding:1rem 1.1rem; }
    .decision strong { color:#0F766E; }
    .privacy { background:rgba(251,113,133,.10); border:1px solid rgba(251,113,133,.45); border-radius:12px; padding:.8rem 1rem; }
    [data-testid="stMetric"] { background:#111C31; border:1px solid rgba(148,163,184,.22); padding:.8rem; border-radius:12px; }
    [data-testid="stDataFrame"] { border:1px solid rgba(251,191,36,.25); border-radius:12px; overflow:hidden; }
    code { color:#A3E635 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_bank_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(BANK_DIR / "clientes.csv"), pd.read_csv(BANK_DIR / "campanas.csv")


@st.cache_data(show_spinner=False)
def load_prepared_bank() -> pd.DataFrame:
    return pd.read_csv(BANK_DIR / "base_modelable_referencia.csv")


def read_uploaded(uploaded, key: str) -> tuple[pd.DataFrame | None, str]:
    if uploaded is None:
        return None, ""
    raw = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix.lower()
    try:
        if suffix == ".xlsx":
            book = pd.ExcelFile(BytesIO(raw))
            sheet = st.selectbox("Hoja del libro", book.sheet_names, key=key)
            return pd.read_excel(BytesIO(raw), sheet_name=sheet), f"{uploaded.name} · {sheet}"
        if suffix == ".csv":
            try:
                return pd.read_csv(BytesIO(raw), sep=None, engine="python"), uploaded.name
            except UnicodeDecodeError:
                return pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding="latin-1"), uploaded.name
    except Exception as exc:
        st.error(f"No pude leer el archivo: {exc}")
        return None, ""
    st.error("Formato no compatible. Usa CSV o XLSX.")
    return None, ""


def report_html(title: str, source: str, expectation: str, interpretation: str, evidence: str) -> bytes:
    safe = lambda text: html.escape(str(text)).replace("\n", "<br>")
    document = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{safe(title)}</title>
    <style>body{{font-family:Arial;color:#172029;background:#f4efe6;padding:36px}}main{{max-width:850px;margin:auto;background:#fffaf2;padding:36px;border:1px solid #d8c7a4;border-radius:16px}}h1{{color:#0f766e}}h2{{color:#b45309;border-bottom:2px solid #c8962d}}.box{{background:#eef8f6;border-left:4px solid #0f766e;padding:14px}}</style>
    </head><body><main><h1>{safe(title)}</h1><p>Fuente: {safe(source)}</p><h2>Expectativa previa</h2><p>{safe(expectation)}</p>
    <h2>Evidencia</h2><div class="box">{evidence}</div><h2>Mi decisión</h2><p>{safe(interpretation)}</p>
    <h2>Límite</h2><p>La predicción organiza casos; no demuestra causalidad ni sustituye el juicio del negocio.</p></main></body></html>"""
    return document.encode("utf-8")


def code_panel() -> None:
    snippet = """from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression

preparar = ColumnTransformer([
    ("num", Pipeline([("imputar", SimpleImputer(strategy="median")),
                      ("escalar", StandardScaler())]), numericas),
    ("cat", Pipeline([("imputar", SimpleImputer(strategy="most_frequent")),
                      ("codificar", OneHotEncoder(handle_unknown="ignore"))]), categoricas),
])
modelo = Pipeline([("preparar", preparar), ("clasificar", LogisticRegression())])
modelo.fit(X_entrenamiento, y_entrenamiento)"""
    with st.expander("¿Cómo se calculó? Ver Python reproducible"):
        st.code(snippet, language="python")
        st.caption("El código es una ampliación voluntaria; la actividad se evalúa por la interpretación.")


st.markdown(
    """<div class="hero"><p><strong>Sesiones 5 y 6</strong></p><h1>Preparar y comparar clasificadores</h1>
    <p>Cada transformación responde a una decisión. Cada métrica representa un tipo de error.</p></div>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    activity = st.radio("Actividad", ["Sesión 5 · Preparar y primer modelo", "Sesión 6 · Algoritmos y métricas"])
    st.markdown('<div class="privacy"><strong>Privacidad</strong><br>No cargues nombres, documentos ni información confidencial.</div>', unsafe_allow_html=True)


if activity.startswith("Sesión 5"):
    st.header("Preparar datos es decidir qué podrá aprender el modelo")
    source_choice = st.radio("Fuente", ["Caso bancario incluido", "Cargar dos tablas"], horizontal=True)
    if source_choice == "Caso bancario incluido":
        clients, campaigns = load_bank_tables()
        source_name = "UCI Bank Marketing · versión pedagógica"
    else:
        c1, c2 = st.columns(2)
        with c1:
            clients_file = st.file_uploader("Tabla de clientes", type=["csv", "xlsx"], key="clients_file")
            clients, clients_name = read_uploaded(clients_file, "clients_sheet")
        with c2:
            campaigns_file = st.file_uploader("Tabla de campañas", type=["csv", "xlsx"], key="campaigns_file")
            campaigns, campaigns_name = read_uploaded(campaigns_file, "campaigns_sheet")
        source_name = f"{clients_name} + {campaigns_name}".strip(" +")
        if clients is None or campaigns is None:
            st.info("Carga ambas tablas para comenzar.")
            st.stop()

    shared_keys = [column for column in campaigns.columns if column in clients.columns]
    if not shared_keys:
        st.error("Las tablas no comparten ninguna columna que pueda usarse como llave.")
        st.stop()
    default_key = shared_keys.index("id_cliente") if "id_cliente" in shared_keys else 0
    left, right = st.columns(2)
    key = left.selectbox("Llave para cruzar", shared_keys, index=default_key)
    join_label = right.radio("Población que conservarás", ["Solo registros con pareja", "Todas las campañas"])
    join_how = "inner" if join_label.startswith("Solo") else "left"
    try:
        merge = merge_client_campaign(clients, campaigns, key, join_how)
    except AnalysisError as exc:
        st.error(str(exc))
        st.stop()

    a, b, c, d = st.columns(4)
    a.metric("Perfiles", f"{len(clients):,}")
    b.metric("Campañas", f"{len(campaigns):,}")
    c.metric("Coincidencias", f"{merge.matched:,}")
    d.metric("Resultado", f"{len(merge.data):,}")
    if merge.client_only or merge.campaign_only:
        st.warning(f"Sin pareja: {merge.client_only} perfiles y {merge.campaign_only} campañas. El tipo de cruce decide qué población sobrevive.")

    target_options = [column for column in merge.data if 2 <= merge.data[column].nunique(dropna=True) <= 10]
    default_target = target_options.index("acepta_deposito") if "acepta_deposito" in target_options else 0
    target = st.selectbox("Variable respuesta", target_options, index=default_target)
    feature_options = [column for column in merge.data if column not in [key, target]]
    features = st.multiselect("Variables disponibles antes de decidir", feature_options, default=feature_options)
    missing_policy = st.radio(
        "Tratamiento de blancos",
        ["Conservar como 'Sin dato' e imputar numéricas", "Imputar con mediana/moda dentro del modelo", "Eliminar filas incompletas"],
    )
    missing_as_category = missing_policy.startswith("Conservar")
    drop_incomplete = missing_policy.startswith("Eliminar")

    audit = pd.DataFrame({
        "Variable": merge.data.columns,
        "Tipo": merge.data.dtypes.astype(str).values,
        "Blancos": merge.data.isna().sum().values,
        "Valores distintos": [merge.data[column].nunique(dropna=True) for column in merge.data],
    }).sort_values("Blancos", ascending=False)
    with st.expander("Auditar faltantes y codificación", expanded=True):
        st.dataframe(audit, width="stretch", hide_index=True)
        st.caption("'Desconocido' es un valor observado; un blanco es ausencia. No se tratan automáticamente como lo mismo.")
        categorical = [column for column in features if not pd.api.types.is_numeric_dtype(merge.data[column])]
        encoding = pd.DataFrame({
            "Variable de texto": categorical,
            "Categorías observadas": [merge.data[column].nunique(dropna=True) for column in categorical],
            "Codificación": ["Indicadores 0/1 creados dentro del modelo" for _ in categorical],
        })
        st.dataframe(encoding, width="stretch", hide_index=True)

    expectation = st.text_area("Antes de ajustar: ¿qué perfil esperas que tenga mayor probabilidad de aceptar y por qué?")
    config = (target, tuple(features), missing_policy, join_how, len(merge.data))
    if st.button("Preparar y ajustar el primer clasificador", type="primary"):
        try:
            levels = merge.data[target].dropna().astype(str).unique().tolist()
            positive = "Sí" if "Sí" in levels else levels[-1]
            with st.spinner("Preparando variables y ajustando la regresión logística..."):
                bundle = evaluate_classifiers(
                    merge.data, target, positive, features, missing_as_category, drop_incomplete,
                    algorithms=["Regresión logística"],
                )
            st.session_state.first_classifier = bundle
            st.session_state.first_classifier_config = config
        except AnalysisError as exc:
            st.error(str(exc))

    bundle = st.session_state.get("first_classifier") if st.session_state.get("first_classifier_config") == config else None
    if bundle:
        logistic = bundle.metrics.loc[bundle.metrics["Modelo"] == "Regresión logística"].iloc[0]
        baseline = bundle.metrics.iloc[0]
        st.subheader("Primer resultado: suficiente para abrir preguntas")
        x, y, z = st.columns(3)
        x.metric("Entrenamiento", f"{bundle.train_rows:,}")
        y.metric("Evaluación", f"{bundle.test_rows:,}")
        z.metric("Exactitud", f"{logistic['Exactitud']:.1%}")
        st.info(f"Una regla que siempre predice la clase mayoritaria logra {baseline['Exactitud']:.1%}. En la próxima sesión auditaremos los errores que esconde la exactitud.")
        code_panel()
        interpretation = st.text_area("Registra una decisión defendible, una discutible y una pregunta abierta")
        st.download_button("Descargar base preparada", merge.data.to_csv(index=False).encode("utf-8-sig"), "base_preparada.csv", "text/csv")
        if interpretation.strip():
            evidence = f"Cruce: {join_label}; filas: {len(merge.data):,}; predictores: {len(features)}; exactitud inicial: {logistic['Exactitud']:.1%}."
            st.download_button("Descargar bitácora", report_html("Preparación y primer clasificador", source_name, expectation, interpretation, evidence), "bitacora_preparacion.html", "text/html")


else:
    st.header("La mejor métrica depende del error que más cuesta")
    source_choice = st.radio("Fuente", ["Base bancaria preparada", "Cargar base preparada"], horizontal=True)
    if source_choice == "Base bancaria preparada":
        data = load_prepared_bank()
        source_name = "Base bancaria modelable de referencia"
    else:
        uploaded = st.file_uploader("CSV o XLSX · máximo 25 MB", type=["csv", "xlsx"])
        data, source_name = read_uploaded(uploaded, "prepared_sheet")
        if data is None:
            st.info("Carga una base preparada para comenzar.")
            st.stop()

    with st.expander("Revisar la base", expanded=False):
        a, b, c = st.columns(3)
        a.metric("Filas", f"{len(data):,}")
        b.metric("Columnas", len(data.columns))
        c.metric("Blancos", f"{int(data.isna().sum().sum()):,}")
        st.dataframe(data.head(20), width="stretch", hide_index=True)

    target_options = [column for column in data if data[column].nunique(dropna=True) == 2]
    if not target_options:
        st.error("La base necesita una variable respuesta con dos clases.")
        st.stop()
    default_target = target_options.index("acepta_deposito") if "acepta_deposito" in target_options else 0
    target = st.selectbox("Variable respuesta", target_options, index=default_target)
    levels = sorted(data[target].dropna().astype(str).unique().tolist())
    positive = st.selectbox("Clase positiva", levels, index=levels.index("Sí") if "Sí" in levels else 1)
    identifiers = [column for column in data if column.lower() == "id" or column.lower().startswith("id_")]
    feature_options = [column for column in data if column not in identifiers + [target]]
    features = st.multiselect("Predictores", feature_options, default=feature_options)
    missing_as_category = st.checkbox("Conservar blancos categóricos como 'Sin dato'", value=True)
    config = (target, positive, tuple(features), missing_as_category, len(data))

    if st.button("Comparar los cuatro algoritmos", type="primary"):
        try:
            with st.spinner("Ajustando cuatro modelos con la misma partición..."):
                bundle = evaluate_classifiers(data, target, positive, features, missing_as_category)
            st.session_state.classifier_comparison = bundle
            st.session_state.classifier_comparison_config = config
            st.session_state.errors_revealed = False
        except AnalysisError as exc:
            st.error(str(exc))

    bundle = st.session_state.get("classifier_comparison") if st.session_state.get("classifier_comparison_config") == config else None
    if bundle:
        st.caption(f"Entrenamiento: {bundle.train_rows:,} · Evaluación: {bundle.test_rows:,} · Clase positiva: {bundle.positive_rate:.1%}")
        st.subheader("Primera mirada")
        st.dataframe(bundle.metrics[["Modelo", "Exactitud"]].style.format({"Exactitud": "{:.1%}"}), width="stretch", hide_index=True)
        preliminary = st.selectbox("Si solo vieras exactitud, ¿qué modelo elegirías?", bundle.metrics["Modelo"].tolist())
        preliminary_reason = st.text_area("Justifica tu elección provisional")
        if st.button("Auditar los errores", disabled=not preliminary_reason.strip()):
            st.session_state.errors_revealed = True

        if st.session_state.get("errors_revealed"):
            st.subheader("La matriz cambia la historia")
            st.dataframe(
                bundle.metrics.style.format({
                    "Exactitud": "{:.1%}", "Precisión": "{:.1%}", "Recall": "{:.1%}",
                    "F1": "{:.1%}", "Especificidad": "{:.1%}", "AUC": "{:.3f}",
                }), width="stretch", hide_index=True,
            )
            model_names = [name for name in bundle.metrics["Modelo"] if not name.startswith("Regla")]
            selected_model = st.selectbox("Modelo para auditar", model_names)
            row = bundle.metrics.loc[bundle.metrics["Modelo"] == selected_model].iloc[0]
            matrix = pd.DataFrame(
                [[int(row["TN"]), int(row["FP"])], [int(row["FN"]), int(row["TP"])]],
                index=["Real: No", f"Real: {positive}"], columns=["Predice: No", f"Predice: {positive}"],
            )
            st.dataframe(matrix, width="stretch")
            st.markdown(
                f'<div class="decision"><strong>Lectura de negocio</strong><br>El modelo dejó escapar <strong>{int(row["FN"])}</strong> aceptantes y generó <strong>{int(row["FP"])}</strong> contactos que no aceptarían.</div>',
                unsafe_allow_html=True,
            )

            st.subheader("ROC y AUC: capacidad de ordenar, no una decisión final")
            roc_data = pd.concat(bundle.curves.values(), ignore_index=True)
            diagonal = pd.DataFrame({"FPR": [0, 1], "TPR": [0, 1]})
            roc = alt.Chart(roc_data).mark_line(strokeWidth=3).encode(
                x=alt.X("FPR:Q", title="Tasa de falsos positivos"), y=alt.Y("TPR:Q", title="Recall"),
                color="Modelo:N", tooltip=["Modelo", alt.Tooltip("FPR:Q", format=".3f"), alt.Tooltip("TPR:Q", format=".3f")],
            )
            chance = alt.Chart(diagonal).mark_line(strokeDash=[5, 5], color="#94A3B8").encode(x="FPR:Q", y="TPR:Q")
            st.altair_chart((roc + chance).properties(height=380), width="stretch")

            st.subheader("Árbol: reglas visibles e importancia con límites")
            importance, rules, tree_names = tree_explanation(bundle)
            tree_model = bundle.models["Árbol"].named_steps["model"]
            fig, ax = plt.subplots(figsize=(15, 7))
            plot_tree(tree_model, feature_names=tree_names, class_names=["No", positive], filled=True, max_depth=3, fontsize=7, ax=ax)
            st.pyplot(fig, clear_figure=True)
            chart = alt.Chart(importance.head(12)).mark_bar(color="#2DD4BF").encode(
                x=alt.X("Importancia:Q", title="Reducción de impureza acumulada"),
                y=alt.Y("Variable:N", sort="-x", title=None), tooltip=["Variable", alt.Tooltip("Importancia:Q", format=".3f")],
            ).properties(height=320)
            st.altair_chart(chart, width="stretch")
            st.warning("Importancia no indica dirección, efecto causal ni conveniencia de intervenir. Puede favorecer variables con muchos cortes posibles.")
            with st.expander("Ver reglas del árbol en texto"):
                st.code(rules, language="text")

            st.subheader("Elegir con un costo explícito")
            scenario = st.radio("Escenario", ["Crecimiento: es más costoso omitir a quien aceptaría", "Capacidad limitada: es más costoso contactar a quien no aceptará"])
            priority = "recall" if scenario.startswith("Crecimiento") else "precisión"
            st.info(f"La métrica prioritaria es **{priority}**. F1 puede ser un compromiso, pero no reemplaza declarar el costo.")
            final_model = st.selectbox("Algoritmo elegido", model_names, key="final_model")
            final_reason = st.text_area("Justifica con una métrica, el error tolerado y una limitación")
            code_panel()
            st.download_button("Descargar predicciones para Excel", bundle.predictions.to_csv(index=False).encode("utf-8-sig"), "predicciones_clasificacion.csv", "text/csv")
            if final_reason.strip():
                chosen = bundle.metrics.loc[bundle.metrics["Modelo"] == final_model].iloc[0]
                evidence = (
                    f"Modelo: {final_model}; exactitud: {chosen['Exactitud']:.1%}; precisión: {chosen['Precisión']:.1%}; "
                    f"recall: {chosen['Recall']:.1%}; F1: {chosen['F1']:.1%}; especificidad: {chosen['Especificidad']:.1%}; AUC: {chosen['AUC']:.3f}."
                )
                st.download_button("Descargar evidencia", report_html("Comparación de clasificadores", source_name, scenario, final_reason, evidence), "evidencia_clasificacion.html", "text/html")

st.divider()
st.caption("Universidad Externado de Colombia · Preparar datos y elegir métricas son decisiones de negocio.")
