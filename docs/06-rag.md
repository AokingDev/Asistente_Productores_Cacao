# RAG: ingesta, fragmentación, recuperación y citas

Parámetros en [config/rag.toml](../config/rag.toml) y [config/fuentes.toml](../config/fuentes.toml); código en
[scripts/ingest.py](../scripts/ingest.py) y [app/rag/](../app/rag/). Evaluación en [07-evaluacion.md](07-evaluacion.md).

## 1. Ingesta reproducible (`scripts/ingest.py`)

```bash
pip install -r requirements-ingest.txt
python scripts/descargar_fuentes.py      # descarga los 3 PDF y verifica su SHA-256
python scripts/ingest.py --revisar       # índice en data/index/ + revisión en data/processed/secciones.md
```

| Paso | Qué hace | Por qué |
|---|---|---|
| 1. Verificar | Compara el SHA-256 de cada PDF con el catalogado | Si el INIAP cambia el documento, la ingesta se detiene: hay que revisar su vigencia |
| 2. Extraer | Cada línea con su **fuente tipográfica y tamaño** (PyMuPDF) | Los títulos se distinguen por la letra, no por adivinar |
| 3. Limpiar | Quita encabezados y pies repetidos, números de página, créditos de fotos y capas duplicadas; repara palabras cortadas con guion («necro-» + «sis») y ligaduras («ﬁ») | Ruido que confunde la búsqueda |
| 4. Seccionar | Reglas por documento en `config/fuentes.toml` (ver §2) | Cada documento tiene otra maqueta |
| 5. Fragmentar | Ventanas sin cruzar secciones (§3) | Un fragmento = un tema |
| 6. Metadatos | documento, institución, año, **sección**, ruta, **páginas**, **tema**, **vigencia**, **URL** | Citas y filtros |
| 7. Embeddings | `gemini-embedding-001`, 768 dimensiones, normalizados; respeta el límite gratuito (100 textos/min) | Búsqueda semántica |
| 8. Guardar | `data/index/fragmentos.jsonl`, `embeddings.npy`, `manifest.json` (≈ 0,8 MB, versionado) | El despliegue no necesita los 70 MB de PDF |

**Reproducible:** los mismos PDF con la misma configuración producen los mismos fragmentos, con el mismo orden y los mismos ids
(`guia_iniap-0042`). El `manifest.json` guarda los hashes de los PDF, los parámetros de fragmentación y el modelo de
embeddings usado.

## 2. Estructura de cada documento

| Documento | Problema de la maqueta | Regla aplicada |
|---|---|---|
| **Guía INIAP** (162 pp.) | Cada módulo alterna páginas para el *facilitador* (OBJETIVO, MATERIALES, PROCEDIMIENTO: «forme grupos…») con **Notas Técnicas** (el contenido técnico). Hay una página fuera de orden (la 96 es del Módulo 2). En el flujo interno, algunos títulos van después de su texto. | Se indexan las **Notas Técnicas** y las introducciones de módulo; las páginas del facilitador se excluyen (`incluir_practicas_facilitador = false`). El módulo sale del pie «MÓDULO N» de cada página. Los bloques se ordenan por posición. Títulos: Bebas 15–16,5 pt (sección) y Helvetica-Bold en mayúsculas (tema). |
| **Manual 76** (25 hojas) | Dos páginas impresas por hoja y dos columnas por página: ordenar por posición mezcla columnas. | Se usa el **orden del flujo interno**, que sí es el de lectura. El capítulo se toma del **«Contenido temático» impreso** (página impresa = 2 × hoja − 4, +1 en la mitad derecha). Secciones: Cronos 16 pt en negrita. |
| **Catálogo de cultivares** (66 pp.) | Cada clon ocupa una ficha de 2 páginas más una página de imagen. | **Un clon = dos fragmentos**: «características, rendimiento y resistencia» y «zonas de adaptación» (la lista de cantones diluía la búsqueda de rendimiento). Se excluyen glosario, bibliografía y anexos. |

La revisión manual de `data/processed/secciones.md` encontró y corrigió, entre otros: columnas mezcladas en el Manual 76,
capítulos asignados por el título de la página anterior y títulos partidos en dos líneas («Cuando el secado / es en marquesina»).

## 3. Fragmentación: tamaño, solapamiento y por qué por sección

| Parámetro | Valor | Justificación |
|---|---|---|
| Unidad | **Sección del documento** (enfermedad, plaga, labor, clon) | La pregunta típica es sobre una sola cosa («¿cómo controlo la monilla?»). Si un fragmento mezcla la monilla con la escoba de bruja, el modelo puede cruzar síntomas o controles entre enfermedades. Por eso un fragmento **nunca cruza** de una sección a otra. |
| Tamaño máximo | **300 palabras** (≈ 400 tokens) | La sección más larga de enfermedades (Moniliasis, 298 palabras en la guía) cabe entera, con síntomas y control juntos. Con 5 fragmentos, el contexto queda en ≈ 2.000 tokens: cabe en el límite de 8.000 tokens/min de Groq aun con dos vueltas del agente. |
| Solapamiento | **45 palabras (≈ 15 %)** | Solo se usa cuando una sección larga se parte en varias ventanas (p. ej., Escoba de bruja: síntomas en una y «Tipos de control» en otra). El solape conserva la oración del corte, y el corte se hace al final de una oración cuando la hay. |
| Mínimo | **40 palabras** | Una sección más corta se une a la anterior del mismo capítulo («Introducción» de 24 palabras + «Gallina ciega»). Los restos de menos de 15 palabras («Fermentación» suelto) se descartan. |
| Cabecera para el embedding | `Documento — Módulo > Sección` + texto | El vector «sabe» de qué trata el fragmento aunque el texto no repita el nombre (p. ej., la segunda ventana de Escoba de bruja). |

