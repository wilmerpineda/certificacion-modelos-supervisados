# Certificación en Ciencia de Datos · Modelos Supervisados

Paquete reproducible para las sesiones 3 y 4 del módulo: p-value, prueba t,
regresión lineal simple, regresión múltiple, variables categóricas y
multicolinealidad.

## Componentes

- `app.py`: laboratorio interactivo en Streamlit.
- `index.qmd`: portal Quarto para estudiantes y docentes.
- `slides/`: presentaciones RevealJS.
- `sesiones/`: guías públicas de cada sesión.
- `guias/`: planeación y respuestas esperadas para el docente.
- `fichas/`: hoja de trabajo del estudiante.
- `data/public/`: muestra ICFES autorizada para clase.
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
