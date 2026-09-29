# Datos del curso

`public/Muestra_ICFES_5000.xlsx` contiene la muestra usada en las actividades.
La aplicación excluye `id_estudiante` de la selección de predictores y no
incluye filas originales en los reportes descargables.

La base completa está en `private/`, carpeta ignorada por Git. No debe
publicarse hasta verificar su autorización de distribución.

## Variables de la muestra

| Variable | Tipo | Uso didáctico |
|---|---|---|
| `puntaje_global` | Numérica | Respuesta principal |
| `estrato_num` | Numérica | Predictor simple o múltiple |
| `personas_hogar_num` | Numérica | Predictor múltiple |
| `internet_casa` | Categórica | Comparación de grupos e indicador |
| `jornada` | Categórica | Indicadores con categoría de referencia |
| `tipo_colegio` | Categórica | Comparación e indicadores |
| `genero` | Categórica | Comparación e indicadores |
| `departamento`, `municipio` | Categóricas | Contexto; pueden tener alta cardinalidad |

## Clasificación bancaria

`public/clasificacion/` contiene una versión pedagógica derivada de UCI Bank
Marketing. La muestra conserva el desbalance original, usa un `id_cliente`
sintético, introduce blancos controlados y separa perfiles y campañas para el
ejercicio de cruce. `duration` se excluye porque solo se conoce después de la
llamada y se reserva para estudiar fuga de datos.

Para las sesiones 7 y 8 se agregan:

- `historial_validacion_con_fuga.csv`: histórico etiquetado con
  `duracion_llamada` plantada como fuga temporal;
- `cartera_clientes.csv`: 1.000 clientes sin respuesta ni duración;
- `bosque_datos_referencia.csv`: cinco predictores trazables y partición;
- `bosque_nodos_referencia.csv`: estructura larga de siete árboles;
- `bosque_importancia_referencia.csv`: importancia Gini agregada;
- `bosque_predicciones_referencia.csv`: probabilidades por árbol y promedio.

La clave real de la cartera se genera únicamente en `private/`, carpeta
ignorada por Git y excluida del contenedor público. Los archivos de referencia
permiten continuar la actividad si no se puede entrenar en línea.
