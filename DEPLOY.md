# Publicación

El proyecto usa un solo repositorio y dos servicios públicos:

1. **GitHub Pages** publica el portal Quarto.
2. **Streamlit Community Cloud** ejecuta `app.py`.

## Repositorio

Nombre sugerido: `certificacion-modelos-supervisados`.

Antes de publicar, confirme que `data/private/` no aparece en `git status` y
que la muestra de 5.000 registros está autorizada para distribución.

## Aplicación Streamlit

En Community Cloud seleccione:

- repositorio: `certificacion-modelos-supervisados`;
- rama: `main`;
- archivo de entrada: `app.py`;
- Python: `3.12`.

No requiere secretos. Una vez asignada la URL, reemplace el enlace local de
`index.qmd` por la URL `https://…streamlit.app` y vuelva a publicar el portal.

## Portal Quarto

El flujo `.github/workflows/publish.yml` renderiza el sitio y lo publica en la
rama `gh-pages` con cada cambio en `main`. En GitHub, Pages debe configurarse
para desplegar desde esa rama.
