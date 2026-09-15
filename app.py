from __future__ import annotations

import html
from io import BytesIO
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.analysis import (
    AnalysisError,
    coefficient_table,
    fit_regression,
    model_summary,
    predict_profile,
    vif_table,
    welch_t_test,
)


ROOT = Path(__file__).parent
SAMPLE_PATH = ROOT / "data" / "public" / "Muestra_ICFES_5000.xlsx"
LOGO_PATH = ROOT / "assets" / "brand" / "logo-externado.png"

st.set_page_config(
    page_title="Laboratorio de Modelos Supervisados",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

if LOGO_PATH.exists():
    st.logo(str(LOGO_PATH), size="large")

st.markdown(
    """
    <style>
    :root { --amber:#FBBF24; --teal:#2DD4BF; --coral:#FB7185; --paper:#FFF7E8; }
    [data-testid="stAppViewContainer"] {
      background: radial-gradient(circle at 92% 5%, rgba(45,212,191,.10), transparent 24%), #0B1220;
    }
    [data-testid="stSidebar"] { background:#111C31; border-right:1px solid rgba(251,191,36,.25); }
    [data-testid="stLogo"] { background:#FFF7E8; border-radius:10px; padding:6px 10px; }
    .block-container { max-width:1180px; padding-top:2.2rem; }
    h1, h2, h3 { letter-spacing:-.02em; }
    h1 { color:#FFF7E8; }
    h2 { color:var(--amber); margin-top:1.6rem; }
    h3 { color:var(--teal); }
    .hero { border-left:5px solid var(--amber); padding:.25rem 0 .25rem 1.1rem; margin-bottom:1.4rem; }
    .hero p { color:#CBD5E1; max-width:72ch; font-size:1.05rem; }
    .evidence { background:#111C31; border:1px solid rgba(45,212,191,.35); border-radius:16px; padding:1rem 1.1rem; }
    .decision { background:#FFF7E8; color:#172029; border-left:5px solid #0F766E; border-radius:12px; padding:1rem 1.1rem; }
    .decision strong { color:#0F766E; }
    .privacy { background:rgba(251,113,133,.10); border:1px solid rgba(251,113,133,.45); border-radius:12px; padding:.8rem 1rem; }
    [data-testid="stMetric"] { background:#111C31; border:1px solid rgba(148,163,184,.22); padding:.8rem; border-radius:12px; }
    [data-testid="stDataFrame"] { border:1px solid rgba(251,191,36,.25); border-radius:12px; overflow:hidden; }
    .stButton > button, .stDownloadButton > button { border-radius:10px; font-weight:700; }
    code { color:#A3E635 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_sample() -> pd.DataFrame:
    return pd.read_excel(SAMPLE_PATH)


def read_uploaded(uploaded) -> tuple[pd.DataFrame | None, str]:
    if uploaded is None:
        return None, ""
    raw = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix.lower()
    try:
        if suffix == ".xlsx":
            book = pd.ExcelFile(BytesIO(raw))
            sheet = st.sidebar.selectbox("Hoja del libro", book.sheet_names)
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


def fmt(value: float, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    if value != 0 and abs(value) < 0.001:
        return f"{value:.2e}"
    return f"{value:,.{digits}f}"


def selectable_columns(data: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    identifiers = [
        column for column in data.columns
        if column.lower() == "id" or column.lower().startswith("id_") or column.lower().endswith("_id")
    ]
    numeric = [column for column in data.select_dtypes(include=np.number).columns if column not in identifiers]
    categorical = [
        column for column in data.columns
        if column not in identifiers and 2 <= data[column].nunique(dropna=True) <= 20
    ]
    return numeric, categorical, identifiers


def conclusion_t(result: dict) -> tuple[str, str]:
    l1, l2 = result["levels"]
    if result["significant"]:
        observation = (
            f"La muestra aporta evidencia de que el promedio de **{result['outcome']}** difiere entre "
            f"**{l1}** y **{l2}** (p = {fmt(result['pvalue'])}). La diferencia estimada "
            f"{l1} − {l2} es **{fmt(result['difference'])}** unidades."
        )
    else:
        observation = (
            f"Con estos datos no hay evidencia suficiente para afirmar que el promedio de "
            f"**{result['outcome']}** difiere entre **{l1}** y **{l2}** (p = {fmt(result['pvalue'])})."
        )
    limit = "Esto no demuestra que pertenecer a un grupo cause la diferencia observada."
    return observation, limit


def report_html(title: str, source: str, hypothesis: str, interpretation: str, body: str) -> bytes:
    safe = lambda text: html.escape(str(text)).replace("\n", "<br>")
    document = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
    <title>{safe(title)}</title><style>
    body{{font-family:Arial,sans-serif;color:#172029;background:#f4efe6;margin:0;padding:36px}}
    main{{max-width:850px;margin:auto;background:#fffaf2;padding:36px;border:1px solid #d8c7a4;border-radius:16px}}
    h1{{color:#0f766e}} h2{{color:#b45309;border-bottom:2px solid #c8962d;padding-bottom:6px}}
    .meta{{color:#53616d}} .box{{background:#eef8f6;border-left:4px solid #0f766e;padding:14px}}
    </style></head><body><main><h1>{safe(title)}</h1>
    <p class="meta">Fuente: {safe(source)}</p><h2>Hipótesis previa</h2><p>{safe(hypothesis)}</p>
    <h2>Evidencia</h2><div class="box">{body}</div><h2>Mi interpretación</h2>
    <p>{safe(interpretation)}</p><h2>Límite</h2><p>Este análisis muestra asociación; por sí solo no demuestra causalidad.</p>
    </main></body></html>"""
    return document.encode("utf-8")


def code_panel(kind: str) -> None:
    snippets = {
        "t": """from scipy import stats

grupo_a = datos.loc[datos[grupo] == nivel_a, respuesta].dropna()
grupo_b = datos.loc[datos[grupo] == nivel_b, respuesta].dropna()
t, p_value = stats.ttest_ind(grupo_a, grupo_b, equal_var=False)
""",
        "simple": """import statsmodels.api as sm

X = sm.add_constant(datos[[predictor]])
modelo = sm.OLS(datos[respuesta], X).fit()
print(modelo.summary())
""",
        "multiple": """import pandas as pd
import statsmodels.api as sm

indicadores = pd.get_dummies(datos[categoricas], drop_first=True, dtype=float)
X = pd.concat([datos[numericas], indicadores], axis=1)
X = sm.add_constant(X)
modelo = sm.OLS(datos[respuesta], X).fit()
print(modelo.summary())
""",
    }
    with st.expander("¿Cómo se calculó? Ver Python reproducible"):
        st.code(snippets[kind], language="python")
        st.caption("El repositorio contiene validaciones y el tratamiento completo de categorías y faltantes.")


def reset_reveal(prefix: str) -> None:
    st.session_state.pop(f"{prefix}_revealed", None)


st.markdown(
    """<div class="hero"><p><strong>Laboratorio de Modelos Supervisados</strong></p>
    <h1>De una salida estadística a una decisión defendible</h1>
    <p>Formula primero una expectativa, observa la evidencia y termina diciendo qué harías y qué no puedes concluir.</p></div>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Datos")
    source_choice = st.radio("Fuente", ["Muestra ICFES", "Cargar mis datos"])
    if source_choice == "Muestra ICFES":
        data = load_sample()
        source_name = "Muestra ICFES 5000"
    else:
        uploaded = st.file_uploader("CSV o XLSX · máximo 25 MB", type=["csv", "xlsx"])
        data, source_name = read_uploaded(uploaded)
    st.markdown(
        '<div class="privacy"><strong>Privacidad</strong><br>No cargues nombres, documentos ni información confidencial.</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    route = st.radio(
        "Recorrido",
        ["1 · Prueba t y p-value", "2 · Regresión simple", "3 · Regresión múltiple"],
    )

if data is None:
    st.info("Carga un archivo CSV o XLSX para comenzar, o usa la muestra ICFES.")
    st.stop()

data_signature = (
    source_name,
    len(data),
    tuple(str(column) for column in data.columns),
    int(pd.util.hash_pandas_object(data.head(100), index=True).sum()),
)
if st.session_state.get("data_signature") != data_signature:
    for key in list(st.session_state):
        if key.endswith("_result") or key.endswith("_bundle") or key.endswith("_revealed"):
            st.session_state.pop(key, None)
    st.session_state.data_signature = data_signature

numeric_columns, categorical_columns, identifiers = selectable_columns(data)
with st.expander("Revisar la base antes de analizar", expanded=False):
    a, b, c = st.columns(3)
    a.metric("Filas", f"{len(data):,}")
    b.metric("Columnas", len(data.columns))
    c.metric("Datos faltantes", f"{int(data.isna().sum().sum()):,}")
    if identifiers:
        st.info("Por privacidad, estas columnas no se ofrecen como predictores: " + ", ".join(identifiers))
    st.dataframe(data.head(20), width="stretch", hide_index=True)
    types = pd.DataFrame({"Variable": data.columns, "Tipo detectado": data.dtypes.astype(str), "Faltantes": data.isna().sum().values})
    st.dataframe(types, width="stretch", hide_index=True)

if not numeric_columns:
    st.error("La base no contiene variables numéricas utilizables.")
    st.stop()


if route.startswith("1"):
    st.header("¿La diferencia podría explicarse por azar?")
    st.write("La prueba t compara una diferencia observada con la variación interna de dos grupos.")
    left, right = st.columns(2)
    outcome = left.selectbox("Variable numérica", numeric_columns, index=numeric_columns.index("puntaje_global") if "puntaje_global" in numeric_columns else 0)
    possible_groups = [column for column in categorical_columns if column != outcome]
    if not possible_groups:
        st.error("No hay una variable con entre 2 y 20 grupos.")
        st.stop()
    default_group = possible_groups.index("internet_casa") if "internet_casa" in possible_groups else 0
    group = right.selectbox("Variable que define los grupos", possible_groups, index=default_group)
    levels_available = sorted(data[group].dropna().astype(str).unique().tolist())
    levels = st.multiselect("Compara exactamente dos grupos", levels_available, default=levels_available[:2], max_selections=2)
    hypothesis = st.text_area(
        "Antes de calcular: ¿qué diferencia esperas y por qué?",
        placeholder="Espero que el grupo… tenga, en promedio… No estoy afirmando causalidad porque…",
        key="t_hypothesis",
    )
    if st.button("Calcular la evidencia", type="primary", key="run_t"):
        try:
            normalized = data.copy()
            normalized[group] = normalized[group].astype(str)
            st.session_state.t_result = welch_t_test(normalized, outcome, group, levels)
            st.session_state.t_source = source_name
            st.session_state.t_config = (outcome, group, tuple(levels))
            reset_reveal("t")
        except AnalysisError as exc:
            st.error(str(exc))

    current_t_config = (outcome, group, tuple(levels))
    result = st.session_state.get("t_result") if st.session_state.get("t_config") == current_t_config else None
    if result:
        st.subheader("La salida")
        m1, m2, md, pv = st.columns(4)
        m1.metric(f"Media · {result['levels'][0]}", fmt(result["means"][0]))
        m2.metric(f"Media · {result['levels'][1]}", fmt(result["means"][1]))
        md.metric("Diferencia", fmt(result["difference"]))
        pv.metric("p-value", fmt(result["pvalue"]))
        summary_frame = pd.DataFrame({
            group: result["levels"], "n": result["n"], "Media": result["means"]
        })
        chart = alt.Chart(summary_frame).mark_bar(color="#2DD4BF").encode(
            x=alt.X(f"{group}:N", title=group), y=alt.Y("Media:Q", title=f"Promedio de {result['outcome']}"),
            tooltip=[group, "n", alt.Tooltip("Media:Q", format=".2f")],
        ).properties(height=300)
        st.altair_chart(chart, width="stretch")
        st.dataframe(pd.DataFrame({
            "Estadístico": ["Diferencia", "IC 95% inferior", "IC 95% superior", "t", "gl Welch", "p-value"],
            "Valor": [result["difference"], result["ci"][0], result["ci"][1], result["statistic"], result["df"], result["pvalue"]],
        }), hide_index=True, width="stretch")
        observation, limit = conclusion_t(result)
        st.markdown(f'<div class="decision"><strong>Lectura guiada</strong><br>{observation}<br><br><strong>Límite:</strong> {limit}</div>', unsafe_allow_html=True)
        if result["dropped_rows"]:
            st.caption(f"Se usaron {result['used_rows']:,} filas; {result['dropped_rows']:,} quedaron fuera por grupo, faltantes o formato.")
        code_panel("t")
        interpretation = st.text_area("Escribe ahora tu conclusión y lo que no puedes concluir", key="t_interpretation")
        if st.button("Guardar mi interpretación y comparar", key="reveal_t", disabled=not interpretation.strip()):
            st.session_state.t_revealed = True
        if st.session_state.get("t_revealed"):
            st.success("Comprueba: ¿nombraste los grupos, dirección, magnitud, p-value y límite causal?")
            st.markdown(observation + "  \n" + limit)
            body = (
                f"p-value: {fmt(result['pvalue'])}; diferencia: {fmt(result['difference'])}; "
                f"IC 95%: [{fmt(result['ci'][0])}, {fmt(result['ci'][1])}]."
            )
            st.download_button(
                "Descargar mi evidencia en HTML",
                report_html("Prueba t y p-value", st.session_state.get("t_source", source_name), hypothesis, interpretation, body),
                file_name="evidencia_prueba_t.html",
                mime="text/html",
            )


elif route.startswith("2"):
    st.header("¿Cuánto cambia el resultado esperado?")
    st.write("La correlación resume fuerza y dirección; la regresión estima cuánto cambia el valor esperado.")
    left, right = st.columns(2)
    outcome = left.selectbox("Respuesta Y", numeric_columns, index=numeric_columns.index("puntaje_global") if "puntaje_global" in numeric_columns else 0)
    predictors = [column for column in numeric_columns if column != outcome]
    if not predictors:
        st.error("Necesitas otra variable numérica para usarla como predictor.")
        st.stop()
    default_x = predictors.index("estrato_num") if "estrato_num" in predictors else 0
    predictor = right.selectbox("Predictor X", predictors, index=default_x)
    hypothesis = st.text_area(
        "Antes de ajustar: ¿qué signo esperas para la pendiente y qué significaría?",
        placeholder="Espero una pendiente positiva/negativa porque…",
        key="simple_hypothesis",
    )
    if st.button("Ajustar regresión simple", type="primary", key="run_simple"):
        try:
            bundle = fit_regression(data, outcome, [predictor])
            st.session_state.simple_bundle = bundle
            st.session_state.simple_source = source_name
            st.session_state.simple_names = (outcome, predictor)
            st.session_state.simple_config = (outcome, predictor)
            reset_reveal("simple")
        except AnalysisError as exc:
            st.error(str(exc))

    bundle = st.session_state.get("simple_bundle") if st.session_state.get("simple_config") == (outcome, predictor) else None
    if bundle:
        outcome, predictor = st.session_state.simple_names
        summary = model_summary(bundle)
        coefficients = coefficient_table(bundle)
        slope = float(bundle.model.params[predictor])
        pvalue = float(bundle.model.pvalues[predictor])
        st.subheader("La salida")
        a, b, c, d = st.columns(4)
        a.metric("Pendiente", fmt(slope))
        b.metric("R²", fmt(summary["r2"]))
        c.metric("p-value", fmt(pvalue))
        d.metric("RMSE descriptivo", fmt(summary["rmse"]))
        chart_data = bundle.clean_data[[predictor, outcome]].copy()
        line_x = np.linspace(chart_data[predictor].min(), chart_data[predictor].max(), 100)
        line_data = pd.DataFrame({predictor: line_x, "Estimación": bundle.model.params["const"] + slope * line_x})
        points = alt.Chart(chart_data.sample(min(len(chart_data), 2000), random_state=7)).mark_circle(opacity=.35, color="#38BDF8").encode(
            x=alt.X(f"{predictor}:Q"), y=alt.Y(f"{outcome}:Q"), tooltip=[predictor, outcome]
        )
        line = alt.Chart(line_data).mark_line(color="#FBBF24", strokeWidth=3).encode(x=f"{predictor}:Q", y="Estimación:Q")
        st.altair_chart((points + line).properties(height=380), width="stretch")
        st.dataframe(coefficients.style.format(precision=4), width="stretch", hide_index=True)
        direction = "aumenta" if slope >= 0 else "disminuye"
        significance = "aporta evidencia de una asociación lineal" if pvalue < .05 else "no aporta evidencia suficiente de una asociación lineal"
        st.markdown(
            f'<div class="decision"><strong>Lectura guiada</strong><br>Por cada unidad adicional de <strong>{html.escape(predictor)}</strong>, '
            f'el valor esperado de <strong>{html.escape(outcome)}</strong> {direction} en <strong>{fmt(abs(slope))}</strong> unidades. '
            f'El p-value {significance}. El R² indica que el modelo describe {summary["r2"]:.1%} de la variación observada, no que sea causal.</div>',
            unsafe_allow_html=True,
        )
        code_panel("simple")
        st.subheader("Probar un valor")
        new_x = st.number_input(f"Nuevo valor de {predictor}", value=float(bundle.clean_data[predictor].median()))
        expected = predict_profile(bundle, {predictor: new_x})
        st.metric(f"Valor esperado de {outcome}", fmt(expected))
        interpretation = st.text_area("Escribe tu frase de negocio y una limitación", key="simple_interpretation")
        if st.button("Guardar mi interpretación y comparar", key="reveal_simple", disabled=not interpretation.strip()):
            st.session_state.simple_revealed = True
        if st.session_state.get("simple_revealed"):
            st.success("Comprueba: dirección, magnitud, unidades, p-value, R² y ausencia de causalidad.")
            body = f"Pendiente: {fmt(slope)}; p-value: {fmt(pvalue)}; R²: {fmt(summary['r2'])}; n: {summary['n']}."
            st.download_button(
                "Descargar mi evidencia en HTML",
                report_html("Regresión lineal simple", st.session_state.get("simple_source", source_name), hypothesis, interpretation, body),
                file_name="evidencia_regresion_simple.html",
                mime="text/html",
            )


else:
    st.header("¿Qué cambia cuando consideramos varias explicaciones?")
    st.write("Ahora cada coeficiente se interpreta manteniendo constantes las demás variables del modelo.")
    outcome = st.selectbox("Respuesta Y", numeric_columns, index=numeric_columns.index("puntaje_global") if "puntaje_global" in numeric_columns else 0)
    numeric_options = [column for column in numeric_columns if column != outcome]
    default_numeric = [column for column in ["estrato_num", "personas_hogar_num"] if column in numeric_options]
    numeric_selected = st.multiselect("Predictores numéricos", numeric_options, default=default_numeric)
    categorical_options = [column for column in categorical_columns if column != outcome and column not in numeric_selected]
    default_categorical = [column for column in ["internet_casa", "tipo_colegio"] if column in categorical_options]
    categorical_selected = st.multiselect("Predictores categóricos", categorical_options, default=default_categorical)
    references: dict[str, str] = {}
    if categorical_selected:
        st.subheader("Elige qué significa comparar")
        st.caption("La categoría de referencia no recibe columna propia: los demás coeficientes se leen frente a ella.")
        columns = st.columns(min(3, len(categorical_selected)))
        for index, column in enumerate(categorical_selected):
            levels = sorted(data[column].dropna().astype(str).unique().tolist())
            references[column] = columns[index % len(columns)].selectbox(
                f"Referencia · {column}", levels, key=f"reference_{column}"
            )
    hypothesis = st.text_area(
        "Antes de ajustar: elige una variable y anticipa su efecto manteniendo constantes las demás",
        key="multiple_hypothesis",
    )
    if st.button("Ajustar regresión múltiple", type="primary", key="run_multiple"):
        try:
            bundle = fit_regression(data, outcome, numeric_selected, categorical_selected, references)
            st.session_state.multiple_bundle = bundle
            st.session_state.multiple_source = source_name
            st.session_state.multiple_outcome = outcome
            st.session_state.multiple_config = (
                outcome,
                tuple(numeric_selected),
                tuple(categorical_selected),
                tuple(sorted(references.items())),
            )
            reset_reveal("multiple")
        except AnalysisError as exc:
            st.error(str(exc))

    current_multiple_config = (
        outcome,
        tuple(numeric_selected),
        tuple(categorical_selected),
        tuple(sorted(references.items())),
    )
    bundle = st.session_state.get("multiple_bundle") if st.session_state.get("multiple_config") == current_multiple_config else None
    if bundle:
        outcome = st.session_state.multiple_outcome
        summary = model_summary(bundle)
        coefficients = coefficient_table(bundle)
        st.subheader("Cómo quedó representado el modelo")
        if bundle.encoded_columns:
            encoding_rows = []
            for column, created in bundle.encoded_columns.items():
                encoding_rows.append({
                    "Variable original": column,
                    "Referencia": bundle.references[column],
                    "Indicadores creados": ", ".join(created),
                })
            st.dataframe(pd.DataFrame(encoding_rows), width="stretch", hide_index=True)
        a, b, c, d = st.columns(4)
        a.metric("R²", fmt(summary["r2"]))
        b.metric("R² ajustado", fmt(summary["r2_adj"]))
        c.metric("p-value global", fmt(summary["f_pvalue"]))
        d.metric("Filas usadas", f"{summary['n']:,}")
        if bundle.numeric_predictors:
            focus = bundle.numeric_predictors[0]
            simple_comparison = fit_regression(data, outcome, [focus])
            simple_summary = model_summary(simple_comparison)
            comparison = pd.DataFrame([
                {
                    "Modelo": f"Simple · {focus}",
                    "n": simple_summary["n"],
                    "Coeficiente focal": simple_comparison.model.params[focus],
                    "p-value focal": simple_comparison.model.pvalues[focus],
                    "R²": simple_summary["r2"],
                    "R² ajustado": simple_summary["r2_adj"],
                },
                {
                    "Modelo": "Múltiple",
                    "n": summary["n"],
                    "Coeficiente focal": bundle.model.params[focus],
                    "p-value focal": bundle.model.pvalues[focus],
                    "R²": summary["r2"],
                    "R² ajustado": summary["r2_adj"],
                },
            ])
            with st.expander(f"Comparar qué ocurrió con {focus}", expanded=True):
                st.dataframe(comparison.style.format(precision=4), width="stretch", hide_index=True)
                if simple_summary["n"] != summary["n"]:
                    st.caption("Los modelos usan distinto número de filas completas; tenga esto en cuenta al comparar.")
        st.subheader("Salida completa")
        st.dataframe(coefficients.style.format(precision=4), width="stretch", hide_index=True)
        plot_data = coefficients.loc[coefficients["Variable"] != "const"].copy()
        coefficient_chart = alt.Chart(plot_data).mark_bar(color="#2DD4BF").encode(
            x=alt.X("Coeficiente:Q", title="Cambio estimado"),
            y=alt.Y("Variable:N", sort="-x", title=None),
            tooltip=["Variable", alt.Tooltip("Coeficiente:Q", format=".3f"), alt.Tooltip("p-value:Q", format=".3g")],
            color=alt.condition("datum['p-value'] < 0.05", alt.value("#2DD4BF"), alt.value("#94A3B8")),
        ).properties(height=max(240, 34 * len(plot_data)))
        st.altair_chart(coefficient_chart, width="stretch")
        st.markdown(
            '<div class="decision"><strong>Regla de lectura</strong><br>Un coeficiente numérico compara una unidad adicional. '
            'Un indicador compara esa categoría con la referencia. En ambos casos la frase termina con '
            '<em>manteniendo constantes las demás variables incluidas</em>.</div>',
            unsafe_allow_html=True,
        )
        st.subheader("Multicolinealidad: una señal para investigar")
        vif = vif_table(bundle)
        if vif.empty:
            st.info("El VIF necesita al menos dos predictores.")
        else:
            st.dataframe(vif.style.format({"VIF": "{:.2f}"}), width="stretch", hide_index=True)
            if (vif["VIF"] >= 5).any():
                st.warning("Algún VIF supera 5. Revisa si varias variables cuentan casi la misma historia; no elimines automáticamente.")
        code_panel("multiple")
        st.subheader("Predecir un perfil")
        profile: dict[str, object] = {}
        inputs = st.columns(2)
        position = 0
        for column in bundle.numeric_predictors:
            profile[column] = inputs[position % 2].number_input(
                column, value=float(bundle.clean_data[column].median()), key=f"profile_num_{column}"
            )
            position += 1
        for column in bundle.categorical_predictors:
            levels = sorted(bundle.clean_data[column].astype(str).unique().tolist())
            profile[column] = inputs[position % 2].selectbox(column, levels, key=f"profile_cat_{column}")
            position += 1
        if profile:
            expected = predict_profile(bundle, profile)
            st.metric(f"Valor esperado de {outcome}", fmt(expected))
        interpretation = st.text_area(
            "Interpreta un coeficiente, recomienda una acción y escribe una limitación",
            key="multiple_interpretation",
        )
        if st.button("Guardar mi interpretación y comparar", key="reveal_multiple", disabled=not interpretation.strip()):
            st.session_state.multiple_revealed = True
        if st.session_state.get("multiple_revealed"):
            st.success("Comprueba: variable, referencia si aplica, signo, unidades, condición sobre las demás variables y límite causal.")
            body = (
                f"R²: {fmt(summary['r2'])}; R² ajustado: {fmt(summary['r2_adj'])}; "
                f"p-value global: {fmt(summary['f_pvalue'])}; n: {summary['n']}."
            )
            st.download_button(
                "Descargar mi evidencia en HTML",
                report_html("Regresión lineal múltiple", st.session_state.get("multiple_source", source_name), hypothesis, interpretation, body),
                file_name="evidencia_regresion_multiple.html",
                mime="text/html",
            )

st.divider()
st.caption("Universidad Externado de Colombia · La evidencia orienta decisiones; no reemplaza el juicio ni demuestra causalidad.")
