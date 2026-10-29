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

### ADR-010 · Recordatorio del técnico en un avatar, no en cada respuesta
- **Estado:** Aceptada.
- **Contexto:** `system_v3` cierra cada respuesta con «Es una orientación preliminar; confírmelo con un técnico…».
  Repetido en todas las respuestas, el productor deja de leerlo y ocupa espacio en una pantalla pequeña.
- **Decisión:** un avatar de cacao (abajo a la derecha) con una nube muestra **siempre** el recordatorio (HU06).
  El frontend quita esa frase cuando es la **última línea suelta** de la respuesta (no se tocan viñetas con contenido).
  La nube se vuelve a abrir, con una animación, después de cada respuesta. El prompt **no** se modificó, para no
  invalidar la comparación de `docs/05-prompts.md`.
- **Consecuencias:** el aviso ya no depende de que el modelo lo escriba (lo pone el código). Si se quiere ahorrar
  tokens, una futura `system_v4` puede omitir la frase de cierre.

### ADR-011 · Mostrar qué proveedor generó cada respuesta y permitir detenerla
- **Estado:** Aceptada.
- **Contexto:** con respaldo automático, el usuario y el evaluador deben saber si respondió Gemini o Groq. Las
  respuestas largas en señal lenta deben poder cortarse.
- **Decisión:** el evento `fin` incluye `proveedor` y `modelo`; la interfaz muestra «Generado por Gemini/Groq» bajo cada
  respuesta y lo guarda en el historial local (al servidor solo se reenvían `role` y `content`). Durante la respuesta,
  «Enviar» sigue deshabilitado (requisito de la guía) y aparece un botón aparte **«Detener respuesta»**. Al detener, el
  backend cierra la conexión con el proveedor (`Flujo.cancelar`) y registra `stream_cancelado`.
- **Consecuencias:** una respuesta detenida no se guarda en el historial (no se reenvía a medias al modelo).

### ADR-012 · Escritorio a todo el ancho con panel informativo
- **Estado:** Aceptada.
- **Decisión:** desde 960 px: panel lateral fijo (qué hace, qué no hace, cómo describir un síntoma, fuentes y estado
  del servicio desde `/health`) + chat a todo el ancho restante. En el teléfono el panel es un cajón (botón «Info»).
  Las burbujas se limitan a ~1100 px para que las líneas sigan siendo legibles en monitores anchos.

---

## Semana 3

### ADR-013 · Fragmentación por sección con reglas tipográficas por documento
- **Estado:** Aceptada. Detalle en [06-rag.md](06-rag.md).
- **Contexto:** los tres PDF no tienen marcadores y cada uno tiene otra maqueta (páginas del facilitador, dos páginas
  por hoja, fichas de clones).
- **Decisión:** las secciones se detectan por fuente y tamaño de letra, con reglas en `config/fuentes.toml`; un fragmento
  nunca cruza de una sección a otra; tiene como máximo 300 palabras y un solape de 45; cada clon se divide en «características» y
  «zonas»; las páginas del facilitador quedan fuera.
- **Consecuencias:** 175 fragmentos coherentes. Agregar un documento requiere escribir sus reglas, no tocar el código.

### ADR-014 · Búsqueda híbrida (BM25 + embeddings de Gemini) con índice versionado
- **Estado:** Aceptada.
- **Contexto:** un modelo de embeddings local multilingüe ocupa unos 470 MB en memoria (el plan gratuito de Render tiene
  512 MB). La API de Gemini es liviana pero inestable (503 y tiempos agotados en las semanas 2 y 3).
- **Decisión:** embeddings `gemini-embedding-001` (768 dimensiones) más BM25 propio en español, fusionados con RRF. Si la API
  de embeddings falla, la búsqueda sigue solo con BM25. El índice (≈ 0,8 MB) se versiona en `data/index/`; no se usa
  ChromaDB ni Pinecone.