Resultado: **175 fragmentos** (guía 86, manual 49, catálogo 40), de 17 a 300 palabras, con un promedio de 149.
Por tema: variedades 42, vivero y siembra 35, poscosecha 29, fertilización 25, poda 25, enfermedades 11, plagas 7, general 1.

> En la semana 1 (`04-fuentes.md`) se había previsto 500 tokens para enfermedades y 800 para labores. Al medir las
> secciones reales, **133 de 151 secciones caben en un solo fragmento de 300 palabras**; solo 18 se parten (como máximo en
> 3 ventanas), entre ellas Escoba de bruja y Mal del machete. Con 800 tokens, la mayoría de los fragmentos habría juntado
> dos secciones, justo lo que se quiere evitar.

## 4. Recuperación híbrida

1. **BM25** sobre raíces en español (Snowball), sin tildes ni palabras vacías. Los códigos de clon se normalizan («EET 103» = «EET-103»).
2. **Embeddings**: coseno entre la consulta y los 175 vectores.
3. **Fusión RRF** (k = 60) de las dos listas; como máximo 2 ventanas de la misma sección; se entregan **5 fragmentos**.
4. **Expansión de la consulta**: si el productor nombra un problema de la tabla validada («monilla»), se agrega su nombre técnico
   («Moniliasis»). Así «3 litros por bomba» no arrastra la búsqueda hacia biol y compost (fallo P11 en `07-evaluacion.md`).
5. **Seguimientos**: un mensaje corto («¿y el CCN-51?») se busca junto con la pregunta anterior.
6. Si la API de embeddings falla, la búsqueda sigue **solo con BM25** y la abstención usa la cobertura de términos.

**Filtros por metadatos:** `tema` (desde la interfaz: «Buscar solo en Plagas») y `documento`. Los temas se asignan en la
ingesta por palabras clave en el título (peso 3) y el texto (peso 1), configurables en `config/rag.toml`.

## 5. Abstención en dos capas

| Capa | Quién decide | Regla |
|---|---|---|
| 1. Umbral | **Código**, sin llamar al modelo | Si el coseno máximo es < **0,63** → «No encontré esa información en los manuales…» y orientación (consultar a un técnico). Antes de abstenerse revisa si el mensaje es para una herramienta: síntomas que reconoce la tabla, pedido de calendario o de registro. |
| 2. Prompt | Modelo | `system_v4`: usar solo los fragmentos; si no responden la pregunta, decirlo y no completar con conocimiento propio. |

Por qué dos capas: la calibración con 40 mensajes (`eval/calibracion_umbral.csv`) muestra que las preguntas válidas y las de
fuera de dominio **se traslapan** (por ejemplo, «¿cuánto gana un jornalero en la cosecha de cacao?» tiene un coseno de 0,731).
Ningún umbral las separa sin bloquear preguntas legítimas: 0,63 bloquea la mitad de las de fuera de dominio y ninguna válida,
y el resto lo filtra el prompt.

## 6. Citas obligatorias y verificación

- Cada fragmento llega numerado: `<fragmento n="2" documento="…" seccion="…" paginas="…">`. El prompt exige `[n]` después de
  cada dato.
- El código extrae las citas, descarta las que no existen y envía al navegador las **fuentes citadas** (documento, sección,
  página con enlace `url#page=N`, tema). Las que se consultaron sin citarse aparecen aparte, plegadas.
- **Dosis:** toda cantidad de producto en la respuesta (cc, ml, l, g, kg, partes, %, libras) debe aparecer en un fragmento de un
  **documento oficial** del catálogo. Si no aparece, la interfaz muestra una alerta («no la use»). Si aparece, muestra el
  aviso de verificar el registro en Agrocalidad. No cuentan como dosis los rendimientos («2.000 kg/ha») ni las cantidades que
  escribió el propio productor.

## 7. Seguridad frente a documentos (inyección indirecta)

- El texto de los fragmentos se **neutraliza**: no puede abrir ni cerrar etiquetas, y se quitan los caracteres de control.
  El prompt indica que es material de consulta, no instrucciones.
- **Cuarentena:** los fragmentos con frases dirigidas al asistente («ignora tus reglas», «instrucción para el asistente»…,
  patrones en `config/rag.toml`) se descartan antes de llegar al modelo y quedan registrados en el log.
- Un documento ajeno al catálogo no puede respaldar una dosis.

Pruebas: `tests/test_prompt.py`, `tests/test_agente.py` (cuarentena) y `python eval/run_eval.py --inyeccion`.
