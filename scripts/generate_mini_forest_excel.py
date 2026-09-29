"""Genera un Random Forest pequeño y auditable en un libro de Excel.

El bosque se entrena en Python (véase generate_mini_forest_reference.py), pero
las predicciones, la matriz de confusión y la importancia Gini se reconstruyen
con fórmulas de Excel. El objetivo es pedagógico: siete árboles, profundidad
máxima dos y únicamente tres hojas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "public" / "clasificacion"
OUTPUT = ROOT / "output" / "excel" / "random-forest-auditable.xlsx"

BLUE = "003B5C"
CYAN = "00A6CE"
GOLD = "F3B61F"
PALE = "EAF4F7"
WHITE = "FFFFFF"
GRAY = "5B6573"
GREEN = "D9EAD3"
RED = "F4CCCC"


def title(ws, text: str, subtitle: str, end_col: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    ws["A1"] = text
    ws["A1"].font = Font(size=18, bold=True, color=WHITE)
    ws["A1"].fill = PatternFill("solid", fgColor=BLUE)
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_col)
    ws["A2"] = subtitle
    ws["A2"].font = Font(size=10, italic=True, color=GRAY)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 30


def header(cells) -> None:
    for cell in cells:
        cell.fill = PatternFill("solid", fgColor=CYAN)
        cell.font = Font(bold=True, color=WHITE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def add_table(ws, ref: str, name: str) -> None:
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
        showRowStripes=True, showColumnStripes=False
    )
    ws.add_table(table)


def tree_formula(tree_nodes: pd.DataFrame, excel_row: int | str, node_id: int = 0) -> str:
    """Devuelve una fórmula IF anidada que referencia la hoja Bosque."""
    node = tree_nodes.loc[tree_nodes["Nodo"] == node_id].iloc[0]
    sheet_row = int(node["fila_excel"])
    if node["Es_hoja"] == "Sí":
        return f"Bosque!$M${sheet_row}"
    data_col = {
        "edad": "E",
        "contactos_campana": "F",
        "contactos_previos": "G",
        "contacto_celular": "H",
        "resultado_previo_exitoso": "I",
    }[node["Variable"]]
    left = tree_formula(tree_nodes, excel_row, int(node["Hijo_izquierdo"]))
    right = tree_formula(tree_nodes, excel_row, int(node["Hijo_derecho"]))
    return f"IF(Datos!${data_col}${excel_row}<=Bosque!$E${sheet_row},{left},{right})"


def build_workbook() -> Path:
    data = pd.read_csv(DATA_DIR / "bosque_datos_referencia.csv")
    nodes = pd.read_csv(DATA_DIR / "bosque_nodos_referencia.csv")
    predictions = pd.read_csv(DATA_DIR / "bosque_predicciones_referencia.csv")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"

    # 1. Datos -------------------------------------------------------------
    ws = wb.create_sheet("Datos")
    title(
        ws,
        "Random Forest auditable · datos",
        "La partición fue fijada en Python. La columna y convierte la respuesta en 0/1; las cinco variables alimentan los siete árboles.",
        9,
    )
    columns = [
        "id_cliente", "particion", "acepta_deposito", "y",
        "edad", "contactos_campana", "contactos_previos",
        "contacto_celular", "resultado_previo_exitoso",
    ]
    for col, value in enumerate(columns, 1):
        ws.cell(3, col, value)
    header(ws[3])
    for row_idx, record in enumerate(data.to_dict("records"), 4):
        ws.cell(row_idx, 1, record["id_cliente"])
        ws.cell(row_idx, 2, record["particion"])
        ws.cell(row_idx, 3, record["acepta_deposito"])
        ws.cell(row_idx, 4, f'=--(C{row_idx}="Sí")')
        for col_idx, feature in enumerate(columns[4:], 5):
            ws.cell(row_idx, col_idx, record[feature])
    data_end = len(data) + 3
    add_table(ws, f"A3:I{data_end}", "tblDatosBosque")
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:I{data_end}"
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 18
    for col in range(4, 10):
        ws.column_dimensions[get_column_letter(col)].width = 23
    ws.sheet_view.showGridLines = False
    ws.print_title_rows = "1:3"
    ws.print_area = "A1:I24"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # 2. Bosque ------------------------------------------------------------
    ws = wb.create_sheet("Bosque")
    title(
        ws,
        "Siete árboles en una sola tabla",
        "Cada fila es un nodo. Gini y reducción Gini son fórmulas; las probabilidades de hoja son la proporción ponderada de clase 1.",
        13,
    )
    node_columns = [
        "Árbol", "Nodo", "¿Hoja?", "Variable", "Umbral", "Hijo izq.",
        "Hijo der.", "N ponderado", "Clase 0", "Clase 1", "Gini",
        "Reducción Gini", "Prob. hoja",
    ]
    for col, value in enumerate(node_columns, 1):
        ws.cell(3, col, value)
    header(ws[3])
    nodes = nodes.copy()
    nodes["fila_excel"] = range(4, len(nodes) + 4)
    row_lookup = {(int(r.Arbol), int(r.Nodo)): int(r.fila_excel) for r in nodes.itertuples()}
    for r in nodes.itertuples(index=False):
        excel_row = int(r.fila_excel)
        values = [
            r.Arbol, r.Nodo, r.Es_hoja, r.Variable, r.Umbral,
            r.Hijo_izquierdo, r.Hijo_derecho, r.N_ponderado, r.Clase_0, r.Clase_1,
        ]
        for col, value in enumerate(values, 1):
            ws.cell(excel_row, col, None if pd.isna(value) else value)
        ws.cell(excel_row, 11, f'=IF(H{excel_row}=0,0,1-(I{excel_row}/H{excel_row})^2-(J{excel_row}/H{excel_row})^2)')
        if r.Es_hoja == "Sí":
            ws.cell(excel_row, 12, 0)
            ws.cell(excel_row, 13, f'=IF(H{excel_row}=0,0,J{excel_row}/H{excel_row})')
        else:
            left_row = row_lookup[(int(r.Arbol), int(r.Hijo_izquierdo))]
            right_row = row_lookup[(int(r.Arbol), int(r.Hijo_derecho))]
            ws.cell(
                excel_row, 12,
                f'=K{excel_row}-(H{left_row}/H{excel_row})*K{left_row}-(H{right_row}/H{excel_row})*K{right_row}'
            )
    node_end = len(nodes) + 3
    add_table(ws, f"A3:M{node_end}", "tblNodosBosque")
    ws.freeze_panes = "A4"
    widths = [9, 8, 10, 28, 12, 12, 12, 15, 12, 12, 14, 18, 14]
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    for row in ws.iter_rows(min_row=4, max_row=node_end, min_col=5, max_col=13):
        for cell in row:
            cell.number_format = "0.0000"
    ws.sheet_view.showGridLines = False
    ws.print_title_rows = "1:3"
    ws.print_area = f"A1:M{node_end}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 2
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # 3. Resultados --------------------------------------------------------
    ws = wb.create_sheet("Resultados")
    title(
        ws,
        "Predicción, decisión e importancia",
        "Cambie el punto de corte en M2. Las siete probabilidades se calculan recorriendo los nodos de Bosque; la importancia es la reducción Gini normalizada por árbol.",
        29,
    )
    # La segunda fila combina instrucciones, el parámetro editable y la tabla
    # de importancia; por eso no puede quedar fusionada hasta AC.
    ws.unmerge_cells("A2:AC2")
    ws.merge_cells("A2:L2")
    ws["N2"] = "← Punto de corte editable"
    ws["N2"].font = Font(bold=True, color=BLUE)
    ws["M2"] = 0.20
    ws["M2"].number_format = "0%"
    ws["M2"].fill = PatternFill("solid", fgColor=GOLD)
    ws["M2"].font = Font(bold=True, color=BLUE)
    result_columns = [
        "id_cliente", "partición", "y real", "fila Datos",
        "Árbol 1", "Árbol 2", "Árbol 3", "Árbol 4", "Árbol 5", "Árbol 6", "Árbol 7",
        "Prob. bosque", "Punto de corte", "Contactar", "TP", "FP", "FN", "TN", "Acierto", "Valor esperado",
    ]
    for col, value in enumerate(result_columns, 1):
        ws.cell(3, col, value)
    header(ws[3][:20])
    tree_templates = {
        tree: tree_formula(nodes.loc[nodes["Arbol"] == tree], "{row}")
        for tree in range(1, 8)
    }
    for offset in range(len(data)):
        result_row = offset + 4
        data_row = offset + 4
        ws.cell(result_row, 1, f"=Datos!A{data_row}")
        ws.cell(result_row, 2, f"=Datos!B{data_row}")
        ws.cell(result_row, 3, f"=Datos!D{data_row}")
        ws.cell(result_row, 4, data_row)
        for tree in range(1, 8):
            ws.cell(result_row, tree + 4, "=" + tree_templates[tree].replace("{row}", str(data_row)))
        ws.cell(result_row, 12, f"=AVERAGE(E{result_row}:K{result_row})")
        ws.cell(result_row, 13, "=$M$2")
        ws.cell(result_row, 14, f'=IF(L{result_row}>=M{result_row},"Sí","No")')
        ws.cell(result_row, 15, f'=--AND(C{result_row}=1,N{result_row}="Sí")')
        ws.cell(result_row, 16, f'=--AND(C{result_row}=0,N{result_row}="Sí")')
        ws.cell(result_row, 17, f'=--AND(C{result_row}=1,N{result_row}="No")')
        ws.cell(result_row, 18, f'=--AND(C{result_row}=0,N{result_row}="No")')
        ws.cell(result_row, 19, f"=--(C{result_row}=--(L{result_row}>=M{result_row}))")
        ws.cell(result_row, 20, f"=O{result_row}*60000-P{result_row}*3000")
    result_end = len(data) + 3
    add_table(ws, f"A3:T{result_end}", "tblResultadosBosque")
    ws.freeze_panes = "E4"
    for col in range(5, 14):
        for cell in ws.iter_cols(min_col=col, max_col=col, min_row=4, max_row=result_end):
            for item in cell:
                item.number_format = "0.0%"
    for cell in ws["T"][3:]:
        cell.number_format = '$#,##0;[Red]-$#,##0'

    # Tabla de importancia Gini a la derecha: una columna por árbol y promedio.
    ws["U2"] = "Variable"
    for tree in range(1, 8):
        ws.cell(2, 21 + tree, tree)
    ws["AC2"] = "Promedio"
    header(ws[2][20:29])
    features = [
        "resultado_previo_exitoso", "contactos_previos", "edad",
        "contacto_celular", "contactos_campana",
    ]
    for idx, feature in enumerate(features, 3):
        ws.cell(idx, 21, feature)
        for tree in range(1, 8):
            col = 21 + tree
            letter = get_column_letter(col)
            ws.cell(
                idx, col,
                f'=IFERROR(SUMIFS(Bosque!$L:$L,Bosque!$A:$A,{letter}$2,Bosque!$D:$D,$U{idx})/SUMIFS(Bosque!$L:$L,Bosque!$A:$A,{letter}$2),0)'
            )
            ws.cell(idx, col).number_format = "0.0%"
        ws.cell(idx, 29, f"=AVERAGE(V{idx}:AB{idx})")
        ws.cell(idx, 29).number_format = "0.0%"
    for row in ws.iter_rows(min_row=2, max_row=7, min_col=21, max_col=29):
        for cell in row:
            cell.border = Border(bottom=Side(style="thin", color="D9E1E8"))

    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = "Importancia promedio por reducción Gini"
    chart.x_axis.title = "Importancia"
    chart.height = 7
    chart.width = 14
    chart.add_data(Reference(ws, min_col=29, min_row=2, max_row=7), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=21, min_row=3, max_row=7))
    chart.legend = None
    ws.add_chart(chart, "U10")

    widths = {
        "A": 16, "B": 16, "C": 10, "D": 11, "L": 15, "M": 15,
        "N": 12, "O": 7, "P": 7, "Q": 7, "R": 7, "S": 10, "T": 16,
        "U": 28, "AC": 14,
    }
    for col in range(5, 12):
        widths[get_column_letter(col)] = 12
    for col in range(22, 29):
        widths[get_column_letter(col)] = 10
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    ws.sheet_view.showGridLines = False
    ws.auto_filter.ref = f"A3:T{result_end}"
    ws.print_title_rows = "1:3"
    ws.print_area = "A1:AC30"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    for sheet in wb.worksheets:
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.oddFooter.center.text = "&P"
        sheet.oddFooter.center.size = 9
        sheet.oddFooter.center.color = GRAY
        sheet.sheet_state = "visible"

    wb.save(OUTPUT)

    # Verificación estructural independiente de Excel.
    check = load_workbook(OUTPUT, data_only=False, read_only=False)
    assert check.sheetnames == ["Datos", "Bosque", "Resultados"]
    assert check["Bosque"].max_row == len(nodes) + 3
    assert check["Resultados"]["E4"].data_type == "f"
    assert check["Resultados"]["AC3"].data_type == "f"
    assert len(check["Resultados"]._charts) == 1
    check.close()
    return OUTPUT


if __name__ == "__main__":
    print(build_workbook())
