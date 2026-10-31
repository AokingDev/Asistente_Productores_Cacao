# Asistente Agrotécnico para Productores de Cacao

**UNIANDES – Seminario de Titulación · Ingeniería de Software con IA Generativa · Caso 09 – Grupo 9**

Asistente web, usable desde el teléfono, que responde consultas técnicas sobre el cultivo de cacao con base en
manuales oficiales del INIAP **citando documento y página**, y un agente que orienta un **diagnóstico preliminar**
de enfermedades a partir de síntomas, genera un **calendario de labores** según la etapa del cultivo y registra la
consulta para un técnico **solo si el productor lo confirma**.

> ⚠️ El asistente es una guía referencial. No reemplaza la visita de un técnico agrícola y solo menciona dosis de
> agroquímicos que estén en la fuente oficial, con cita (el sistema lo verifica).

## Problema

Moniliasis, escoba de bruja y mazorca negra causan pérdidas importantes a miles de pequeños productores ecuatorianos
cuando no se identifican a tiempo. Los manuales técnicos del INIAP y el MAG son de calidad, pero poco accesibles en
el campo. Detalle en [docs/01-propuesta.md](docs/01-propuesta.md).

## Estado

| Semana | Fase | Estado |
| :-: | :--- | :-: |
| 1 | Definición del problema y diseño | ✅ |
| 2 | MVP de chat + integración con IA generativa | ✅ ([evidencias](docs/evidencias/semana-2/README.md)) |
| 3 | RAG con citas, agente y evaluación | ✅ en revisión ([evidencias](docs/evidencias/semana-3/README.md)) |
| 4 | Despliegue y validación | ⏳ |

## Arquitectura

Interfaz web mobile-first (HTML/CSS/JS) → API FastAPI (`POST /chat` con streaming) → búsqueda híbrida (BM25 +
embeddings de Gemini) sobre 175 fragmentos de los manuales → abstención si no hay base → agente (≤ 3 vueltas) con
`diagnosticar_sintomas`, `calendario_labores` y `registrar_consulta` → verificación de citas y dosis → `ClienteLLM` con
reintentos, respaldo e interruptor de circuito → Gemini / Groq. Diagramas C4 en [docs/03-arquitectura.md](docs/03-arquitectura.md),
RAG en [docs/06-rag.md](docs/06-rag.md), evaluación en [docs/07-evaluacion.md](docs/07-evaluacion.md) y decisiones en
[docs/09-decisiones.md](docs/09-decisiones.md).

## Estructura

```
├── app/                     API FastAPI
│   ├── main.py              rutas: /chat, /fuentes, /consultas/{id}/confirmar|cancelar, /health; sirve la interfaz
│   ├── asistente.py         un turno: buscar → decidir (abstención) → agente → verificar citas y dosis
│   ├── rag/                 indice.py (BM25 + embeddings, filtros), embeddings.py, texto.py
│   ├── agente/              herramientas.py (Pydantic + deterministas), consultas.py (registro confirmado)
│   ├── services/            llm.py (ÚNICO que habla con el modelo), prompt.py, citas.py
│   ├── prompts/             system_v1 … v3 (semana 2) · system_v4.md (activo: RAG + herramientas)
│   ├── parametros.py        lee config/*.toml
│   ├── config.py            lee .env; catálogo de proveedores (gemini | groq | simulado)
│   └── schemas.py           entrada validada con Pydantic
├── config/                  parámetros: fuentes, rag (umbrales), agente, síntomas, calendario
├── data/index/              índice versionado: fragmentos.jsonl, embeddings.npy, manifest.json
├── data/raw/                manuales oficiales (PDF fuera de Git; ver README de la carpeta)
├── frontend/                interfaz del chat (index.html, styles.css, app.js)
├── tests/                   pytest con dobles del modelo y del índice (no gasta API)
├── eval/                    preguntas de referencia, síntomas, calibración, inyección, run_eval.py y resultados
├── scripts/                 ingest.py, descarga de fuentes, comparación de prompts, simulador, demo 429
├── docs/                    levantamiento (00) … prompts (05), RAG (06), evaluación (07), decisiones (09)
│   └── evidencias/          evidencias semanales
├── requirements.txt         servidor
├── requirements-ingest.txt  + PyMuPDF para reconstruir el índice
└── .env.example             plantilla de variables de entorno
```

## Instalación y ejecución local

Requisitos: Python 3.11+ y Git.

```bash
git clone <URL-del-repositorio>
cd Asistente_Productores_Cacao

python -m venv .venv
.venv\Scripts\activate             # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env → pegar GEMINI_API_KEY y GROQ_API_KEY
uvicorn app.main:app --reload      # abrir http://localhost:8000
```

- Chat: http://localhost:8000 · API: http://localhost:8000/docs · Estado: http://localhost:8000/health
- Pruebas (sin gastar API): `pytest`
- Sin claves: `python scripts/servidor_simulado.py` y en `.env` `LLM_PRINCIPAL=simulado`, `LLM_RESPALDO=` (vacío)
- Comparar prompts con el modelo real: `python scripts/comparar_prompts.py` → `docs/05-prompts.md`
- Evaluación: `python eval/run_eval.py --sintomas --recuperacion` (casi sin API) · `--completo --inyeccion` (con el modelo)
- Reconstruir el índice: `pip install -r requirements-ingest.txt`, `python scripts/descargar_fuentes.py` (~70 MB) y
  `python scripts/ingest.py` (≈ 2 min por el límite gratuito de embeddings). El índice ya viene en `data/index/`.

