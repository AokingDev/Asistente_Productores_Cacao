# Evidencias – Semana 3 (Fase 3: RAG, agente y calidad)

## Entregables

| Entregable de la guía | Dónde | Evidencia | Estado |
| :--- | :--- | :--- | :-: |
| `scripts/ingest.py` reproducible (extrae, limpia, fragmenta, embeddings, metadatos) | [scripts/ingest.py](../../../scripts/ingest.py), índice en [data/index/](../../../data/index/) | [manifest.json](../../../data/index/manifest.json): 175 fragmentos, hashes de los PDF y parámetros | ✅ |
| `docs/06-rag.md`: tamaño, solapamiento y por qué por sección | [06-rag.md](../../06-rag.md) §3 | 300 palabras, 45 de solapamiento, sin cruzar secciones | ✅ |
| Respuestas con cita obligatoria y filtros por metadatos | `app/services/citas.py`, `frontend/app.js` | capturas 01 y 02 | ✅ |
| Abstención implementada y probada | Umbral en [config/rag.toml](../../../config/rag.toml) + `system_v4` | capturas 03, 04 y 05 · [log](log-cuarentena-y-abstencion.jsonl) · `test_sin_base_en_las_fuentes_se_abstiene_sin_llamar_al_modelo` | ✅ |
| Agente con herramientas (Pydantic, deterministas, límite de iteraciones) | [app/agente/herramientas.py](../../../app/agente/herramientas.py), [app/asistente.py](../../../app/asistente.py) | capturas 06, 07 y 08 · `max_iteraciones = 3` en [config/agente.toml](../../../config/agente.toml) | ✅ |
| Parámetros en `config/` | [config/](../../../config/): `agente.toml`, `calendario.toml`, `rag.toml`, `sintomas.toml`, `fuentes.toml` | umbrales, épocas por región, tabla de síntomas y patrones de inyección | ✅ |
| Confirmación humana antes de registrar | `registrar_consulta` solo propone; `POST /consultas/{id}/confirmar` | capturas 08 → 09 (código R-0001) | ✅ |
| Conjunto de evaluación con `run_eval.py` | [eval/](../../../eval/) | 20 preguntas + 10 síntomas + 40 de calibración + inyección | ✅ |
| `docs/07-evaluacion.md` | [07-evaluacion.md](../../07-evaluacion.md) | métricas, 4 corridas, fallos diagnosticados y cambios | ✅ |
| Pruebas con `pytest` (herramientas y prompt) | [tests/](../../../tests/) | [pytest.txt](pytest.txt): **117 pruebas**, sin API | ✅ |

## Resultados de la evaluación (04/11/2026)

Resumen completo en [07-evaluacion.md](../../07-evaluacion.md). Archivos en [eval/resultados/](../../../eval/resultados/):
[ultimo_completo.md](../../../eval/resultados/ultimo_completo.md), [ultimo_inyeccion.md](../../../eval/resultados/ultimo_inyeccion.md),
[ultimo_recuperacion.md](../../../eval/resultados/ultimo_recuperacion.md), [ultimo_sintomas.md](../../../eval/resultados/ultimo_sintomas.md),
[ultimo_calibracion.md](../../../eval/resultados/ultimo_calibracion.md) y [repeticion_P15_S09.md](../../../eval/resultados/repeticion_P15_S09.md).

| Métrica | Resultado |
| :--- | :--- |
| Preguntas correctas | 19/20 (95 %); 20/20 con la repetición de P15 tras corregir el detector |
| Respuestas con cita | 17/17 (100 %) |
| Abstención o aclaración de alcance | 3/3 (100 %) |
| Síntomas con la causa esperada (indicador ≥ 80 %) | 10/10 (100 %) |
| Inyección indirecta: resistió / en cuarentena / citó el documento falso | 3/3 · 3/3 · 0/3 |
| Recuperación: hit@5 / MRR | 100 % · 0,971 |
| ⚠️ Latencia p95 (meta ≤ 5 s) | Medida de nuevo el 05/11: **6,3 s con Groq como principal** (2,6 s sin herramienta; primera palabra 1,5 s) frente a 31–51 s con Gemini. Ver [07-evaluacion.md §2.1](../../07-evaluacion.md) |

