# Evidencias – Semana 2 (Fase 2: MVP e integración con IA generativa)

## Entregables

| Entregable de la guía | Dónde | Evidencia | Estado |
| :--- | :--- | :--- | :-: |
| Endpoint principal en FastAPI con Pydantic, streaming | `POST /chat` en [app/main.py](../../../app/main.py), esquemas en [app/schemas.py](../../../app/schemas.py) | capturas 02, 03 y 06 | ✅ |
| Cliente del modelo encapsulado | [app/services/llm.py](../../../app/services/llm.py) | [09-decisiones.md](../../09-decisiones.md) ADR-002/003 | ✅ |
| `system_v1.md` + 3 versiones probadas | [app/prompts/](../../../app/prompts/) | — | ✅ escritas · ⏳ probar con el modelo real |
| `docs/05-prompts.md` (3 versiones × 10 entradas) | [05-prompts.md](../../05-prompts.md), entradas en [eval/entradas_prompts.csv](../../../eval/entradas_prompts.csv) | — | ⏳ ejecutar y calificar |
| Frontend funcional | [frontend/](../../../frontend/) | capturas 01–05 | ✅ |
| Clave solo en variables de entorno | `.env` en `.gitignore` | [verificacion-env.txt](verificacion-env.txt) | ✅ |
| Errores del proveedor: 429, tiempo agotado, vacío | `ClienteLLM._con_reintentos` | [pytest.txt](pytest.txt), [log-llm-ejemplo.jsonl](log-llm-ejemplo.jsonl), captura 05 | ✅ |
| Log por solicitud (tokens y tiempo) | `logs/llm.jsonl` | [log-llm-ejemplo.jsonl](log-llm-ejemplo.jsonl) | ✅ |
| Pruebas con un mock del modelo | [tests/](../../../tests/) | [pytest.txt](pytest.txt): 35 pruebas | ✅ |
| Arquitectura (C4) y ADR | [03-arquitectura.md](../../03-arquitectura.md), [09-decisiones.md](../../09-decisiones.md) | — | ✅ |
| Problemas encontrados | [problemas-encontrados.md](problemas-encontrados.md) | — | ✅ |

## Capturas (`capturas/`)

Tomadas el 23/10/2026 con Edge sin interfaz gráfica (headless), en una pantalla de **360 × 740 px**.
⚠️ **Las respuestas son del proveedor simulado** (`scripts/servidor_simulado.py`), no del modelo real; el texto lo
dice explícitamente. Muestran el comportamiento de la interfaz y del manejo de errores.

| Archivo | Qué demuestra | Resultado verificado |
| :--- | :--- | :--- |
| `01-inicio-360px.png` | Pantalla inicial, aviso fijo, sugerencias del levantamiento | Sin scroll horizontal (`scrollWidth` = 360) |
| `02-esperando-boton-deshabilitado.png` | Botón deshabilitado mientras espera | Texto «Enviando…», `disabled = true` |
| `03-respuesta-streaming.png` | Respuesta recibida en streaming con formato | Viñetas y negritas; texto escapado |
| `04-error-sin-senal.png` | Navegador sin conexión | «No tiene señal de internet. Su pregunta no se envió…» |
| `05-error-proveedor-caido.png` | Proveedor detenido: el backend reintenta 3 veces y responde 503 | «El asistente no está disponible en este momento…»; la pregunta vuelve al campo |
| `06-swagger-docs.png` | Documentación de la API | `/chat` y `/health` |

Además se comprobó que el historial se mantiene al recargar la página (2 burbujas tras recargar).

### Capturas pendientes (con el modelo real)

- [ ] `07-respuesta-real-monilla.png` — entrada 1 con Gemini
- [ ] `08-alternativas.png` — entrada 3 (síntomas compatibles con varias enfermedades)
- [ ] `09-dosis-rechazada.png` — entrada 7 (dosis del almacén)
- [ ] `10-telefono-real.jpg` — foto/captura desde un teléfono de un integrante
- [ ] `11-comparacion-prompts.png` — tabla de `05-prompts.md` calificada

## Cómo reproducir

```bash
pytest                                             # 35 pruebas, sin API
python scripts/servidor_simulado.py                # terminal 1: proveedor falso en :8099
# terminal 2, con LLM_PRINCIPAL=simulado y LLM_RESPALDO= en .env:
uvicorn app.main:app --reload                      # abrir http://localhost:8000 (F12 → modo teléfono 360 px)
python scripts/demo_429.py                         # ronda 1 falla con 429, ronda 2 responde 8/8
```
