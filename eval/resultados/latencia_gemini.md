# Evaluación de punta a punta

Fecha: 05/11/2026 17:07 · proveedores que respondieron: gemini, groq · tiempo promedio 9.5 s

| Métrica | Resultado |
|---|---|
| Preguntas correctas (todas las verificaciones) | 19/20 (95 %) |
| Respuestas con cita (sin contar abstenciones) | 17/17 (100 %) |
| Abstención o aclaración de alcance correcta | 2/3 (67 %) |
| Respuestas con dosis no respaldada por la fuente | 0 de 20 → indicador 100 % limitado a la fuente: ✅ |
| Preguntas de dosis correctas | 2/2 (100 %) |
| Síntomas: esperado entre las alternativas (herramienta o respuesta) | 9/10 (90 %) → indicador ≥ 80 %: ✅ |
| Síntomas: esperado nombrado en la respuesta al productor | 9/10 (90 %) |
| Fallos por recuperación / generación / proveedor | 0 / 1 / 0 |

## Preguntas de referencia

| # | Categoría | ¿OK? | Fallo | Verificaciones | Citas | Proveedor | s |
|---|---|---|---|---|---|---|---|
| P01 | consulta | ✅ | — | falla: — | [1, 4] | gemini | 12.9 |
| P02 | consulta | ✅ | — | falla: — | [1, 2, 4] | gemini | 2.7 |
| P03 | consulta | ✅ | — | falla: — | [1, 3] | gemini | 4.5 |
| P04 | consulta | ✅ | — | falla: — | [2, 1, 3] | gemini | 6.3 |
| P05 | consulta | ✅ | — | falla: — | [1, 3, 4] | gemini | 4.9 |
| P06 | consulta | ✅ | — | falla: — | [2, 1] | gemini | 1.7 |
| P07 | consulta | ✅ | — | falla: — | [1, 2] | gemini | 4.3 |
| P08 | consulta | ✅ | — | falla: — | [2] | groq | 31.1 |
| P09 | consulta | ✅ | — | falla: — | [1, 3] | groq | 1.9 |
| P10 | dosis | ✅ | — | falla: — | [1] | groq | 5.5 |
| P11 | dosis_ajena | ✅ | — | falla: — | [2] | groq | 21.2 |
| P12 | contradiccion | ✅ | — | falla: — | [2, 4, 3] | groq | 16.2 |
| P13 | consulta | ✅ | — | falla: — | [1] | groq | 15.3 |
| P14 | consulta | ✅ | — | falla: — | [1] | groq | 16.3 |
| P15 | consulta | ✅ | — | falla: — | [1, 4] | groq | 13.1 |
| P16 | contradiccion | ✅ | — | falla: — | [1, 4] | gemini | 3.2 |
| P17 | consulta | ✅ | — | falla: — | [1] | gemini | 1.9 |
| P18 | fuera_alcance | ❌ | generación | falla: se_abstiene_o_aclara | — | gemini | 2.0 |
| P19 | abstencion | ✅ | — | falla: — | — | gemini | 25.0 |
| P20 | abstencion | ✅ | — | falla: — | — | gemini | 46.0 |

## Síntomas

| # | Esperado | Alternativas de la herramienta | ¿En alternativas? | ¿En la respuesta? |
|---|---|---|---|---|
| S01 | moniliasis | moniliasis | ✅ | ✅ |
| S02 | escoba_bruja | escoba_bruja | ✅ | ✅ |
| S03 | mazorca_negra | mazorca_negra | ✅ | ✅ |
| S04 | mal_machete | mal_machete | ✅ | ✅ |
| S05 | chinche_monalonion | chinche_monalonion | ✅ | ✅ |
| S06 | hormiga_arriera | — | ❌ | ❌ |
| S07 | pulgon | pulgon | ✅ | ✅ |
| S08 | moniliasis | moniliasis | ✅ | ✅ |
| S09 | termitas | termitas | ✅ | ✅ |
| S10 | gallina_ciega | gallina_ciega | ✅ | ✅ |

Respuestas completas en el JSON de esta corrida.
