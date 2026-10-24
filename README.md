# Asistente Agrotécnico para Productores de Cacao

**UNIANDES – Seminario de Titulación · Ingeniería de Software con IA Generativa · Caso 09 – Grupo 9**

Asistente web, usable desde el teléfono, que responde consultas técnicas sobre el cultivo de cacao con base en
manuales oficiales del INIAP y del MAG **citando la fuente**, y un agente que orienta un **diagnóstico preliminar**
de enfermedades a partir de síntomas y genera un **calendario de labores** según la etapa del cultivo.

> ⚠️ El asistente es una guía referencial. No reemplaza la visita de un técnico agrícola y no recomienda dosis de
> agroquímicos que no estén en la fuente oficial.

## Problema

Moniliasis, escoba de bruja y mazorca negra causan pérdidas importantes a miles de pequeños productores ecuatorianos
cuando no se identifican a tiempo. Los manuales técnicos del INIAP y el MAG son de calidad, pero poco accesibles en
el campo. Detalle en [docs/01-propuesta.md](docs/01-propuesta.md).

## Estado

| Semana | Fase | Estado |
| :-: | :--- | :-: |
| 1 | Definición del problema y diseño | ✅ |
| 2 | MVP de chat + integración con IA generativa | ✅ en revisión ([evidencias](docs/evidencias/semana-2/README.md)) |
| 3 | RAG con citas, agente y evaluación | ⏳ |
| 4 | Despliegue y validación | ⏳ |

## Arquitectura

Interfaz web mobile-first (HTML/CSS/JS) → API FastAPI (`POST /chat` con streaming) → `ClienteLLM` con reintentos,
espera exponencial y respaldo → Gemini Flash (principal) / Groq (respaldo). Desde la semana 3: RAG sobre los
manuales INIAP/MAG con citas y agente con `diagnosticar_sintomas(sintomas)`, `calendario_labores(etapa, fecha)` y
`registrar_consulta(datos)`. Diagramas C4 en [docs/03-arquitectura.md](docs/03-arquitectura.md) y decisiones en
[docs/09-decisiones.md](docs/09-decisiones.md).

## Estructura

```
├── app/                     API FastAPI
│   ├── main.py              rutas: POST /chat (streaming), GET /health; sirve la interfaz
│   ├── config.py            lee .env; catálogo de proveedores (gemini | groq | simulado)
│   ├── schemas.py           entrada/salida validadas con Pydantic
│   ├── prompts/             system_v1.md · system_v2.md · system_v3.md (activo)
│   └── services/llm.py      ÚNICO módulo que habla con el modelo
├── frontend/                interfaz del chat (index.html, styles.css, app.js)
├── tests/                   pytest con un doble del modelo (no gasta API)
├── eval/                    entradas para comparar prompts y sus resultados
├── scripts/                 descarga de fuentes, comparación de prompts, simulador, demo 429
├── data/raw/                manuales oficiales (ver README de la carpeta)
├── docs/                    levantamiento (00), propuesta (01) … prompts (05), decisiones (09)
│   └── evidencias/          evidencias semanales
├── requirements.txt
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
- Fuentes oficiales: `python scripts/descargar_fuentes.py` (descarga ~70 MB y verifica SHA-256)

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

## Endpoints

| Método | Ruta | Entrada | Salida | Estado |
| :-: | :--- | :--- | :--- | :-: |
| GET | `/health` | — | `{"estado":"ok", "version", "prompt", "llm":{"principal","respaldo"}}` | ✅ |
| POST | `/chat` | `{"mensaje": str (2–1000), "historial": [{"role":"user"\|"assistant","content"}]}` | NDJSON en streaming: `{"tipo":"texto"\|"fin"\|"error"}`; 503 si el modelo no está disponible | ✅ |
| GET | `/` | — | Interfaz web del chat | ✅ |

## URL desplegada

_Pendiente (semana 4)._

## Fuentes de conocimiento

Catálogo completo, enlaces y hashes en [data/raw/README.md](data/raw/README.md) y [docs/04-fuentes.md](docs/04-fuentes.md).

## Limitaciones

- Diagnóstico **preliminar** basado en síntomas descritos por texto; no analiza fotografías.
- Solo cubre el cultivo de cacao y lo que contienen los manuales cargados.
- Requiere conexión a internet para consultar al modelo (el historial sí se puede leer sin señal).
- **Semana 2:** el chat responde con el conocimiento general del modelo, todavía **sin RAG ni citas**; por eso no
  nombra productos ni dosis. Las citas a los manuales llegan en la semana 3.

## Declaración de uso de IA

_Completar: herramientas de IA usadas en el desarrollo (p. ej., asistentes de código, LLM para redacción), para qué
se usaron y cómo se verificó su salida._

## Integrantes y aporte

| Integrante | Rol | Aporte |
| :--- | :--- | :--- |
| Darío Tipanluisa | Análisis | Elaboración de propuesta del problema (01) y requisitos con historias de usuario (02). |
| Jhonn Miranda | Arquitectura | Diseño de la arquitectura (03), inventario de fuentes (04) e integración de manuales. |
| Marco Rivas | Gestión y Desarrollo | Levantamiento real de preguntas, configuración base del repositorio y evidencias. |
