# Decisiones – Semana 1

| # | Decisión | Alternativas consideradas | Justificación | Estado |
| :-: | :--- | :--- | :--- | :-: |
| D1 | **Backend en FastAPI (Python)** | Spring Boot (indicado en `03-arquitectura.md`) | El caso sugiere FastAPI; el ecosistema RAG (embeddings, ChromaDB, SDK del LLM) es nativo en Python, y el esqueleto con `/health` ya funciona | ⚠️ Pendiente actualizar el diagrama de `03-arquitectura.md` |
| D2 | Modelo: familia **Gemini Flash** | Modelos ligeros de otros proveedores | Bajo costo y baja latencia, buen seguimiento del system prompt (ver `01-propuesta.md`) | ✅ |
| D3 | Clave del modelo **solo en el backend**, desde `.env` | Clave en el frontend | Requisito del caso y OWASP LLM Top 10; `.env` está en `.gitignore` y existe `.env.example` | ✅ |
| D4 | **PDF oficiales fuera de Git**; se versionan enlaces, SHA-256 y un script de descarga | Subir los PDF al repositorio | Suman ~70 MB; el ZIP de entrega admite máx. 20 MB | ✅ |
| D5 | Fragmentación por estructura del documento (por enfermedad, labor o clon) con metadato `tema` | Fragmentación fija por tokens | Evita mezclar síntomas de enfermedades o características de clones distintos (ver `04-fuentes.md`) | ✅ |
| D6 | Las dosis de agroquímicos solo se muestran si están en la fuente, con cita; si no, se deriva a un técnico | Que el LLM responda libremente | Indicador del caso: 100 % de recomendaciones limitadas a la fuente oficial | ✅ |
| D7 | Levantamiento por preguntas frecuentes documentales (20) + encuesta corta pendiente de aplicar | Solo entrevistas | Tiempo de la semana 1; la encuesta validará y ampliará las preguntas | ⏳ |
| D8 | Diseño mobile-first con ancho mínimo de 360 px | Escritorio primero | Usuario en campo con teléfono de gama media/baja (HU08) | ✅ |

## Hallazgos que requieren acción

- El documento catalogado como **"Manual del Cultivo de Cacao en Ecuador – MAG"** es en realidad el **Manual No. 76 del
  INIAP** (EE Central de la Amazonía). Corregir el origen en `04-fuentes.md`.
- **Falta al menos una guía oficial del MAG** sobre manejo integrado de enfermedades. Buscar en agricultura.gob.ec.
