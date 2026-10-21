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
| 1 | Definición del problema y diseño | ✅ en revisión |
| 2 | MVP de chat + integración con IA generativa | ⏳ |
| 3 | RAG con citas, agente y evaluación | ⏳ |
| 4 | Despliegue y validación | ⏳ |

## Arquitectura

Frontend web mobile-first → API FastAPI → recuperación en base vectorial (manuales INIAP/MAG) → LLM (Gemini Flash)
con herramientas del agente: `diagnosticar_sintomas(sintomas)`, `calendario_labores(etapa, fecha)` y
`registrar_consulta(datos)`. Diagrama en [docs/03-arquitectura.md](docs/03-arquitectura.md).

## Estructura

```
├── backend/              API FastAPI
│   ├── app/              main.py (endpoints), config.py (variables de entorno)
│   ├── tests/            pruebas con pytest
│   └── requirements.txt
├── data/raw/             manuales oficiales (PDF fuera de Git, ver README de la carpeta)
├── docs/                 propuesta, requisitos, arquitectura, fuentes, levantamiento
│   └── evidencias/       evidencias semanales (capturas, revisiones, decisiones)
├── scripts/              utilidades (descarga y verificación de fuentes)
└── .env.example          plantilla de variables de entorno
```

## Instalación y ejecución local

Requisitos: Python 3.11+ y Git.

```bash
git clone <URL-del-repositorio>
cd Asistente_Productores_Cacao

# 1. Variables de entorno
cp .env.example .env          # en Windows: copy .env.example .env  → completar GEMINI_API_KEY

# 2. Fuentes oficiales (descarga ~70 MB y verifica SHA-256)
python scripts/descargar_fuentes.py

# 3. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verificar: http://localhost:8000/health → `{"status":"ok", ...}` · Documentación interactiva: http://localhost:8000/docs

Pruebas: `cd backend && pytest -q`

## Variables de entorno

| Variable | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `APP_NAME` | Nombre del servicio | `Asistente Agrotecnico Cacao` |
| `APP_ENV` | Entorno | `development` / `production` |
| `APP_VERSION` | Versión expuesta en `/health` | `0.1.0` |
| `ALLOWED_ORIGINS` | Orígenes CORS del frontend, separados por coma | `http://localhost:4200` |
| `GEMINI_API_KEY` | Clave del modelo. **Solo en `.env` o en el panel de la plataforma; nunca en el código** | — |
| `LLM_MODEL` | Identificador del modelo | `gemini-flash-latest` |
| `VECTORSTORE_DIR` | Carpeta de la base vectorial (semana 3) | `data/vectorstore` |

## Endpoints

| Método | Ruta | Descripción | Estado |
| :-: | :--- | :--- | :-: |
| GET | `/health` | Estado del servicio | ✅ |
| POST | `/chat` | Consulta al asistente | ⏳ semana 2 |

## URL desplegada

_Pendiente (semana 4)._

## Fuentes de conocimiento

Catálogo completo, enlaces y hashes en [data/raw/README.md](data/raw/README.md) y [docs/04-fuentes.md](docs/04-fuentes.md).

## Limitaciones

- Diagnóstico **preliminar** basado en síntomas descritos por texto; no analiza fotografías.
- Solo cubre el cultivo de cacao y lo que contienen los manuales cargados.
- Requiere conexión a internet para consultar al modelo.

## Declaración de uso de IA

_Completar: herramientas de IA usadas en el desarrollo (p. ej., asistentes de código, LLM para redacción), para qué
se usaron y cómo se verificó su salida._

## Integrantes y aporte

| Integrante | Rol | Aporte |
| :--- | :--- | :--- |
| Darío Tipanluisa | Análisis | Elaboración de propuesta del problema (01) y requisitos con historias de usuario (02). |
| Jhonn Miranda | Arquitectura | Diseño de la arquitectura (03), inventario de fuentes (04) e integración de manuales. |
| Marco Rivas | Gestión y Desarrollo | Levantamiento real de preguntas, configuración base del repositorio y evidencias. |
