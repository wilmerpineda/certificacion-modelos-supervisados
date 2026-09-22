"""Genera la guía docente en PDF con una maquetación estable y legible."""

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
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "guia-docente-sesiones-5-y-6.pdf"
GREEN = colors.HexColor("#006633")
LIGHT_GREEN = colors.HexColor("#E7F1EC")
GOLD = colors.HexColor("#C9A227")
INK = colors.HexColor("#242424")
MUTED = colors.HexColor("#5F6368")


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("CourseSans", str(regular)))
        pdfmetrics.registerFont(TTFont("CourseSans-Bold", str(bold)))
        return "CourseSans", "CourseSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def page_decor(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 8 * mm, width, 8 * mm, fill=1, stroke=0)
    canvas.setFont(FONT, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 9 * mm, "Universidad Externado de Colombia · Certificación en Ciencia de Datos")
    canvas.drawRightString(width - 15 * mm, 9 * mm, f"{doc.page}")
    canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "TitleCourse",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=22,
        leading=25,
        textColor=GREEN,
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "SubtitleCourse",
        parent=styles["Normal"],
        fontName=FONT,
        fontSize=10.5,
        leading=13,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "HeadingCourse",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=15,
        leading=18,
        textColor=GREEN,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        "SubheadingCourse",
        parent=styles["Heading3"],
        fontName=FONT_BOLD,
        fontSize=11.5,
        leading=14,
        textColor=INK,
        spaceBefore=2.5 * mm,
        spaceAfter=1.3 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        "BodyCourse",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=9.3,
        leading=12,
        textColor=INK,
        spaceAfter=1.8 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "SmallCourse",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=8.2,
        leading=10.2,
        textColor=INK,
    )
)


def p(text: str, style: str = "BodyCourse") -> Paragraph:
    return Paragraph(text, styles[style])


