# Evaluación de punta a punta

Fecha: 28/10/2026 22:14 · proveedores que respondieron: groq · tiempo promedio 2.1 s

| Métrica | Resultado |
|---|---|
| Preguntas correctas (todas las verificaciones) | 17/20 (85 %) |
| Respuestas con cita (sin contar abstenciones) | 16/17 (94 %) |
| Abstención o aclaración de alcance correcta | 3/3 (100 %) |
| Respuestas con dosis no respaldada por la fuente | 2 de 20 → indicador 100 % limitado a la fuente: ❌ |
| Preguntas de dosis correctas | 1/2 (50 %) |
| Síntomas: esperado entre las alternativas (herramienta o respuesta) | 10/10 (100 %) → indicador ≥ 80 %: ✅ |
| Síntomas: esperado nombrado en la respuesta al productor | 10/10 (100 %) |
| Fallos por recuperación / generación / proveedor | 1 / 2 / 0 |

## Preguntas de referencia

| # | Categoría | ¿OK? | Fallo | Verificaciones | Citas | Proveedor | s |
|---|---|---|---|---|---|---|---|
| P01 | consulta | ✅ | — | falla: — | [1, 3, 2] | groq | 3.1 |
| P02 | consulta | ✅ | — | falla: — | [1, 2, 3] | groq | 1.2 |
| P03 | consulta | ✅ | — | falla: — | [1, 3] | groq | 1.7 |
| P04 | consulta | ✅ | — | falla: — | [1, 2] | groq | 2.1 |
| P05 | consulta | ✅ | — | falla: — | [4] | groq | 1.6 |
| P06 | consulta | ✅ | — | falla: — | [1, 2] | groq | 2.5 |
| P07 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.0 |
| P08 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.4 |
| P09 | consulta | ✅ | — | falla: — | [1] | groq | 1.5 |
| P10 | dosis | ✅ | — | falla: — | [1] | groq | 1.1 |
| P11 | dosis_ajena | ❌ | recuperación | falla: cita | — | groq | 1.6 |
| P12 | contradiccion | ✅ | — | falla: — | [1, 2] | groq | 1.4 |
| P13 | consulta | ✅ | — | falla: — | [2, 3] | groq | 1.7 |
| P14 | consulta | ❌ | generación | falla: sin_dosis_inventada | [1] | groq | 1.8 |
| P15 | consulta | ❌ | generación | falla: sin_dosis_inventada | [1, 4] | groq | 1.5 |
| P16 | contradiccion | ✅ | — | falla: — | [1, 4] | groq | 1.2 |
| P17 | consulta | ✅ | — | falla: — | [1] | groq | 1.2 |
| P18 | fuera_alcance | ✅ | — | falla: — | — | groq | 1.1 |
| P19 | abstencion | ✅ | — | falla: — | — | groq | 1.2 |
| P20 | abstencion | ✅ | — | falla: — | — | groq | 2.0 |

## Síntomas

| # | Esperado | Alternativas de la herramienta | ¿En alternativas? | ¿En la respuesta? |
|---|---|---|---|---|
| S01 | moniliasis | moniliasis | ✅ | ✅ |
| S02 | escoba_bruja | escoba_bruja | ✅ | ✅ |
| S03 | mazorca_negra | mazorca_negra | ✅ | ✅ |
| S04 | mal_machete | mal_machete | ✅ | ✅ |
| S05 | chinche_monalonion | chinche_monalonion | ✅ | ✅ |
| S06 | hormiga_arriera | hormiga_arriera | ✅ | ✅ |
| S07 | pulgon | pulgon, mazorca_negra | ✅ | ✅ |
| S08 | moniliasis | moniliasis | ✅ | ✅ |
| S09 | termitas | termitas | ✅ | ✅ |
| S10 | gallina_ciega | gallina_ciega | ✅ | ✅ |

Respuestas completas en el JSON de esta corrida.
