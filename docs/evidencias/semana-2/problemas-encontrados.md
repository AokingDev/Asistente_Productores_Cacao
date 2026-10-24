# Problemas encontrados – Semana 2

| # | Problema | Causa | Solución | Prueba que lo cubre |
| :-: | :--- | :--- | :--- | :--- |
| 1 | El streaming del kit no reintentaba ante un 429 ni ante respuestas vacías | `generar_stream` llamaba al proveedor una sola vez | La política de reintentos se extrajo a `_con_reintentos` y se usa también al abrir el flujo | `test_stream_429_reintenta_con_retry_after`, `test_stream_vacio_se_reintenta` |
| 2 | El streaming no registraba tokens ni tiempo | Los proveedores solo envían el uso si se pide | Se pide `stream_options.include_usage` y la clase `Flujo` registra tokens, tiempo hasta el primer trozo y tiempo total | `test_stream_entrega_el_texto_y_registra_tokens` |
| 3 | Si el proveedor cortaba a mitad de respuesta, el kit pasaba al respaldo y el usuario recibía texto repetido | El cambio de proveedor ocurría después de haber enviado trozos | Solo se cambia de proveedor **antes** del primer trozo; después se envía `{"tipo":"error"}` y la interfaz marca la respuesta como incompleta | `test_stream_cortado_a_la_mitad_no_cambia_de_proveedor`, `test_corte_a_la_mitad_envia_evento_de_error` |
| 4 | Los modelos de razonamiento envían trozos vacíos al inicio | El «pensamiento» no viaja en `content` | Se espera el primer trozo **con texto** antes de dar el flujo por abierto | `test_stream_salta_trozos_vacios_iniciales` |
| 5 | El simulador del kit no soportaba streaming | Respondía siempre JSON completo | Se agregó respuesta SSE (`text/event-stream`) palabra por palabra | `test_stream_por_http_con_429_real_y_tokens` |
| 6 | Las pruebas de integración fallaban si había un simulador abierto en el puerto 8099 | En Windows dos procesos pueden escuchar el mismo puerto; las pruebas hablaban con el simulador equivocado | Las pruebas usan su propio puerto (8098) | — |
| 7 | Las pruebas escribían en el log real `logs/llm.jsonl` | Ruta de log fija | `LLM_LOG_DIR` configurable; `tests/conftest.py` usa una carpeta temporal | — |
| 8 | Sin clave configurada, `/chat` devolvía un 500 con el nombre de la variable | `ErrorConfiguracion` no se capturaba | Manejador que responde 503 «El asistente aún no está configurado» y deja el detalle en el log | `test_sin_clave_configurada_da_503_sin_detalles_internos` |
| 9 | El cliente podía enviar un mensaje con rol `system` en el historial (inyección) | Historial sin validar | `Mensaje.role` solo acepta `user`/`assistant` | `test_chat_rechaza_rol_system_en_el_historial` |
| 10 | `curl` en Git Bash (Windows) devolvía «error parsing the body» con tildes | La consola no enviaba el cuerpo en UTF-8 | Probar con `httpx`/Swagger, o `curl --data-binary @archivo.json` | — |
| 11 | Conflicto de numeración: la guía pide `docs/05-prompts.md`, pero `05` era el levantamiento | Numeración de la semana 1 | El levantamiento pasó a `docs/00-levantamiento.md` | — |
| 12 | Al pulsar «Detener» el servidor no se enteraba: la conexión con el proveedor seguía abierta y el modelo seguía generando tokens, sin ningún registro | Starlette no cierra un generador síncrono cuando el navegador se desconecta | El endpoint recorre el flujo con un generador asíncrono y, si no terminó, llama a `Flujo.cancelar()`, que cierra la conexión con el proveedor y registra `stream_cancelado` | `test_si_el_cliente_se_desconecta_se_cancela_el_flujo`, `test_detener_cierra_la_conexion_con_el_proveedor` |
| 13 | Si se detenía justo después del primer trozo, la conexión no se cerraba | El primer `yield` estaba fuera del bloque `try` | Se movió dentro | `test_detener_cierra_la_conexion_con_el_proveedor` |
| 14 | Un error de red no previsto a mitad del flujo (p. ej. `httpx.RemoteProtocolError`) llegaba crudo | Solo se capturaba `openai.APIError` | Cualquier error a mitad del flujo se traduce a `FlujoInterrumpido` (mensaje claro) | `test_error_inesperado_a_mitad_se_traduce_a_flujo_interrumpido` |

## Pendientes

- Ejecutar `scripts/comparar_prompts.py` con el modelo real y calificar la tabla (ADR-007, ADR-008).
- Probar desde un teléfono real (no solo con la emulación de 360 px).
- Confirmar con el grupo ADR-006 (frontend sin framework en lugar de Angular + Ionic).
