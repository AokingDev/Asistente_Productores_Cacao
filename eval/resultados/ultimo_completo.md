# Evaluación de punta a punta

Fecha: 04/11/2026 10:43 · proveedores que respondieron: gemini, groq · tiempo promedio 25.5 s

> ⚠️ Sin modelo (cuota agotada o proveedor caído), **excluidos de las métricas**: S09. Repetirlos con `--solo`.

| Métrica | Resultado |
|---|---|
| Preguntas correctas (todas las verificaciones) | 19/20 (95 %) |
| Respuestas con cita (sin contar abstenciones) | 17/17 (100 %) |
| Abstención o aclaración de alcance correcta | 3/3 (100 %) |
| Respuestas con dosis no respaldada por la fuente | 1 de 20 → indicador 100 % limitado a la fuente: ❌ |
| Preguntas de dosis correctas | 2/2 (100 %) |
| Síntomas: esperado entre las alternativas (herramienta o respuesta) | 9/9 (100 %) → indicador ≥ 80 %: ✅ |
| Síntomas: esperado nombrado en la respuesta al productor | 9/9 (100 %) |
| Fallos por recuperación / generación / proveedor | 0 / 1 / 0 |

## Preguntas de referencia

| # | Categoría | ¿OK? | Fallo | Verificaciones | Citas | Proveedor | s |
|---|---|---|---|---|---|---|---|
| P01 | consulta | ✅ | — | falla: — | [1, 4] | gemini | 23.0 |
| P02 | consulta | ✅ | — | falla: — | [1, 2, 4] | gemini | 16.1 |
| P03 | consulta | ✅ | — | falla: — | [1, 3] | gemini | 30.6 |
| P04 | consulta | ✅ | — | falla: — | [1, 2, 3] | gemini | 15.1 |
| P05 | consulta | ✅ | — | falla: — | [1, 3, 4] | gemini | 26.8 |
| P06 | consulta | ✅ | — | falla: — | [2, 1] | gemini | 17.7 |
| P07 | consulta | ✅ | — | falla: — | [1, 2] | gemini | 21.3 |
| P08 | consulta | ✅ | — | falla: — | [1] | gemini | 20.1 |
| P09 | consulta | ✅ | — | falla: — | [1, 2] | gemini | 28.5 |
| P10 | dosis | ✅ | — | falla: — | [1] | gemini | 19.6 |
| P11 | dosis_ajena | ✅ | — | falla: — | [2] | gemini | 22.9 |
| P12 | contradiccion | ✅ | — | falla: — | [1, 2, 3] | gemini | 17.4 |
| P13 | consulta | ✅ | — | falla: — | [1] | groq | 32.8 |
| P14 | consulta | ✅ | — | falla: — | [1] | groq | 1.5 |
| P15 | consulta | ❌ | generación | falla: sin_dosis_inventada | [1, 4] | groq | 1.4 |
| P16 | contradiccion | ✅ | — | falla: — | [1, 2] | groq | 14.2 |
| P17 | consulta | ✅ | — | falla: — | [1] | gemini | 23.6 |
| P18 | fuera_alcance | ✅ | — | falla: — | — | gemini | 25.6 |
| P19 | abstencion | ✅ | — | falla: — | — | gemini | 42.4 |
| P20 | abstencion | ✅ | — | falla: — | [4] | gemini | 21.0 |

## Síntomas

| # | Esperado | Alternativas de la herramienta | ¿En alternativas? | ¿En la respuesta? |
|---|---|---|---|---|
| S01 | moniliasis | moniliasis | ✅ | ✅ |
| S02 | escoba_bruja | escoba_bruja | ✅ | ✅ |
| S03 | mazorca_negra | mazorca_negra | ✅ | ✅ |
| S04 | mal_machete | — | ❌ | ✅ |
| S05 | chinche_monalonion | chinche_monalonion | ✅ | ✅ |
| S06 | hormiga_arriera | — | ❌ | ✅ |
| S07 | pulgon | pulgon | ✅ | ✅ |
| S08 | moniliasis | moniliasis | ✅ | ✅ |
| S09 | termitas | termitas | sin modelo | sin modelo |
| S10 | gallina_ciega | gallina_ciega | ✅ | ✅ |

Respuestas completas en el JSON de esta corrida.
