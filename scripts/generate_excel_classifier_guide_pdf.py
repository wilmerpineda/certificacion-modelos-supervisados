"""Genera la guía práctica del primer clasificador logístico en Excel."""

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "guia-primer-clasificador-en-excel.pdf"
GREEN = colors.HexColor("#006633")
DARK_GREEN = colors.HexColor("#004B32")
LIGHT_GREEN = colors.HexColor("#E7F1EC")
PALE = colors.HexColor("#F6F8F7")
GOLD = colors.HexColor("#C9A227")
INK = colors.HexColor("#252525")
MUTED = colors.HexColor("#61676B")
LINE = colors.HexColor("#B7C8BF")


def register_fonts():
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    mono = Path("C:/Windows/Fonts/consola.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("GuideSans", str(regular)))
        pdfmetrics.registerFont(TTFont("GuideSans-Bold", str(bold)))
        regular_name, bold_name = "GuideSans", "GuideSans-Bold"
    else:
        regular_name, bold_name = "Helvetica", "Helvetica-Bold"
    if mono.exists():
        pdfmetrics.registerFont(TTFont("GuideMono", str(mono)))
        mono_name = "GuideMono"
    else:
        mono_name = "Courier"
    return regular_name, bold_name, mono_name


FONT, FONT_BOLD, FONT_MONO = register_fonts()


def page_decor(canvas, doc):
    width, height = letter
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 7 * mm, width, 7 * mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(15 * mm, 8.5 * mm, "Universidad Externado de Colombia - Certificación en Ciencia de Datos")
    canvas.drawRightString(width - 15 * mm, 8.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "GuideTitle",
        fontName=FONT_BOLD,
        fontSize=23,
        leading=27,
        textColor=GREEN,
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "GuideSubtitle",
        fontName=FONT,
        fontSize=11,
        leading=14,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "GuideH1",
        fontName=FONT_BOLD,
        fontSize=17,
        leading=20,
        textColor=GREEN,
        spaceBefore=3 * mm,
        spaceAfter=2.5 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        "GuideH2",
        fontName=FONT_BOLD,
        fontSize=12.5,
        leading=15,
        textColor=DARK_GREEN,
        spaceBefore=2.5 * mm,
        spaceAfter=1.5 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        "GuideBody",
        fontName=FONT,
        fontSize=9.5,
        leading=12.5,
        textColor=INK,
        spaceAfter=2 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "GuideSmall",
        fontName=FONT,
        fontSize=8.2,
        leading=10.3,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        "GuideCode",
        fontName=FONT_MONO,
        fontSize=7.7,
        leading=10,
        textColor=INK,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        "GuideCallout",
        fontName=FONT,
        fontSize=9.3,
        leading=12.3,
        textColor=INK,
        leftIndent=2 * mm,
        rightIndent=2 * mm,
    )
)


def p(text, style="GuideBody"):
    return Paragraph(text, styles[style])


def bullets(items):
    return [p(f"• {item}") for item in items]


def code_box(*lines):
    content = "<br/>".join(escape(line) for line in lines)
    box = Table([[Paragraph(content, styles["GuideCode"])]], colWidths=[174 * mm], hAlign="LEFT")
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return box


