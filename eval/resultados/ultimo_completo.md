# Evaluación de punta a punta

Fecha: 05/11/2026 17:32 · proveedores que respondieron: gemini, groq · tiempo promedio 2.3 s

> ⚠️ Sin modelo (cuota agotada o proveedor caído), **excluidos de las métricas**: S09. Repetirlos con `--solo`.

| Métrica | Resultado |
|---|---|
| Preguntas correctas (todas las verificaciones) | 19/20 (95 %) |
| Respuestas con cita (sin contar abstenciones) | 16/17 (94 %) |
| Abstención o aclaración de alcance correcta | 3/3 (100 %) |
| Respuestas con dosis no respaldada por la fuente | 0 de 20 → indicador 100 % limitado a la fuente: ✅ |
| Preguntas de dosis correctas | 1/2 (50 %) |
| Síntomas: esperado entre las alternativas (herramienta o respuesta) | 9/9 (100 %) → indicador ≥ 80 %: ✅ |
| Síntomas: esperado nombrado en la respuesta al productor | 9/9 (100 %) |
| Fallos por recuperación / generación / proveedor | 0 / 1 / 0 |

## Preguntas de referencia

| # | Categoría | ¿OK? | Fallo | Verificaciones | Citas | Proveedor | s |
|---|---|---|---|---|---|---|---|
| P01 | consulta | ✅ | — | falla: — | [4, 1] | groq | 2.4 |
| P02 | consulta | ✅ | — | falla: — | [2, 1, 4] | groq | 2.6 |
| P03 | consulta | ✅ | — | falla: — | [1, 3, 5, 4] | groq | 1.4 |
| P04 | consulta | ✅ | — | falla: — | [1, 2, 3] | groq | 1.6 |
| P05 | consulta | ✅ | — | falla: — | [1, 2, 3] | groq | 2.2 |
| P06 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.1 |
| P07 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.2 |
| P08 | consulta | ✅ | — | falla: — | [2] | groq | 1.8 |
| P09 | consulta | ✅ | — | falla: — | [1] | groq | 1.4 |
| P10 | dosis | ✅ | — | falla: — | [1] | groq | 2.0 |
| P11 | dosis_ajena | ❌ | generación | falla: cita | — | groq | 3.4 |
| P12 | contradiccion | ✅ | — | falla: — | [1, 2] | groq | 1.7 |
| P13 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.5 |
| P14 | consulta | ✅ | — | falla: — | [1] | groq | 1.5 |
| P15 | consulta | ✅ | — | falla: — | [1, 4] | groq | 2.4 |
| P16 | contradiccion | ✅ | — | falla: — | [1, 4] | groq | 1.4 |
| P17 | consulta | ✅ | — | falla: — | [1] | groq | 1.1 |
| P18 | fuera_alcance | ✅ | — | falla: — | — | groq | 1.1 |
| P19 | abstencion | ✅ | — | falla: — | — | groq | 1.7 |
| P20 | abstencion | ✅ | — | falla: — | — | groq | 1.0 |

## Síntomas

| # | Esperado | Alternativas de la herramienta | ¿En alternativas? | ¿En la respuesta? |
|---|---|---|---|---|
| S01 | moniliasis | moniliasis | ✅ | ✅ |
| S02 | escoba_bruja | escoba_bruja | ✅ | ✅ |
| S03 | mazorca_negra | mazorca_negra | ✅ | ✅ |
| S04 | mal_machete | mal_machete | ✅ | ✅ |
| S05 | chinche_monalonion | chinche_monalonion | ✅ | ✅ |
| S06 | hormiga_arriera | hormiga_arriera | ✅ | ✅ |
| S07 | pulgon | pulgon | ✅ | ✅ |
| S08 | moniliasis | moniliasis | ✅ | ✅ |
| S09 | termitas | termitas | sin modelo | sin modelo |
| S10 | gallina_ciega | gallina_ciega | ✅ | ✅ |

Respuestas completas en el JSON de esta corrida.