def agenda_table(rows):
    data = [[p("Minutos", "SmallCourse"), p("Actividad", "SmallCourse"), p("Evidencia observable", "SmallCourse")]]
    data.extend([[p(a, "SmallCourse"), p(b, "SmallCourse"), p(c, "SmallCourse")] for a, b, c in rows])
    table = Table(data, colWidths=[22 * mm, 55 * mm, 92 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C9C0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREEN]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def bullet_list(items):
    return [p(f"• {item}") for item in items]


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title="Guía docente · Sesiones 5 y 6",
        author="Universidad Externado de Colombia",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="course", frames=[frame], onPage=page_decor)])

    story = []
    logo = ROOT / "assets" / "brand" / "logo-externado.png"
    if logo.exists():
        img = Image(str(logo), width=29 * mm, height=29 * mm)
        img.hAlign = "CENTER"
        story.extend([img, Spacer(1, 1.5 * mm)])
    story.extend(
        [
            p("Guía docente · Sesiones 5 y 6", "TitleCourse"),
            p("Preparación, clasificación y métricas orientadas a decisiones", "SubtitleCourse"),
            p("Propósito", "HeadingCourse"),
            p(
                "Al terminar las dos sesiones, los participantes deben poder justificar cómo prepararon una base y elegir un clasificador según el costo del error, sin confundir desempeño predictivo, importancia y causalidad."
            ),
            p("Sesión 5 · Preparar la base y primer clasificador", "HeadingCourse"),
            agenda_table(
                [
                    ("0–15", "Pregunta bancaria", "Definen decisión y unidad de análisis"),
                    ("15–40", "Objetivo y momento", "Separan información disponible y futura"),
                    ("40–75", "Cruce de tablas", "Auditan coincidencias y exclusiones"),
                    ("75–105", "Tipos de ausencia", "Distinguen blanco, desconocido, cero y no aplica"),
                    ("105–120", "Codificación", "Excluyen ID y anticipan indicadores"),
                    ("120–135", "Pausa", "—"),
                    ("135–165", "Base modelable", "Registran decisiones y controversias"),
                    ("165–195", "Regresión logística", "Obtienen probabilidades y clases"),
                    ("195–220", "Exactitud inicial", "Comparan con la regla mayoritaria"),
                    ("220–240", "Entrega y defensa", "Descargan base y bitácora"),
                ]
            ),
            p("Preguntas para intervenir", "SubheadingCourse"),
        ]
    )
    story.extend(
        bullet_list(
            [
                "¿La fila representa cliente, hogar o contacto?",
                "¿Qué población desaparece con el cruce interno?",
                "¿Por qué “Desconocido” no equivale a blanco?",
                "¿La imputación recupera el dato real?",
                "¿La variable existía antes de decidir a quién llamar?",
            ]
        )
    )
    story.extend(
        [
            p("Respuesta esperada", "SubheadingCourse"),
            p(
                "El grupo conserva un registro explícito de filas, llaves, faltantes, codificación y exclusiones. No hay una única política correcta: la elección debe ser coherente con la pregunta y aplicarse dentro del proceso de modelado."
            ),
            p("Sesión 6 · Algoritmos y métricas", "HeadingCourse"),
            agenda_table(
                [
                    ("0–15", "Recuperación", "Explican el primer clasificador"),
                    ("15–35", "Trampa de exactitud", "Detectan el clasificador mayoritario"),
                    ("35–65", "Matriz de confusión", "Traducen falsos positivos y negativos al negocio"),
                    ("65–100", "Métricas", "Relacionan cada métrica con una pregunta"),
                    ("100–120", "Auditoría en Excel", "Reconstruyen matriz y fórmulas"),
                    ("120–135", "Pausa", "—"),
                    ("135–165", "Cuatro algoritmos", "Comparan con la misma evaluación"),
                    ("165–190", "ROC y AUC", "Distinguen ordenamiento y decisión"),
                    ("190–215", "Árbol e importancia", "Leen reglas y evitan causalidad"),
                    ("215–235", "Dos escenarios", "Eligen métrica según costo"),
                    ("235–240", "Salida", "Declaran modelo, error y límite"),
                ]
            ),
            p("Revelación del desbalance", "SubheadingCourse"),
            p(
                "No anuncie al inicio la tasa de aceptación. Muestre primero la exactitud y solicite una elección. Después revele que la regla <b>siempre No</b> supera 88 % y abra la matriz. La corrección no es “la exactitud es mala”, sino “la exactitud sola responde una pregunta insuficiente”."
            ),
            p("Lecturas esperadas", "SubheadingCourse"),
        ]
    )
    story.extend(
        bullet_list(
            [
                "<b>Precisión alta:</b> una mayor proporción de los contactados aceptaría.",
                "<b>Recall alto:</b> se detecta una mayor proporción de quienes aceptarían.",
                "<b>Especificidad alta:</b> se evita contactar a una mayor proporción de quienes no aceptarían.",
                "<b>F1:</b> resume precisión y recall, pero no incorpora costos explícitos.",
                "<b>AUC:</b> resume ordenamiento a través de umbrales; no fija una operación.",
            ]
        )
    )
    story.extend(
        [
            KeepTogether(
                [
                    p("Árbol e importancia", "SubheadingCourse"),
                    p(
                        "Pida leer un camino completo y terminar con una probabilidad o clase de hoja. Corrija “la variable más importante causa la aceptación”. Una lectura responsable es: “el árbol usó esta variable con mayor contribución a la reducción de impureza en estos datos”."
                    ),
                ]
            ),
            p("Criterio de logro", "HeadingCourse"),
        ]
    )
    story.extend(
        bullet_list(
            [
                "Población y momento de predicción explícitos.",
                "Decisiones de preparación auditables.",
                "Métrica vinculada a un costo del negocio.",
                "Conteo concreto de errores.",
                "Recomendación y límite explícitos. El código no es el criterio principal.",
            ]
        )
    )
    story.extend(
        [
            p("Plan de contingencia", "HeadingCourse"),
            p(
                "Si falla internet, use las capturas de resultados y los archivos de referencia. La base y las predicciones permiten trabajar la matriz y las métricas sin volver a entrenar. Si el ajuste tarda, ejecute una vez desde el equipo docente y distribuya <b>predicciones_referencia.csv</b>."
            ),
            Spacer(1, 2 * mm),
            Table(
                [[p("Idea transversal", "SmallCourse"), p("La preparación y la métrica solo son correctas en relación con la decisión que se quiere tomar.", "SmallCourse")]],
                colWidths=[32 * mm, 137 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), GREEN),
                        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                        ("BACKGROUND", (1, 0), (1, 0), LIGHT_GREEN),
                        ("BOX", (0, 0), (-1, -1), 0.7, GOLD),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                ),
            ),
        ]
    )
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
