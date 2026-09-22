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

Los archivos de referencia con métricas y predicciones permiten continuar la
actividad si no se puede entrenar en línea. El diccionario registra las
modificaciones y la correspondencia con las variables UCI.
