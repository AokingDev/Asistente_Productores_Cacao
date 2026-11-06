# Despliegue en Google Cloud Run

Decisión y datos en producción: [ADR-020](09-decisiones.md#adr-020--despliegue-en-google-cloud-run-con-contenedor-docker).
Todo se hace desde **Cloud Shell** (console.cloud.google.com → botón `>_` arriba a la derecha), que ya trae `gcloud`,
`git` y `docker`. No hace falta instalar nada en el computador.

| Qué | Valor |
|---|---|
| Servicio | `g9-cacao` · región `us-central1` |
| Imagen | [Dockerfile](../Dockerfile) (`python:3.12-slim`, usuario sin privilegios, puerto `${PORT}`) |
| Recursos | 1 GiB · 1 vCPU · `min-instances 0` · `max-instances 1` · `timeout 120 s` |
| Secretos (Secret Manager) | `gemini-key` → `GEMINI_API_KEY` · `groq-key` → `GROQ_API_KEY` |
| Variables (no secretas) | `LLM_PRINCIPAL=gemini` · `LLM_RESPALDO=groq` · `LLM_TIMEOUT_S=8` · `GEMINI_MODEL` · `GROQ_MODEL` · `APP_VERSION` |
| Salud | `GET /health` → `{"estado": "ok", …}` sin llamar al modelo |

> **Gemini principal, Groq respaldo.** Gemini además calcula los embeddings de cada pregunta (búsqueda híbrida).
> `LLM_TIMEOUT_S=8` hace que, si Gemini se cuelga o responde «high demand», la app pase a Groq en segundos y no en 30 s
> (medición del 05/11 en [07-evaluacion.md](07-evaluacion.md) §2.1). Groq gratis admite ~200 000 tokens al día.

## 0. Probar la imagen en local (opcional, con Docker Desktop)

```powershell
docker build -t g9-cacao .
docker run --rm -p 8080:8080 --env-file .env -e LLM_TIMEOUT_S=8 g9-cacao
# abrir http://localhost:8080/health y http://localhost:8080
```

## 1. Preparar el proyecto (una vez)

En la consola, arriba a la izquierda, elegir el proyecto (anotar su **ID**, no el nombre) y abrir Cloud Shell:

```bash
git clone -b NOMBRE_DE_LA_RAMA https://github.com/AokingDev/Asistente_Productores_Cacao.git
cd Asistente_Productores_Cacao
gcloud config set project ID_DE_SU_PROYECTO
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com
```

Si el repositorio es privado, `git clone` pide usuario y contraseña: la contraseña es un *token* de GitHub
(Settings › Developer settings › Personal access tokens). Si aparece una ventana «Autorizar Cloud Shell», aceptar.

**Alerta de presupuesto:** Menú ☰ › Facturación › Presupuestos y alertas › Crear presupuesto de **5 USD** con alertas al
50, 90 y 100 %. No corta el servicio, pero avisa por correo.

## 2. Guardar las claves en Secret Manager (una vez)

`read -s` no muestra la clave en pantalla ni la deja en el historial. Pegar la clave y Enter.

```bash
read -s CLAVE   # clave de Gemini + Enter
printf %s "$CLAVE" | gcloud secrets create gemini-key --data-file=-
read -s CLAVE   # clave de Groq + Enter
printf %s "$CLAVE" | gcloud secrets create groq-key --data-file=-
unset CLAVE

# Permiso para que Cloud Run (cuenta de servicio por defecto) lea los secretos
NUM=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
for s in gemini-key groq-key; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:${NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

Para rotar una clave: `printf %s "$CLAVE" | gcloud secrets versions add gemini-key --data-file=-` y volver a desplegar.

## 3. Desplegar (5 a 10 minutos)

La primera vez pregunta si crea un repositorio en Artifact Registry: responder **Y**. Cloud Build construye la imagen
con el Dockerfile.

```bash
gcloud run deploy g9-cacao --source . --region us-central1 \
  --memory 1Gi --cpu 1 --min-instances 0 --max-instances 1 \
  --timeout 120 --allow-unauthenticated \
  --set-env-vars LLM_PRINCIPAL=gemini,LLM_RESPALDO=groq,LLM_TIMEOUT_S=8,GEMINI_MODEL=gemini-3.5-flash-lite,GROQ_MODEL=openai/gpt-oss-20b,APP_VERSION=0.3.0 \
  --set-secrets GEMINI_API_KEY=gemini-key:latest,GROQ_API_KEY=groq-key:latest
```

Al terminar muestra `Service URL: https://g9-cacao-….run.app`.

Por qué estas opciones: **1 GiB** porque la app no carga modelos locales (embeddings por API); **min-instances 0** se
apaga sin tráfico (no gasta, pero hay arranque en frío); **max-instances 1** evita sorpresas en la factura y que las
propuestas de registro pendientes (en memoria) se repartan entre copias; **timeout 120** da tiempo al streaming del modelo.

## 4. Probar

```bash
URL=$(gcloud run services describe g9-cacao --region us-central1 --format 'value(status.url)')
echo $URL
curl -s "$URL/health"                   # {"estado":"ok", … "llm":{"principal":"gemini","respaldo":"groq"} …}
curl -sN "$URL/chat" -H 'Content-Type: application/json' \
  -d '{"mensaje":"¿Cómo controlo la moniliasis?"}' | tail -1
gcloud run services logs read g9-cacao --region us-central1 --limit 50   # si algo falla
```

Abrir la URL en el navegador o el celular: es la interfaz del chat.
**Antes de una demo:** abrir `URL/health` uno o dos minutos antes para despertar el servicio (arranque en frío).

## 5. Despliegue automático desde GitHub (CI/CD)

`.github/workflows/ci-cd.yml` corre **gitleaks + pytest + build de la imagen** en cada push y pull request. El job
`desplegar` corre solo en push a `main`, solo si `pruebas` pasó (`needs: pruebas`), y solo cuando el equipo lo activa:

1. Cuenta de servicio para GitHub con los roles mínimos (en Cloud Shell):

   ```bash
   PROY=$(gcloud config get-value project)
   gcloud iam service-accounts create github-deploy --display-name "GitHub Actions"
   for rol in run.admin iam.serviceAccountUser cloudbuild.builds.editor artifactregistry.writer storage.admin; do
     gcloud projects add-iam-policy-binding $PROY \
       --member="serviceAccount:github-deploy@${PROY}.iam.gserviceaccount.com" --role="roles/$rol"
   done
   gcloud iam service-accounts keys create gh-sa-key.json \
     --iam-account=github-deploy@${PROY}.iam.gserviceaccount.com
   cat gh-sa-key.json   # copiar TODO el contenido
   rm gh-sa-key.json    # borrarlo apenas se copie
   ```

2. En GitHub › Settings › Secrets and variables › Actions:
   - **Secrets** → `GCP_SA_KEY` = el contenido del JSON.
   - **Variables** → `DESPLEGAR_CLOUD_RUN` = `true`.

El workflow no pasa claves ni variables de los modelos: Cloud Run conserva entre versiones lo configurado en el paso 3.
Después de desplegar, el pipeline llama a `URL/health` como prueba de humo.

## 6. Actualizar a mano después de un cambio

```bash
cd Asistente_Productores_Cacao && git pull
gcloud run deploy g9-cacao --source . --region us-central1
```

Sin `--set-env-vars` ni `--set-secrets`, Cloud Run conserva la configuración anterior. Para cambiar de proveedor
principal sin reconstruir: `gcloud run services update g9-cacao --region us-central1 --update-env-vars LLM_PRINCIPAL=groq,LLM_RESPALDO=gemini`.

## Lo que se pierde al reiniciar

Ver la tabla «Datos en producción» del ADR-020: las consultas registradas (`data/consultas/consultas.jsonl`) y
`logs/llm.jsonl` viven en el disco temporal del contenedor. Los eventos del log también salen por la consola y quedan en
**Cloud Logging**.
