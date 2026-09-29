# Certificación en Ciencia de Datos · Modelos Supervisados

Paquete reproducible para las sesiones 3 a 8 del módulo: p-value, regresión
lineal, preparación de datos, clasificación, validación y decisiones operativas.

## Componentes

- `app.py`: laboratorio interactivo en Streamlit.
- `index.qmd`: portal Quarto para estudiantes y docentes.
- `slides/`: presentaciones RevealJS.
- `sesiones/`: guías públicas de cada sesión.
- `guias/`: planeación y respuestas esperadas para el docente.
- `fichas/`: hoja de trabajo del estudiante.
- `data/public/`: muestra ICFES autorizada para clase.
- `data/public/clasificacion/`: caso bancario pedagógico, diccionario y base de referencia.
- `pages/2_Clasificacion.py`: laboratorio de preparación y comparación de clasificadores.
- `data/public/clasificacion/historial_validacion_con_fuga.csv`: caso para auditar fuga temporal.
- `data/public/clasificacion/cartera_clientes.csv`: cartera sin etiqueta para la decisión final.
- `proyecto/proyecto-final.qmd`: instrucciones y rúbrica del proyecto final.
- `output/excel/random-forest-auditable.xlsx`: bosque de siete árboles reconstruido con fórmulas en tres hojas.
- `tests/`: verificación de cálculos estadísticos.

## Ejecutar la aplicación

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## Construir el portal

```powershell
quarto render
```

La guía reservada para el docente se renderiza por separado cuando se necesite:

```powershell
quarto render guias/guia-docente.qmd --output-dir material-docente
```

La aplicación procesa los archivos en memoria. No se deben cargar datos
personales, confidenciales ni sin anonimizar.