## Variables de entorno

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `LLM_PRINCIPAL` | Proveedor principal: `gemini`, `groq` o `simulado` | `gemini` |
| `LLM_RESPALDO` | Proveedor de respaldo (vacío = sin respaldo) | `groq` |
| `GEMINI_API_KEY` | Clave de Gemini. **Solo en `.env` o en el panel de la plataforma; nunca en el código** | — |
| `GEMINI_MODEL` | Modelo de Gemini | `gemini-3.8-flash` |
| `GROQ_API_KEY` | Clave de Groq (misma regla) | — |
| `GROQ_MODEL` | Modelo de Groq | `openai/gpt-oss-20b` |
| `LLM_TIMEOUT_S` | Tiempo límite por llamada (s) | `30` |
| `LLM_MAX_TOKENS` | Máximo de tokens de salida | `2048` |
| `LLM_REINTENTOS` | Intentos por proveedor ante 429 / tiempo agotado / vacío | `3` |
| `LLM_RAZONAMIENTO` | Esfuerzo de razonamiento: `low`, `medium`, `high` | `low` |
| `APP_VERSION` | Versión expuesta en `/health` | `0.2.0` |
| `LLM_LOG_DIR` | Carpeta del log por solicitud | `logs` |
| `LLM_ENFRIAMIENTO_S` | Segundos que un proveedor que falló queda al final de la fila | `120` |
| `RAG_INDICE` | Carpeta del índice (pruebas: `data/index_inyeccion`) | `data/index` |
| `CONFIG_DIR` | Carpeta de parámetros | `config` |

Los parámetros del negocio (umbrales, tabla de síntomas, calendario, mensajes) **no** son variables de entorno: viven en
`config/*.toml`. Mientras Gemini siga inestable, se recomienda `LLM_PRINCIPAL=groq` y `LLM_RESPALDO=gemini`.

> **Cuotas gratuitas.** `gemini-3.8-flash` admite solo **20 solicitudes por día** y cada pregunta al agente usa 2–3;
> `gemini-3.5-flash-lite` tiene cuota propia y también soporta herramientas. El motivo exacto de un 429 (qué límite y
> de qué modelo) queda en `logs/llm.jsonl`, campo `detalle`.
>
> **Si cambias el `.env` y el log sigue mostrando el valor anterior:** una variable que ya existe en la terminal gana
> sobre el `.env` (VS Code las inyecta al abrir la terminal). Abre una terminal nueva, o en PowerShell
> `Remove-Item Env:GEMINI_MODEL`, y vuelve a lanzar uvicorn: `--reload` no basta, porque hereda el entorno.

## Endpoints

| Método | Ruta | Entrada | Salida | Estado |
| :-: | :--- | :--- | :--- | :-: |
| GET | `/health` | — | `{"estado", "version", "prompt", "llm":{principal, respaldo}, "indice":{fragmentos, busqueda}}` | ✅ |
| GET | `/fuentes` | — | Documentos (título, URL, cita APA) y temas para el filtro | ✅ |
| POST | `/chat` | `{"mensaje": str (2–1000), "historial": [...], "tema": str?}` | NDJSON: `fuentes`, `herramienta`, `confirmacion`, `texto`, `alerta`, `aviso`, `error`, `fin` (con `citadas`, `abstencion`, `proveedor`, tokens); 503 si no hay modelo | ✅ |
| POST | `/consultas/{id}/confirmar` | — | Guarda la consulta propuesta por el agente → `{"codigo": "R-0001"}`; 404 si caducó | ✅ |
| POST | `/consultas/{id}/cancelar` | — | Descarta la propuesta | ✅ |
| GET | `/` | — | Interfaz web del chat | ✅ |

## URL desplegada

_Pendiente (semana 4)._

## Fuentes de conocimiento

Catálogo completo, enlaces y hashes en [data/raw/README.md](data/raw/README.md) y [docs/04-fuentes.md](docs/04-fuentes.md).

## Limitaciones

- Diagnóstico **preliminar** basado en síntomas descritos por texto; no analiza fotografías.
- Solo cubre el cultivo de cacao y lo que contienen los manuales cargados.
- Requiere conexión a internet para consultar al modelo (el historial sí se puede leer sin señal).
- La base de conocimiento tiene **3 documentos del INIAP**; falta una guía oficial del **MAG** (no se encontró una
  publicada). Agregarla es configurar `config/fuentes.toml` y reingestar.
- Las dosis citadas vienen de manuales de 2015–2021: el sistema pide verificar el registro vigente en Agrocalidad.
- La abstención por umbral no separa todas las preguntas de fuera de dominio (se traslapan con las válidas); el resto
  depende del prompt (ver `docs/07-evaluacion.md`).
- Las propuestas de registro viven en memoria (30 min) y las consultas confirmadas en un archivo local: en un despliegue
  con disco efímero se pierden al reiniciar.

## Declaración de uso de IA

_Completar: herramientas de IA usadas en el desarrollo (p. ej., asistentes de código, LLM para redacción), para qué
se usaron y cómo se verificó su salida._

## Integrantes y aporte

| Integrante | Rol | Aporte |
| :--- | :--- | :--- |
| Darío Tipanluisa | Análisis | Elaboración de propuesta del problema (01) y requisitos con historias de usuario (02). |
| Jhonn Miranda | Arquitectura | Diseño de la arquitectura (03), inventario de fuentes (04) e integración de manuales. |
| Marco Rivas | Gestión y Desarrollo | Levantamiento real de preguntas, configuración base del repositorio y evidencias. |
