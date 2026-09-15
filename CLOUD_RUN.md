# Despliegue en Google Cloud Run

Google Cloud Run ejecuta `app.py` dentro de un contenedor y complementa el
portal estático publicado en GitHub Pages.

## Configuración

- proyecto: `api-calculadora-502601`;
- servicio: `modelos-supervisados`;
- región: `us-central1`;
- acceso público;
- escalado mínimo en cero y máximo en tres instancias;
- 1 GiB de memoria por instancia.

URL pública:

`https://modelos-supervisados-1046402432088.us-central1.run.app`

No requiere secretos. El contenedor solo incluye la muestra pública: la carpeta
`data/private/` está excluida explícitamente.

## Despliegue

```powershell
gcloud run deploy modelos-supervisados `
  --source . `
  --project api-calculadora-502601 `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 1Gi `
  --min-instances 0 `
  --max-instances 3
```

Cloud Run construye la imagen usando `Dockerfile`, almacena la imagen en
Artifact Registry y devuelve la URL pública al finalizar. Después se debe
reemplazar el enlace local de `index.qmd` por esa URL y publicar el portal.

## Prueba local

```powershell
docker build -t modelos-supervisados .
docker run --rm -p 8080:8080 modelos-supervisados
```
