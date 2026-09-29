"""Genera los PDF de las sesiones 7-8, random forest y proyecto final."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
GREEN = colors.HexColor("#006633")
DARK_GREEN = colors.HexColor("#004B32")
LIGHT_GREEN = colors.HexColor("#E7F1EC")
GOLD = colors.HexColor("#C9A227")
INK = colors.HexColor("#242424")
MUTED = colors.HexColor("#5F6368")
LINE = colors.HexColor("#B8C9C0")


def register_fonts() -> tuple[str, str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    mono = Path("C:/Windows/Fonts/consola.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("CourseSansV", str(regular)))
        pdfmetrics.registerFont(TTFont("CourseSansV-Bold", str(bold)))
        body, strong = "CourseSansV", "CourseSansV-Bold"
    else:
        body, strong = "Helvetica", "Helvetica-Bold"
    if mono.exists():
        pdfmetrics.registerFont(TTFont("CourseMonoV", str(mono)))
        fixed = "CourseMonoV"
    else:
        fixed = "Courier"
    return body, strong, fixed


FONT, FONT_BOLD, FONT_MONO = register_fonts()
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("CourseTitleV", fontName=FONT_BOLD, fontSize=22, leading=25, textColor=GREEN, alignment=TA_CENTER, spaceAfter=3 * mm))
styles.add(ParagraphStyle("CourseSubtitleV", fontName=FONT, fontSize=10.5, leading=13, textColor=MUTED, alignment=TA_CENTER, spaceAfter=5 * mm))
styles.add(ParagraphStyle("CourseH1V", fontName=FONT_BOLD, fontSize=15, leading=18, textColor=GREEN, spaceBefore=3.5 * mm, spaceAfter=2 * mm, keepWithNext=True))
styles.add(ParagraphStyle("CourseH2V", fontName=FONT_BOLD, fontSize=11.2, leading=14, textColor=DARK_GREEN, spaceBefore=2.5 * mm, spaceAfter=1.2 * mm, keepWithNext=True))
styles.add(ParagraphStyle("CourseBodyV", fontName=FONT, fontSize=9.2, leading=11.7, textColor=INK, spaceAfter=1.7 * mm))
styles.add(ParagraphStyle("CourseSmallV", fontName=FONT, fontSize=8.0, leading=9.8, textColor=INK))
styles.add(ParagraphStyle("CourseCodeV", fontName=FONT_MONO, fontSize=8.2, leading=10.2, textColor=INK, leftIndent=4 * mm, rightIndent=4 * mm, borderColor=LINE, borderWidth=0.5, borderPadding=5, backColor=colors.HexColor("#F4F7F5"), spaceAfter=2 * mm))


def p(text: str, style: str = "CourseBodyV") -> Paragraph:
    return Paragraph(text, styles[style])


def page_decor(canvas, doc) -> None:
    width, height = letter
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 8 * mm, width, 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(15 * mm, 8.5 * mm, "Universidad Externado de Colombia - Certificacion en Ciencia de Datos")
    canvas.drawCentredString(width / 2, 8.5 * mm, str(doc.page))
    canvas.restoreState()


def document(path: Path, title: str) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        str(path), pagesize=letter, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=21 * mm, title=title,
        author="Universidad Externado de Colombia",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="course", frames=[frame], onPage=page_decor)])
    return doc


def opening(title: str, subtitle: str) -> list:
    story: list = []
    logo = ROOT / "assets" / "brand" / "logo-externado.png"
    if logo.exists():
        image = Image(str(logo), width=25 * mm, height=25 * mm)
        image.hAlign = "CENTER"
        story.extend([image, Spacer(1, 1.5 * mm)])
    story.extend([p(title, "CourseTitleV"), p(subtitle, "CourseSubtitleV")])
    return story


def bullets(items: list[str]) -> list[Paragraph]:
    return [p(f"&#8226; {item}") for item in items]


def grid(headers: list[str], rows: list[tuple], widths: list[float]) -> Table:
    data = [[p(value, "CourseSmallV") for value in headers]]
    data.extend([[p(str(value), "CourseSmallV") for value in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREEN]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def callout(label: str, text: str) -> Table:
    table = Table([[p(label, "CourseSmallV"), p(text, "CourseSmallV")]], colWidths=[33 * mm, 136 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.7, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build_teacher_guide() -> None:
    path = OUTPUT / "guia-docente-sesiones-7-y-8.pdf"
    doc = document(path, "Guia docente - Sesiones 7 y 8")
    story = opening("Guia docente - Sesiones 7 y 8", "Validacion, fuga de datos y decisiones economicas")
    story.extend([
        p("Proposito", "CourseH1V"),
        p("Los participantes auditan un resultado perfecto, validan sin compartir informacion y convierten probabilidades en una lista operativa mediante supuestos explicitos."),
        p("Sesion 7 - Validacion y fuga", "CourseH1V"),
        grid(["Min", "Actividad", "Evidencia"], [
            ("0-20", "Resultado perfecto", "Formulan hipotesis de auditoria"),
            ("20-50", "Tres particiones", "Asignan una funcion a cada muestra"),
            ("50-80", "Brecha", "Distinguen ajuste y generalizacion"),
            ("80-110", "Evaluacion incorrecta", "Detectan reutilizacion de filas"),
            ("110-125", "Fuga plantada", "Cuestionan disponibilidad temporal"),
            ("125-140", "Pausa", "-"),
            ("140-170", "Validacion cruzada", "Reportan media y variabilidad"),
            ("170-200", "Repeticion sin fuga", "Comparan antes y despues"),
            ("200-225", "Bosque en Excel", "Siguen reglas y reconstruyen Gini"),
            ("225-240", "Explicacion", "Justifican por que parecia perfecto"),
        ], [18 * mm, 62 * mm, 89 * mm]),
        p("Revelacion", "CourseH2V"),
        p("No anuncie duracion_llamada. Pida ordenar importancias y preguntar cuando existe cada variable. La fuga puede validar bien historicamente: el error esta en el momento de disponibilidad."),
        callout("Respuesta esperada", "El resultado se inflaba por informacion posterior al contacto y por confundir ajuste con generalizacion. La correccion combina particiones, pipeline por pliegue y variables disponibles antes de actuar."),
        PageBreak(),
        p("Mini random forest", "CourseH1V"),
        p("Siete arboles, profundidad maxima dos, bootstrap y dos variables candidatas por division. Python aprende los nodos; Excel reconstruye recorridos, probabilidades e importancia."),
        p("Reduccion por nodo", "CourseH2V"),
        p("N_padre x Gini_padre - N_izquierdo x Gini_izquierdo - N_derecho x Gini_derecho", "CourseCodeV"),
        p("Importancia", "CourseH2V"),
    ])
    story.extend(bullets([
        "sumar reducciones de los nodos que usan la variable;",
        "normalizar dentro de cada arbol;",
        "promediar los siete arboles;",
        "no interpretar como direccion, efecto o causalidad.",
    ]))
    story.extend([
        p("Sesion 8 - Del modelo a la decision", "CourseH1V"),
        grid(["Min", "Actividad", "Evidencia"], [
            ("0-20", "Pregunta bancaria", "Recuperan decision y poblacion"),
            ("20-45", "Costos", "Traducen errores a valor"),
            ("45-80", "Tabla de cortes", "Comparan volumen, metricas y valor"),
            ("80-110", "Corte economico", "Eligen solo con validacion"),
            ("110-125", "Bloqueo", "Registran modelo, variables y corte"),
            ("125-140", "Pausa", "-"),
            ("140-170", "Prueba", "Auditan una vez la politica"),
            ("170-195", "Cartera", "Puntuan casos sin etiqueta"),
            ("195-225", "Excel", "Verifican valor, filtro y prioridad"),
            ("225-240", "Entrega", "Defienden lista, cifra y limite"),
        ], [18 * mm, 62 * mm, 89 * mm]),
        p("Supuestos", "CourseH2V"),
        p("Contribucion: COP 100.000. Costo por contacto: COP 20.000. Valor = 100.000 x TP - 20.000 x (TP + FP). En empate se conserva el corte mayor."),
        p("Intervenciones", "CourseH2V"),
    ])
    story.extend(bullets([
        "detener la eleccion del corte si ya se abrio prueba;",
        "eliminar respuesta y duracion de la cartera;",
        "pedir conteos ademas de AUC;",
        "distinguir valor esperado de ingreso garantizado.",
    ]))
    story.extend([
        callout("Criterio de logro", "Particiones correctas, fuga explicada, corte elegido en validacion, conteos en prueba y lista operativa con limite."),
        p("Contingencia", "CourseH1V"),
        p("Distribuya historico, nodos y predicciones. Excel permite reconstruir el bosque y la decision sin volver a entrenar."),
    ])
    doc.build(story)


def build_forest_guide() -> None:
    path = OUTPUT / "guia-random-forest-en-excel.pdf"
    doc = document(path, "Random forest auditable en Excel")
    story = opening("Random forest auditable en Excel", "Siete arboles, tres hojas y una importancia Gini trazable")
    story.extend([
        callout("Alcance", "Python entrena un bosque real y exporta sus nodos. Excel reproduce reglas, probabilidades e importancia. Solver se conserva para estudiar un corte, no para crecer todos los nodos."),
        p("Estructura del libro", "CourseH1V"),
        grid(["Hoja", "Contenido", "Funcion"], [
            ("Datos", "ID, particion, respuesta y cinco predictores", "Fuente visible"),
            ("Bosque", "Una fila por nodo de los siete arboles", "Reglas y reduccion Gini"),
            ("Resultados", "Probabilidades, promedio, metricas e importancia", "Auditoria final"),
        ], [30 * mm, 72 * mm, 67 * mm]),
        p("Parametros fijos", "CourseH2V"),
    ])
    story.extend(bullets([
        "7 arboles y profundidad maxima 2;",
        "bootstrap activado y semilla fija;",
        "2 variables candidatas por division;",
        "40 observaciones minimas por hoja;",
        "edad, contactos de campana, contactos previos, contacto celular y exito previo.",
    ]))
    story.extend([
        p("1. Leer un nodo", "CourseH1V"),
        p("Cada fila indica arbol, nodo, variable, umbral, hijos, cantidades por clase, Gini y probabilidad si es hoja."),
        p("Si edad <= 37, vaya al hijo izquierdo; de lo contrario, al derecho.", "CourseCodeV"),
        p("2. Seguir un cliente", "CourseH1V"),
        p("Empiece en el nodo 0. Aplique la regla, busque el hijo indicado y repita hasta llegar a Es_hoja = Si. Registre Probabilidad_hoja."),
        PageBreak(),
        p("3. Promediar los arboles", "CourseH1V"),
        p("Probabilidad_bosque = PROMEDIO(prob_arbol_1:prob_arbol_7)", "CourseCodeV"),
        p("Prediccion = SI(probabilidad_bosque >= punto_corte; 1; 0)", "CourseCodeV"),
        p("El random forest de clasificacion promedia probabilidades de clase. El corte convierte ese promedio en una accion."),
        p("4. Reconstruir Gini", "CourseH1V"),
        p("Gini = 1 - proporcion_clase_0^2 - proporcion_clase_1^2", "CourseCodeV"),
        p("Reduccion = Np x Gp - Ni x Gi - Nd x Gd", "CourseCodeV"),
        p("La reduccion es cero en una hoja. En un nodo interno es positiva cuando los hijos quedan mas puros que el padre."),
        p("5. Importancia por variable", "CourseH1V"),
        p("Use SUMAR.SI.CONJUNTO para acumular Reduccion_Gini por variable y arbol. Divida por la suma del arbol, promedie los siete porcentajes y normalice a 100 %."),
        p("6. Comprobar", "CourseH1V"),
    ])
    story.extend(bullets([
        "la probabilidad del bosque coincide con Python;",
        "las cinco importancias suman 100 %;",
        "ninguna regla usa duracion o respuesta;",
        "los siete arboles no son identicos;",
        "la matriz utiliza solo la particion indicada.",
    ]))
    story.extend([
        PageBreak(),
        p("Que aporta Excel", "CourseH1V"),
        grid(["Pregunta", "Evidencia en Excel"], [
            ("Como decide un arbol", "Camino de nodos y probabilidad de hoja"),
            ("Como decide el bosque", "Promedio de siete probabilidades"),
            ("Que variable uso mas", "Reduccion Gini acumulada"),
            ("Que no sabemos", "Direccion, causalidad y estabilidad futura"),
        ], [62 * mm, 107 * mm]),
        p("Por que no usar Solver siete veces", "CourseH1V"),
        p("Un bosque requiere bootstrap, seleccion aleatoria de variables, busqueda de cortes en cada nodo y crecimiento recursivo. Solver puede ilustrar un corte, pero repetirlo manualmente vuelve opaco y fragil el procedimiento."),
        callout("Lectura responsable", "La variable fue usada para reducir impureza en este bosque y estos datos. No significa que cambiarla cause una aceptacion."),
        p("Extension", "CourseH1V"),
        p("Compare la importancia Gini con permutacion en prueba. Si difieren, discuta correlacion entre variables, cardinalidad y dependencia de la muestra."),
    ])
    doc.build(story)


def build_project_guide() -> None:
    path = OUTPUT / "proyecto-final-instrucciones.pdf"
    doc = document(path, "Proyecto final - Vender una solucion con evidencia")
    story = opening("Proyecto final", "Vender una solucion con evidencia - grupos de 3 a 4 personas")
    story.extend([
        callout("Reto", "Elijan un problema de regresion o clasificacion y convenzan a un decisor de que la propuesta merece una prueba piloto, sin ocultar limites."),
        p("Entregables", "CourseH1V"),
        p("1. PDF ejecutivo de maximo cuatro paginas, con maximo dos visualizaciones. 2. Anexo reproducible con datos o enlace, diccionario, codigo o Excel, resultados y README."),
        p("Pagina 1 - Problema y decision", "CourseH1V"),
    ])
    story.extend(bullets([
        "usuario de la solucion y responsable de actuar;",
        "unidad de analisis y variable respuesta;",
        "momento de la prediccion;",
        "consecuencia de equivocarse.",
    ]))
    story.extend([
        p("Pagina 2 - Datos y evidencia", "CourseH1V"),
    ])
    story.extend(bullets([
        "fuente, poblacion y tamano;",
        "preparacion y variables excluidas;",
        "particion o validacion;",
        "linea base, modelo y evidencia principal.",
    ]))
    story.extend([
        PageBreak(),
        p("Pagina 3 - Propuesta accionable", "CourseH1V"),
        p("Clasificacion: metrica, punto de corte, volumen y regla operativa. Regresion: magnitud predicha, escenario y regla que convierte la prediccion en accion."),
        p("Incluyan recursos, beneficio posible y responsable de ejecutar."),
        p("Pagina 4 - Riesgos y siguiente paso", "CourseH1V"),
    ])
    story.extend(bullets([
        "fuga de datos descartada;",
        "sesgos o poblacion no representada;",
        "afirmaciones que no permite el analisis;",
        "supuesto mas sensible;",
        "prueba piloto o dato adicional.",
    ]))
    story.extend([
        p("Rubrica - 100 puntos", "CourseH1V"),
        grid(["Criterio", "Puntos"], [
            ("Problema, usuario y decision", "15"),
            ("Calidad y trazabilidad de datos", "15"),
            ("Validacion, linea base, modelo y metricas", "25"),
            ("Recomendacion y sustento numerico", "25"),
            ("Limites, riesgos y siguiente paso", "10"),
            ("Claridad y cumplimiento", "10"),
        ], [139 * mm, 30 * mm]),
        PageBreak(),
        p("Lista de comprobacion", "CourseH1V"),
    ])
    story.extend(bullets([
        "la respuesta puede observarse y existen suficientes casos;",
        "la respuesta no aparece disfrazada entre predictores;",
        "las variables existirian al momento de decidir;",
        "la linea base usa la misma muestra de evaluacion;",
        "la metrica responde al costo del error;",
        "las cifras coinciden con el anexo;",
        "la recomendacion identifica quien hace que y sobre quien;",
        "se declara al menos una limitacion material;",
        "no se usaron datos personales sin autorizacion.",
    ]))
    story.extend([
        p("Plantilla de conclusion", "CourseH1V"),
        p("Recomendamos [accion] para [poblacion] mediante [modelo o regla]. En una evaluacion fuera de muestra obtuvimos [metrica], lo que implica [conteo, magnitud o beneficio] bajo [supuesto]. Antes de escalar, proponemos [piloto] porque no podemos concluir [limite].", "CourseCodeV"),
        callout("Criterio final", "Una buena entrega no vende certeza. Vende una decision comprobable, numeros reproducibles y una forma responsable de aprender que ocurre despues."),
    ])
    doc.build(story)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_teacher_guide()
    build_forest_guide()
    build_project_guide()
    print("\n".join(str(path) for path in [
        OUTPUT / "guia-docente-sesiones-7-y-8.pdf",
        OUTPUT / "guia-random-forest-en-excel.pdf",
        OUTPUT / "proyecto-final-instrucciones.pdf",
    ]))


if __name__ == "__main__":
    main()