def callout(label, text, color=LIGHT_GREEN):
    table = Table(
        [[p(label, "GuideSmall"), p(text, "GuideCallout")]],
        colWidths=[32 * mm, 142 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                ("FONTNAME", (0, 0), (0, 0), FONT_BOLD),
                ("BACKGROUND", (1, 0), (1, 0), color),
                ("BOX", (0, 0), (-1, -1), 0.7, GOLD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def grid_table(headers, rows, widths):
    data = [[p(h, "GuideSmall") for h in headers]]
    data.extend([[p(str(value), "GuideSmall") for value in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREEN]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def add_step(story, number, title, body):
    story.append(p(f"Paso {number}. {title}", "GuideH2"))
    story.append(p(body))


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Guía práctica - Primer clasificador en Excel",
        author="Universidad Externado de Colombia",
        subject="Regresión logística con Solver y evaluación de clasificación",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="guide", frames=[frame], onPage=page_decor)])

    story = []
    logo = ROOT / "assets" / "brand" / "logo-externado.png"
    if logo.exists():
        iw, ih = ImageReader(str(logo)).getSize()
        target_w = 34 * mm
        image = Image(str(logo), width=target_w, height=target_w * ih / iw)
        image.hAlign = "CENTER"
        story.extend([image, Spacer(1, 3 * mm)])

    story.extend(
        [
            p("Guía práctica", "GuideTitle"),
            p("Primer clasificador en Excel con regresión logística y Solver", "GuideSubtitle"),
            callout(
                "Propósito",
                "Construir un clasificador reproducible, evaluar sus errores en una muestra de prueba y traducir las métricas a una decisión de negocio.",
            ),
            Spacer(1, 4 * mm),
            p("Qué necesita", "GuideH1"),
        ]
    )
    story.extend(
        bullets(
            [
                "Microsoft Excel con Power Query y el complemento Solver.",
                "Los archivos <b>clientes.csv</b> y <b>campanas.csv</b>.",
                "Una copia de trabajo: no modifique los archivos originales.",
                "Excel configurado con separador decimal coma y separador de argumentos punto y coma. Si su Excel está en inglés, traduzca los nombres de las funciones.",
            ]
        )
    )
    story.extend(
        [
            p("Dónde están los datos", "GuideH1"),
            code_box(
                "Carpeta: data/public/clasificacion/",
                "- clientes.csv",
                "- campanas.csv",
                "- base_modelable_referencia.csv",
                "- diccionario_clasificacion.csv",
            ),
            Spacer(1, 3 * mm),
            grid_table(
                ["Archivo", "Contenido", "Filas"],
                [
                    ("clientes.csv", "Perfil demográfico y financiero del cliente", "7.980"),
                    ("campanas.csv", "Contexto de campaña y respuesta acepta_deposito", "7.960"),
                    ("Cruce interno esperado", "Registros con id_cliente en ambas tablas", "7.940"),
                ],
                [42 * mm, 104 * mm, 28 * mm],
            ),
            Spacer(1, 3 * mm),
            callout(
                "Auditoría",
                "El ejercicio contiene deliberadamente 40 clientes sin campaña y 20 campañas sin perfil. La diferencia de filas es parte del análisis, no un error accidental.",
            ),
            p("Ruta rápida", "GuideH2"),
            p(
                "Si el objetivo de la clase es concentrarse en el clasificador, importe directamente <b>base_modelable_referencia.csv</b>. Si el objetivo incluye preparación, realice primero el cruce descrito en la página siguiente."
            ),
            PageBreak(),
            p("1. Preparar la base con Power Query", "GuideH1"),
        ]
    )
    add_step(story, 1, "Importar clientes", "Abra un libro nuevo. Vaya a <b>Datos - Obtener datos - Desde texto/CSV</b>, seleccione <b>clientes.csv</b> y elija <b>Transformar datos</b>.")
    add_step(story, 2, "Importar campañas", "Repita el proceso con <b>campanas.csv</b>. Confirme que ambas consultas reconocen <b>id_cliente</b> como texto.")
    add_step(story, 3, "Combinar", "Seleccione la consulta <b>campanas</b> y use <b>Inicio - Combinar consultas</b>. Relacione ambas tablas mediante <b>id_cliente</b>.")
    story.extend(
        [
            p("Compare antes de elegir", "GuideH2"),
            grid_table(
                ["Tipo de cruce", "Qué conserva", "Pregunta de negocio"],
                [
                    ("Interno", "Solo las 7.940 llaves presentes en ambas tablas", "¿Aceptamos excluir registros sin pareja?"),
                    ("Izquierdo desde campañas", "Las 7.960 campañas", "¿Cómo trataremos los 20 perfiles ausentes?"),
                ],
                [38 * mm, 66 * mm, 70 * mm],
            ),
        ]
    )
    add_step(story, 4, "Expandir y cargar", "Expanda las columnas de clientes, evite duplicar <b>id_cliente</b> y cargue el resultado como tabla de Excel. En <b>Diseño de tabla</b>, asigne el nombre <b>Base</b>.")
    story.extend(
        [
            p("Control antes de modelar", "GuideH2"),
        ]
    )
    story.extend(
        bullets(
            [
                "Una fila representa un contacto asociado a un cliente.",
                "La respuesta es <b>acepta_deposito</b>.",
                "La predicción se realiza antes de contactar al cliente.",
                "El identificador <b>id_cliente</b> no se usa como predictor.",
                "Un blanco no significa lo mismo que la categoría <b>unknown</b> o <b>nonexistent</b>.",
            ]
        )
    )
    story.extend(
        [
            callout(
                "No usar",
                "No incluya la duración de la llamada para decidir a quién contactar: solo se conoce después de la llamada y produciría fuga de datos.",
            ),
            PageBreak(),
            p("2. Diseñar el primer clasificador", "GuideH1"),
            p(
                "Para que el mecanismo sea visible en Excel, el primer modelo utiliza cinco predictores. No busca maximizar desempeño: busca mostrar cómo una probabilidad se convierte en una decisión."
            ),
            grid_table(
                ["Predictor", "Tipo", "Preparación"],
                [
                    ("edad", "Numérico", "Usar el valor observado"),
                    ("contactos_campana", "Numérico", "Usar el valor observado"),
                    ("contactos_previos", "Numérico", "Usar el valor observado"),
                    ("tipo_contacto", "Categórico", "Crear indicador de cellular"),
                    ("resultado_previo", "Categórico", "Crear indicador de success"),
                ],
                [52 * mm, 38 * mm, 84 * mm],
            ),
            p("Crear la respuesta numérica", "GuideH2"),
            code_box('y = --([@acepta_deposito]="Sí")'),
            p("Crear variables indicadoras", "GuideH2"),
            code_box(
                'x_celular = --([@tipo_contacto]="cellular")',
                'x_exito_previo = --([@resultado_previo]="success")',
            ),
            p("Separar entrenamiento y prueba", "GuideH2"),
            p("Agregue una columna <b>particion</b>. La fórmula genera una división estable cercana a 75 % / 25 %:"),
            code_box(
                '=SI(RESIDUO(VALOR(DERECHA([@id_cliente];6));4)=0;',
                '   "Prueba";"Entrenamiento")',
            ),
            callout(
                "Regla",
                "Solver solo debe aprender con Entrenamiento. La matriz de confusión y las métricas deben calcularse únicamente con Prueba.",
            ),
            p("Crear los parámetros", "GuideH2"),
            p("En una hoja denominada <b>Parametros</b>, escriba estos valores iniciales:"),
            grid_table(
                ["Celda", "Parámetro", "Valor inicial"],
                [
                    ("B2", "Intercepto", "0"),
                    ("B3", "Edad", "0"),
                    ("B4", "Contactos de campaña", "0"),
                    ("B5", "Contactos previos", "0"),
                    ("B6", "Contacto celular", "0"),
                    ("B7", "Éxito previo", "0"),
                ],
                [30 * mm, 106 * mm, 38 * mm],
            ),
            PageBreak(),
            p("3. Construir la probabilidad logística", "GuideH1"),
            p("En la tabla <b>Base</b>, cree la columna <b>z</b>. Esta es la combinación lineal de variables y coeficientes:"),
            code_box(
                '=Parametros!$B$2',
                ' +Parametros!$B$3*[@edad]',
                ' +Parametros!$B$4*[@contactos_campana]',
                ' +Parametros!$B$5*[@contactos_previos]',
                ' +Parametros!$B$6*[@x_celular]',
                ' +Parametros!$B$7*[@x_exito_previo]',
            ),
            p("Cree después la columna <b>p</b>:", "GuideH2"),
            code_box('=MAX(1E-8;MIN(1-1E-8;1/(1+EXP(-[@z]))))'),
            p(
                "La función logística transforma cualquier valor de <b>z</b> en una probabilidad entre 0 y 1. Los límites 1E-8 y 1-1E-8 evitan calcular LN(0)."
            ),
            p("Construir la pérdida de entrenamiento", "GuideH2"),
            p("Agregue la columna <b>loglik_entrenamiento</b>:"),
            code_box(
                '=SI([@particion]="Entrenamiento";',
                '   [@y]*LN([@p])+(1-[@y])*LN(1-[@p]);',
                '   0)',
            ),
            p("En <b>Parametros!B10</b>, escriba la pérdida total que Solver debe minimizar:"),
            code_box('=-SUMA(Base[loglik_entrenamiento])'),
            callout(
                "Importante",
                "La herramienta Análisis de datos - Regresión ajusta una regresión lineal. Para este ejercicio no reemplaza la regresión logística.",
            ),
            p("Activar Solver", "GuideH2"),
            p("Si Solver no aparece, use <b>Archivo - Opciones - Complementos - Administrar complementos de Excel - Ir</b> y active <b>Solver</b>."),
            PageBreak(),
            p("4. Ajustar el modelo con Solver", "GuideH1"),
            p("Abra <b>Datos - Solver</b> y configure:"),
            grid_table(
                ["Campo", "Configuración"],
                [
                    ("Definir objetivo", "Parametros!B10"),
                    ("Optimizar", "Mínimo"),
                    ("Cambiando las celdas", "Parametros!B2:B7"),
                    ("Método", "GRG No lineal"),
                ],
                [58 * mm, 116 * mm],
            ),
            Spacer(1, 3 * mm),
            callout(
                "Crítico",
                "En Opciones, desmarque Convertir variables sin restricciones en no negativas. Los coeficientes logísticos pueden ser positivos o negativos.",
            ),
            Spacer(1, 3 * mm),
            p("Presione <b>Resolver</b> y conserve la solución. Si Solver no converge:", "GuideH2"),
        ]
    )
    story.extend(
        bullets(
            [
                "revise que edad y los conteos sean numéricos;",
                "confirme que las probabilidades no contengan errores;",
                "verifique que la pérdida solo incluya Entrenamiento;",
                "reinicie B2:B7 en cero y vuelva a ejecutar;",
                "como medida de estabilidad, puede restringir los coeficientes entre -20 y 20.",
            ]
        )
    )
    story.extend(
        [
            p("Convertir probabilidades en clases", "GuideH2"),
            p("Agregue la columna <b>predice</b> con un punto de corte inicial de 0,5:"),
            code_box('=SI([@p]>=0,5;1;0)'),
            grid_table(
                ["Probabilidad", "Decisión inicial"],
                [
                    ("p >= 0,5", "Predice aceptación: 1"),
                    ("p < 0,5", "Predice no aceptación: 0"),
                ],
                [66 * mm, 108 * mm],
            ),
            Spacer(1, 3 * mm),
            p(
                "El punto de corte no pertenece al algoritmo como una verdad universal. Es una regla de decisión que puede modificarse según el costo de falsos positivos y falsos negativos."
            ),
            PageBreak(),
            p("5. Evaluar en la muestra de prueba", "GuideH1"),
            p("Construya la matriz únicamente con filas cuya partición sea <b>Prueba</b>."),
            p("Verdaderos positivos - TP", "GuideH2"),
            code_box('=CONTAR.SI.CONJUNTO(Base[particion];"Prueba";Base[y];1;Base[predice];1)'),
            p("Falsos positivos - FP", "GuideH2"),
            code_box('=CONTAR.SI.CONJUNTO(Base[particion];"Prueba";Base[y];0;Base[predice];1)'),
            p("Falsos negativos - FN", "GuideH2"),
            code_box('=CONTAR.SI.CONJUNTO(Base[particion];"Prueba";Base[y];1;Base[predice];0)'),
            p("Verdaderos negativos - TN", "GuideH2"),
            code_box('=CONTAR.SI.CONJUNTO(Base[particion];"Prueba";Base[y];0;Base[predice];0)'),
            p("Calcular las métricas", "GuideH2"),
            grid_table(
                ["Métrica", "Fórmula", "Pregunta que responde"],
                [
                    ("Exactitud", "(TP+TN)/(TP+FP+FN+TN)", "¿Qué proporción total acertó?"),
                    ("Precisión", "TP/(TP+FP)", "De los contactados, ¿cuántos aceptarían?"),
                    ("Recall", "TP/(TP+FN)", "De quienes aceptarían, ¿cuántos detectamos?"),
                    ("Especificidad", "TN/(TN+FP)", "¿Cuántos no aceptantes evitamos contactar?"),
                    ("F1", "2*Precisión*Recall/(Precisión+Recall)", "¿Qué equilibrio existe entre precisión y recall?"),
                ],
                [31 * mm, 58 * mm, 85 * mm],
            ),
            PageBreak(),
            p("6. Interpretar antes de recomendar", "GuideH1"),
            callout(
                "Línea base",
                "Como cerca de 89 % de los casos corresponde a No, un clasificador que siempre predice No puede obtener una exactitud cercana a 89 % y un recall de aceptantes igual a 0 %.",
            ),
            p("Preguntas para el grupo", "GuideH2"),
        ]
    )
    story.extend(
        bullets(
            [
                "¿El modelo predijo alguna aceptación?",
                "¿Cuántos aceptantes reales dejó escapar?",
                "¿Cuántas llamadas improductivas generó?",
                "¿Qué cambia al bajar el punto de corte a 0,30 o 0,20?",
                "¿Cuál error es más costoso para el escenario analizado?",
            ]
        )
    )
    story.extend(
        [
            p("Dos escenarios", "GuideH2"),
            grid_table(
                ["Escenario", "Error más costoso", "Prioridad"],
                [
                    ("Crecimiento", "No contactar a alguien que habría aceptado - FN", "Recall"),
                    ("Capacidad limitada", "Contactar a alguien que no aceptará - FP", "Precisión"),
                ],
                [48 * mm, 84 * mm, 42 * mm],
            ),
            p("Formato de conclusión", "GuideH2"),
            code_box(
                '"Para [escenario], elegiría el modelo con [métrica] de [valor],',
                'porque el error más costoso es [FP o FN]. Con el corte [valor],',
                'el modelo produce [conteo] errores de ese tipo. No podemos concluir causalidad."',
            ),
            p("Lista de comprobación final", "GuideH2"),
        ]
    )
    story.extend(
        bullets(
            [
                "El cruce y las exclusiones quedaron documentados.",
                "La llave no fue utilizada como predictor.",
                "Entrenamiento y prueba están separados.",
                "Solver utilizó únicamente entrenamiento.",
                "La matriz utiliza únicamente prueba.",
                "La recomendación relaciona una métrica con el costo de un error.",
                "La conclusión declara límites y no confunde predicción con causalidad.",
            ]
        )
    )
    story.extend(
        [
            Spacer(1, 4 * mm),
            callout(
                "Idea central",
                "Solver estima los coeficientes; el punto de corte convierte probabilidades en decisiones; el costo del error define si la decisión es adecuada.",
            ),
            Spacer(1, 4 * mm),
            p(
                '<link href="https://wilmerpineda.github.io/certificacion-modelos-supervisados/sesiones/sesion-05.html" color="#006633">Material público de la sesión 5</link>',
                "GuideBody",
            ),
        ]
    )

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
