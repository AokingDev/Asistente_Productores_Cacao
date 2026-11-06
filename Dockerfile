# Asistente Agrotécnico para Productores de Cacao · imagen para Azure Container Apps (semana 4, misión 1)
#
# Construir y probar en local:
#   docker build -t g9-cacao .
#   docker run --rm -p 8080:8080 --env-file .env g9-cacao      → http://localhost:8080/health
#
# Las claves (GEMINI_API_KEY, GROQ_API_KEY) NUNCA entran a la imagen: la plataforma las entrega
# al contenedor como variables o secretos (ver docs/despliegue.md).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1. Dependencias (esta capa se reutiliza mientras requirements.txt no cambie).
#    Embeddings por API (Gemini): no hay torch ni modelos locales que descargar.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Código y datos de SOLO LECTURA. El índice del RAG (data/index) ya viene construido en el repo:
#    ingest.py necesita la clave de Gemini para los embeddings, así que no se ejecuta en el build.
#    Lo que no entra (PDF, .env, pruebas, evaluación…) está en .dockerignore.
COPY app ./app
COPY config ./config
COPY frontend ./frontend
COPY data/index ./data/index

# 3. Usuario sin privilegios. Es dueño de /app solo para poder escribir logs/ y data/consultas/,
#    que son EFÍMEROS: se pierden en cada reinicio (decisión en docs/09-decisiones.md, ADR-020).
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

# 4. Arranque: Azure Container Apps (y otras plataformas) indican el puerto en la variable PORT.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