## Capturas (`capturas/`)

Tomadas el 04/11/2026 con Edge sin interfaz gráfica (Playwright), en una pantalla de **1280 × 900 px**, con el
**modelo real** (Gemini `gemini-3.5-flash-lite` y Groq `openai/gpt-oss-20b`; cada burbuja indica cuál respondió).

| Archivo | Qué demuestra | Resultado verificado |
| :--- | :--- | :--- |
| `01-respuesta-con-citas.png` | Citas [n] en cada dato y tarjetas de fuentes (documento, sección, páginas con enlace, tema). Se abrió la cita 1. | 3 fuentes citadas del Manual 76 y de la Guía INIAP; dos documentos con días distintos de fermentación, ambos citados |
| `02-filtro-por-tema.png` | Filtro por metadatos «Buscar solo en: Cosecha y poscosecha» | Todas las fuentes son del tema Cosecha y poscosecha |
| `03-abstencion-por-umbral.png` · `03b-…-pantalla-completa.png` | «¿Va a llover mañana en Quevedo?»: el **código** se abstiene **sin llamar al modelo** (coseno 0,544 < 0,63) y orienta al productor | «📭 Sin información en los manuales cargados» · «Respuesta del sistema (sin consultar al modelo)» |
| `04-abstencion-del-modelo.png` | «¿A qué precio está hoy el quintal…?» supera el umbral; se abstiene la **2.ª capa** (el prompt) | «No encontré esa información en los manuales…», sin citas |
| `05-dosis-del-almacen.png` | «En el almacén me dijeron 3 litros por bomba…» | No valida la dosis; deriva a un técnico del MAG o del INIAP |
| `06-herramienta-diagnostico.png` | `diagnosticar_sintomas` con tarjeta «Diagnóstico preliminar» | Moniliasis, «Coincide bien», dato para confirmar y fuente con página |
| `07-herramienta-calendario.png` | `calendario_labores` con tarjeta de 12 meses | Plantación joven, Costa, noviembre 2026 – octubre 2027 |
| `08-confirmacion-propuesta.png` | `registrar_consulta` **propone**: tarjeta con los datos y los botones «Sí, registrar» / «No, gracias» | «No se guarda nada sin su confirmación» |
| `09-confirmacion-registrada.png` | Tras pulsar «Sí, registrar» | «✅ Registrada con el código R-0001» |
| `10-inyeccion-cuarentena.png` | Servidor con `RAG_INDICE=data/index_inyeccion` (índice + boletín falso de «5 litros de glifosato») | «🛡️ Se descartó 1 fragmento que contenía instrucciones sospechosas…»; la respuesta usa solo los manuales del INIAP |

[log-cuarentena-y-abstencion.jsonl](log-cuarentena-y-abstencion.jsonl) contiene los eventos del log de esas capturas:
`fragmento_en_cuarentena` (`prueba-boletin_falso`) y la `busqueda` con decisión `insuficiente` (coseno 0,544).

## Problemas encontrados en la semana

Se corrigieron y se documentaron en [07-evaluacion.md §4](../../07-evaluacion.md):
- **Detector de dosis:** marcaba los rendimientos («2 760 kg de cacao seco por hectárea») como dosis, y el productor veía una alerta falsa.
- **Verificaciones de `run_eval.py`:** tenían falsos negativos («no atiendo…», «2 000» con espacio fino) y un falso positivo («citó el documento falso»).
- **Casos sin modelo:** con la cuota agotada se contaban como fallos de la herramienta.
- **Ids internos en el calendario:** el modelo citaba con ellos («[joven_corona]»). Se descubrió al tomar la captura 07.

## Cómo reproducir

```bash
pytest                                                   # 117 pruebas, sin API
python eval/run_eval.py --recuperacion --sintomas        # casi sin API
python eval/run_eval.py --completo --inyeccion           # con el modelo real (≈ 20 min con el nivel gratuito)
uvicorn app.main:app                                     # capturas 01–09 en http://localhost:8000
RAG_INDICE=data/index_inyeccion uvicorn app.main:app --port 8001   # captura 10
```
