# Evaluación de punta a punta

Fecha: 29/10/2026 00:11 · proveedores que respondieron: gemini, groq · tiempo promedio 8.1 s

| Métrica | Resultado |
|---|---|
| Preguntas correctas (todas las verificaciones) | 14/20 (70 %) |
| Respuestas con cita (sin contar abstenciones) | 16/17 (94 %) |
| Abstención o aclaración de alcance correcta | 2/3 (67 %) |
| Respuestas con dosis no respaldada por la fuente | 1 de 20 → indicador 100 % limitado a la fuente: ❌ |
| Preguntas de dosis correctas | 1/2 (50 %) |
| Síntomas: esperado entre las alternativas (herramienta o respuesta) | 5/10 (50 %) → indicador ≥ 80 %: ❌ |
| Síntomas: esperado nombrado en la respuesta al productor | 3/10 (30 %) |
| Fallos por recuperación / generación / proveedor | 0 / 6 / 0 |

## Preguntas de referencia

| # | Categoría | ¿OK? | Fallo | Verificaciones | Citas | Proveedor | s |
|---|---|---|---|---|---|---|---|
| P01 | consulta | ✅ | — | falla: — | [1, 4] | groq | 2.3 |
| P02 | consulta | ❌ | generación | falla: claves | [1] | groq | 1.2 |
| P03 | consulta | ✅ | — | falla: — | [5, 3, 1] | groq | 1.7 |
| P04 | consulta | ✅ | — | falla: — | [1, 2, 3] | groq | 6.2 |
| P05 | consulta | ❌ | generación | falla: sin_dosis_inventada | [1, 3] | groq | 3.1 |
| P06 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.4 |
| P07 | consulta | ✅ | — | falla: — | [1, 2] | groq | 2.0 |
| P08 | consulta | ✅ | — | falla: — | [1, 2] | groq | 1.3 |
| P09 | consulta | ✅ | — | falla: — | [1] | groq | 1.3 |
| P10 | dosis | ✅ | — | falla: — | [1] | groq | 2.2 |
| P11 | dosis_ajena | ❌ | generación | falla: cita | — | groq | 1.3 |
| P12 | contradiccion | ✅ | — | falla: — | [2, 4] | groq | 3.4 |
| P13 | consulta | ✅ | — | falla: — | [1] | groq | 1.5 |
| P14 | consulta | ❌ | generación | falla: claves | [1] | groq | 1.3 |
| P15 | consulta | ✅ | — | falla: — | [1, 4] | groq | 1.5 |
| P16 | contradiccion | ❌ | generación | falla: cita_dos_fuentes | [2, 4] | groq | 2.6 |
| P17 | consulta | ✅ | — | falla: — | [1] | groq | 1.4 |
| P18 | fuera_alcance | ❌ | generación | falla: se_abstiene_o_aclara | — | groq | 1.3 |
| P19 | abstencion | ✅ | — | falla: — | — | groq | 3.1 |
| P20 | abstencion | ✅ | — | falla: — | — | groq | 1.7 |

## Síntomas

| # | Esperado | Alternativas de la herramienta | ¿En alternativas? | ¿En la respuesta? |
|---|---|---|---|---|
| S01 | moniliasis | moniliasis | ✅ | ✅ |
| S02 | escoba_bruja | escoba_bruja | ✅ | ✅ |
| S03 | mazorca_negra | mazorca_negra | ✅ | ❌ |
| S04 | mal_machete | barrenador, mal_machete | ✅ | ❌ |
| S05 | chinche_monalonion | chinche_monalonion | ✅ | ✅ |
| S06 | hormiga_arriera | — | ❌ | ❌ |
| S07 | pulgon | — | ❌ | ❌ |
| S08 | moniliasis | — | ❌ | ❌ |
| S09 | termitas | — | ❌ | ❌ |
| S10 | gallina_ciega | — | ❌ | ❌ |

Respuestas completas en el JSON de esta corrida.
