# Publicación

El proyecto usa un solo repositorio y dos servicios públicos:

1. **GitHub Pages** publica el portal Quarto.
2. **Google Cloud Run** ejecuta `app.py`.

## Repositorio

Nombre sugerido: `certificacion-modelos-supervisados`.

Antes de publicar, confirme que `data/private/` no aparece en `git status` y
que la muestra de 5.000 registros está autorizada para distribución.

## Aplicación Streamlit

La aplicación está desplegada en:

- servicio: `modelos-supervisados`;
- proyecto: `api-calculadora-502601`;
- región: `us-central1`;
- URL: `https://modelos-supervisados-brt75qqksa-uc.a.run.app`.

No requiere secretos. La configuración reproducible y los comandos están en
`CLOUD_RUN.md`.

## Portal Quarto

El flujo `.github/workflows/publish.yml` renderiza el sitio y lo publica en la
rama `gh-pages` con cada cambio en `main`. En GitHub, Pages debe configurarse
para desplegar desde esa rama.