- **Consecuencias:** sin servicios extra en el despliegue. Se gasta una llamada de embeddings por pregunta (en caché).
  PyMuPDF (licencia AGPL) queda solo en `requirements-ingest.txt`.

### ADR-015 · Abstención en dos capas con umbral calibrado
- **Estado:** Aceptada. Datos en [07-evaluacion.md](07-evaluacion.md).
- **Decisión:** el código se abstiene sin llamar al modelo si el coseno máximo es < 0,63, salvo que el mensaje sea para una
  herramienta (síntomas reconocidos, calendario, registro). El prompt cubre el resto.
- **Consecuencias:** un mensaje sin base no gasta tokens y la respuesta es predecible. Los mensajes de fuera de dominio que
  superan el umbral dependen del modelo (3/3 correctos en la evaluación).

### ADR-016 · Agente con bucle limitado y herramientas deterministas
- **Estado:** Aceptada.
- **Decisión:** bucle modelo → herramienta → modelo de **3 vueltas como máximo** (`config/agente.toml`); en la última vuelta
  se llama al modelo sin herramientas para obligarlo a responder. Las herramientas validan con Pydantic (`extra="forbid"`) y
  calculan con tablas de `config/`, citadas por página: `sintomas.toml` y `calendario.toml`. Un argumento inválido se le
  devuelve al modelo como error, sin ejecutar nada. Todas las vueltas prefieren el mismo proveedor, y la `thought_signature`
  de Gemini solo se le devuelve a Gemini.
- **Consecuencias:** 10/10 síntomas de referencia con la causa esperada en primer lugar; el agente es auditable y se prueba
  sin API (`tests/test_agente.py`, `tests/test_herramientas.py`).

### ADR-017 · Confirmación humana para registrar
- **Estado:** Aceptada.
- **Decisión:** `registrar_consulta` **no guarda**: crea una propuesta pendiente (30 minutos) y la interfaz muestra una
  tarjeta con los datos y los botones «Sí, registrar» y «No, gracias». Solo `POST /consultas/{id}/confirmar` escribe en
  `data/consultas/consultas.jsonl`, con un código R-0001 y sin datos de contacto.
- **Consecuencias:** el modelo nunca registra ni deriva por su cuenta. Las propuestas viven en memoria y se pierden si el
  servidor se reinicia (el productor vuelve a pedirlo).

### ADR-018 · Las dosis se verifican contra las fuentes oficiales; cuarentena de fragmentos sospechosos
- **Estado:** Aceptada tras la 1.ª prueba de inyección.
- **Contexto:** con un documento envenenado en el primer lugar, el modelo recomendó «5 litros de glifosato» en 1 de 3 casos, y
  el verificador no alertó porque el propio documento envenenado «respaldaba» la dosis.
- **Decisión:** (1) las dosis solo cuentan como respaldadas si están en documentos de `config/fuentes.toml`; (2) los
  fragmentos con frases dirigidas al asistente se descartan antes del prompt (patrones en `config/rag.toml`).
- **Consecuencias:** defensa en profundidad; no depende de que el modelo resista. Riesgo residual: una inyección redactada
  sin esas frases. La cuarentena por patrones no reemplaza el control de qué documentos entran al índice.

### ADR-019 · Un tiempo agotado pasa al respaldo; interruptor de circuito
- **Estado:** Aceptada.
- **Contexto:** con Gemini caído, la primera respuesta tardó 97 s (3 × 30 s de espera antes de usar Groq).
- **Decisión:** un `APITimeoutError` ya no se reintenta con el mismo proveedor si hay respaldo; un proveedor que falla queda
  al final de la fila durante `LLM_ENFRIAMIENTO_S` (120 s).
- **Consecuencias:** con Gemini caído la respuesta llega en unos 2 s desde Groq. Recomendación al equipo: mientras Gemini siga
  inestable, usar `LLM_PRINCIPAL=groq` en el `.env`.
