# Registro de Decisiones de Arquitectura (ADR)

Formato: contexto → decisión → consecuencias. Estados: **Aceptada**, **Propuesta** (falta validar con datos),
**Reemplazada**. Las decisiones de la semana 1 están en
[evidencias/semana-1/decisiones.md](evidencias/semana-1/decisiones.md).

---

## Semana 2

### ADR-001 · Backend en FastAPI (Python) en lugar de Spring Boot
- **Estado:** Aceptada · reemplaza el backend Spring Boot del diagrama de la semana 1 (decisión D1 pendiente).
- **Contexto:** el caso sugiere FastAPI; el kit de integración del seminario, los SDK de los proveedores y las
  librerías de RAG (semana 3) son nativos de Python. Mantener dos lenguajes en el backend duplicaría esfuerzo.
- **Decisión:** un solo backend FastAPI + Pydantic en `app/`.
- **Consecuencias:** se descarta Spring Boot. El esqueleto `backend/` de la semana 1 se fusionó en `app/`.

### ADR-002 · Integrar el kit del seminario como capa de servicio del modelo
- **Estado:** Aceptada.
- **Contexto:** el seminario entregó `kit-integracion-ia` con un `ClienteLLM` probado (reintentos, respaldo, log).
  Su ejemplo es el caso 03 (triaje, JSON); el nuestro es conversacional.
- **Decisión:** ubicar el kit en la estructura del repositorio (`app/`, `tests/`, `eval/`, `scripts/` en la raíz,
  como espera la guía) y adaptarlo:
  - `generar_stream` ahora usa la **misma** política de reintentos, espera exponencial y respaldo que las llamadas
    normales, hasta recibir el primer trozo con texto. El kit original no reintentaba en streaming ni registraba tokens.
  - El flujo registra **tokens y tiempos** al terminar (`stream_options.include_usage`), además del tiempo hasta el
    primer trozo.
  - Si el flujo se corta a la mitad **no** se cambia de proveedor (repetiría texto): se informa al usuario.
  - El simulador del kit ahora también responde en streaming (SSE).
  - Los esquemas de otros casos se eliminaron; quedan `ChatSolicitud`, `Mensaje` y `RespuestaAsistente`.
- **Consecuencias:** se elimina la carpeta `kit-integracion-ia/`. Las pruebas del kit se adaptaron y se agregaron
  pruebas de streaming y del endpoint (35 en total).

### ADR-003 · Proveedor principal Gemini Flash con respaldo Groq, vía API compatible con OpenAI
- **Estado:** Aceptada.
- **Contexto:** nivel gratuito con límites por proyecto (Gemini) y por organización (Groq). Un 429 no debe llegar
  al productor como error.
- **Decisión:** un solo cliente (`openai`) con `base_url` distinto por proveedor. Principal `gemini-3.8-flash`,
  respaldo `openai/gpt-oss-20b`. Modelo, proveedor y límites se cambian en `.env`.
- **Consecuencias:** cambiar de proveedor no toca los endpoints. Cada integrante usa su propio proyecto de Gemini.

### ADR-004 · `POST /chat` con streaming NDJSON
- **Estado:** Aceptada.
- **Contexto:** la guía pide streaming en productos conversacionales. `EventSource` (SSE) no permite POST con cuerpo.
- **Decisión:** la respuesta es `application/x-ndjson`, una línea JSON por evento:
  `{"tipo":"texto"}`, `{"tipo":"fin"}` (con tokens y latencia) o `{"tipo":"error"}` (mensaje comprensible).
  Los fallos antes del primer trozo devuelven **503** con `detail` claro.
- **Consecuencias:** el frontend lee con `fetch` + `ReadableStream`; el error a mitad de flujo se distingue del fin normal.

### ADR-005 · Historial de la conversación en el teléfono (localStorage)
- **Estado:** Aceptada.
- **Contexto:** la propuesta exige que el productor pueda revisar sus consultas sin señal. Un historial en memoria
  del servidor se pierde al reiniciar la instancia en Render/Railway.
- **Decisión:** el navegador guarda el historial y reenvía los últimos 10 turnos; el servidor no guarda
  conversaciones. Pydantic solo acepta los roles `user`/`assistant` (el rol `system` lo pone el servidor).
- **Consecuencias:** API sin estado y fácil de escalar; menos datos personales en el servidor. `registrar_consulta`
  (semana 3) guardará solo lo necesario para la evaluación.

### ADR-006 · Interfaz en HTML/CSS/JS sin framework, servida por FastAPI
- **Estado:** Propuesta · reemplaza Angular + Ionic de la semana 1. Confirmar con el grupo.
- **Contexto:** productores con señal 3G intermitente y teléfonos de gama baja; un solo servicio simplifica el
  despliegue (semana 4) y evita CORS.
- **Decisión:** `frontend/` con tres archivos (≈ 20 KB, sin dependencias), montado en `/` por FastAPI.
- **Consecuencias:** carga rápida y despliegue único. Si más adelante se necesita una app instalable, se puede
  convertir en PWA (manifest + service worker) sin cambiar de framework.

### ADR-007 · System prompt versionado en archivos y elección de versión
- **Estado:** Propuesta · se confirma al calificar `docs/05-prompts.md` con el modelo real.
- **Contexto:** la guía pide tres versiones probadas y una comparación con 10 entradas.
- **Decisión:** `app/prompts/system_v1.md` (mínimo), `system_v2.md` (rol, tono, alcance) y `system_v3.md`
  (+ datos de finca, razonamiento paso a paso para síntomas, restricciones de dosis, abstención, defensa contra
  inyección y ejemplo tomado de la Guía INIAP, pág. 117). La ruta usa `system_v3`.
- **Consecuencias:** si la comparación muestra que otra versión inventa menos, se cambia la constante `PROMPT` en
  `app/main.py`.

### ADR-008 · Cadena de pensamiento «en silencio» con resumen visible
- **Estado:** Propuesta · validar con las entradas 1–3 de la comparación.
- **Contexto:** el caso pide probar cadena de pensamiento para razonar por síntomas, pero el productor necesita
  una respuesta corta.
- **Decisión:** el prompt ordena razonar en cuatro pasos (parte afectada → señales → causas compatibles → dato
  diferenciador) y mostrar solo un resumen fijo: *Lo que usted describe / Puede ser / Para confirmar, revise /
  Mientras tanto*. El modelo de razonamiento se controla con `LLM_RAZONAMIENTO`.
- **Consecuencias:** las alternativas quedan visibles (requisito de la Fase 4). La tabla de síntomas validada con
  los manuales llega en la semana 3 como herramienta `diagnosticar_sintomas`.

### ADR-009 · Sin productos ni dosis hasta tener RAG con citas
- **Estado:** Aceptada.
- **Contexto:** indicador del caso: el 100 % de las recomendaciones de agroquímicos debe limitarse a la fuente
  oficial, con cita. En la semana 2 el modelo aún no tiene los manuales.
- **Decisión:** el prompt prohíbe nombrar productos o dosis y validar dosis de terceros; la interfaz muestra un aviso
  fijo. La comparación marca automáticamente cualquier cantidad por bomba/litro/ha (`⚠dosis`).
- **Consecuencias:** en la semana 3 la regla se relaja **solo** para dosis presentes en los fragmentos recuperados,
  con cita.
