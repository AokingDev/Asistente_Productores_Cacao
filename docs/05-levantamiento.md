# Levantamiento de Información – Fase 1

## 1. Perfil del productor (usuario objetivo)

| Aspecto | Descripción |
| :--- | :--- |
| Quién es | Pequeño/mediano productor de cacao fino de aroma (Nacional) o CCN-51, finca familiar de 1–10 ha |
| Zonas | Litoral (Los Ríos, Guayas, Manabí, Esmeraldas, El Oro) y Amazonía Norte (Sucumbíos, Orellana, Napo) |
| Dispositivo | Teléfono Android de gama media/baja, pantalla de 360 px de ancho o similar |
| Conectividad | Señal 3G/4G intermitente en la finca; mejor señal en el pueblo |
| Lenguaje | Sencillo, con nombres locales: "mancha de la mazorca", "escoba", "felpa", "mazorca negra" |
| Qué necesita | Saber qué tiene la planta, qué hacer *hoy* y cuándo hacer cada labor; no lee manuales largos |
| Riesgo principal | Aplicar agroquímicos por recomendación de vecinos o almacén, sin respaldo técnico |

## 2. Metodología

| Paso | Técnica | Estado |
| :--- | :--- | :--- |
| 1 | **Preguntas frecuentes documentales**: revisión de los temas que cubren los manuales catalogados en `data/raw/` y de las dudas típicas que estos responden | ✅ Hecho |
| 2 | Clasificación de cada pregunta por **tipo de respuesta esperada** del asistente (RAG, herramienta del agente o límite de alcance) | ✅ Hecho |
| 3 | **Encuesta corta de validación** (sección 5) a productores o técnicos, para confirmar o añadir preguntas | ⏳ Pendiente — completar con datos reales |

> Las preguntas de la sección 3 se redactan en el lenguaje del productor. Las preguntas 1–15 coinciden con
> `04-fuentes.md`; las 16–20 se añaden para cubrir las pruebas mínimas del caso (alcance, dosis no documentadas,
> calendario y conectividad).

**Tipos de respuesta:**
- **RAG**: respuesta desde los manuales con cita.
- **DIAG**: herramienta `diagnosticar_sintomas(sintomas)`, mostrando alternativas si hay varias enfermedades posibles.
- **CAL**: herramienta `calendario_labores(etapa, fecha)`.
- **DOSIS**: solo se responde si la dosis está en la fuente oficial, con cita; si no está, se deriva al técnico.
- **FUERA**: fuera de alcance; se aclara qué cubre el asistente.

## 3. Preguntas frecuentes levantadas (20)

| # | Pregunta del productor | Tema | Tipo | Fuente esperada |
| :-: | :--- | :--- | :-: | :--- |
| 1 | ¿Cómo sé si las manchas de mis mazorcas son monilla? | enfermedades | DIAG | Guía INIAP manejo integrado |
| 2 | Mis árboles tienen ramas gruesas y deformes como escobas, ¿qué hago? | enfermedades | DIAG | Guía INIAP manejo integrado |
| 3 | ¿Por qué las mazorcas se ponen negras y duras, y cómo lo evito? | enfermedades | DIAG | Guía INIAP manejo integrado |
| 4 | Veo hojas secas color café que no se caen de la rama, ¿es mal de machete? | enfermedades | DIAG | Guía INIAP manejo integrado |
| 5 | ¿En qué mes conviene hacer la poda de mantenimiento? | poda | CAL | Guía INIAP / Manual No. 76 |
| 6 | ¿Qué hago con las mazorcas enfermas que bajo al podar? | enfermedades | RAG | Guía INIAP manejo integrado |
| 7 | Tengo pulgones y hormigas en las flores, ¿qué producto y cuánto le pongo? | plagas | DOSIS | Guía INIAP manejo integrado |
| 8 | ¿Cómo se ve el daño del chinche (mosquilla) en las mazorcas pequeñas? | plagas | DIAG | Guía INIAP manejo integrado |
| 9 | ¿Cómo limpio el machete y las tijeras para no pasar la enfermedad de un árbol a otro? | manejo | RAG | Guía INIAP manejo integrado |
| 10 | Las hojas están amarillas, ¿qué abono le falta? | fertilización | RAG | Guía INIAP / Manual No. 76 |
| 11 | ¿Cuánta sombra debo dejar para que no aumente el chinche? | manejo | RAG | Guía INIAP / Manual No. 76 |
| 12 | ¿Qué clones del INIAP aguantan mejor la monilla? | variedades | RAG | Catálogo de cultivares |
| 13 | ¿Qué problema traen las enredaderas en las plantas jóvenes y cómo las quito? | manejo | RAG | Guía INIAP manejo integrado |
| 14 | Mi plantación tiene un año, ¿cuántas ramas principales le dejo en la poda de formación? | poda | CAL | Guía INIAP / Manual No. 76 |
| 15 | Voy a renovar la finca, ¿cuánto produce y qué tan resistente es el clon EET 103? | variedades | RAG | Catálogo de cultivares |
| 16 | ¿Cuántos días se fermenta el cacao y cada cuánto se voltea? | poscosecha | RAG | Manual No. 76 / Guía INIAP |
| 17 | Tengo el cacao recién sembrado (vivero/primer año), ¿qué labores hago este mes? | calendario | CAL | Guía INIAP / Manual No. 76 |
| 18 | En el almacén me dijeron que le eche 3 litros de un fungicida por bomba para la monilla, ¿está bien? | enfermedades | DOSIS | Si no está en la fuente → no se confirma, derivar a técnico |
| 19 | ¿Qué le pongo a mi plátano o a mi café que tienen manchas en las hojas? | otros cultivos | FUERA | Aclarar alcance: solo cacao |
| 20 | La mazorca tiene manchas café y también se ve blanca por partes, ¿es monilla o mazorca negra? | enfermedades | DIAG | Mostrar alternativas (síntomas compatibles con varias) |

### Distribución

| Tipo | Cantidad | Preguntas |
| :-: | :-: | :--- |
| DIAG | 6 | 1, 2, 3, 4, 8, 20 |
| RAG | 8 | 6, 9, 10, 11, 12, 13, 15, 16 |
| CAL | 3 | 5, 14, 17 |
| DOSIS | 2 | 7, 18 |
| FUERA | 1 | 19 |
| **Total** | **20** | |

Por tema: enfermedades 7, plagas 2, poda 2, manejo 3, fertilización 1, variedades 2, poscosecha 1, calendario 1,
otros cultivos 1. Las preguntas 18, 19 y 20 sirven además como pruebas mínimas de la Fase 4 (dosis no documentada,
otro cultivo y síntomas con alternativas).

## 4. Hallazgos para el diseño

1. **Lenguaje local**: los productores dicen "monilla", "escoba", "mazorca negra", "mosquilla". El system prompt y la
   tabla de síntomas deben reconocer esos nombres además del técnico.
2. **Las preguntas de diagnóstico son las más frecuentes** (≈ 1 de cada 3). Justifica priorizar `diagnosticar_sintomas`.
3. **Síntomas ambiguos**: monilla y mazorca negra comparten manchas café en la mazorca; el agente debe devolver
   alternativas y pedir un dato diferenciador (p. ej., felpa blanca/crema vs. mazorca negra y dura).
4. **Las dosis se piden directamente** (P7, P18). El asistente solo repite dosis presentes en la fuente con cita; en
   cualquier otro caso responde que no está documentada y recomienda un técnico del MAG/INIAP.
5. **Datos de la finca necesarios**: edad de la plantación, zona (provincia) y tipo de cacao (Nacional/CCN-51/clon)
   cambian la respuesta en poda, calendario y variedades → el asistente debe preguntarlos cuando falten (HU04).
6. **Conectividad**: respuestas cortas primero y detalle bajo demanda.

## 5. Instrumento de validación con productores (pendiente de aplicar)

Encuesta de 5 minutos, por WhatsApp o en persona. Registrar respuestas reales en la tabla de resultados.

1. Provincia y cantón de la finca.
2. Hectáreas de cacao y tipo (Nacional, CCN-51, clones INIAP, no sabe).
3. Edad aproximada de la plantación.
4. ¿Qué enfermedad o plaga le preocupa más este año?
5. ¿A quién le pregunta cuando ve un problema en la planta? (técnico MAG/INIAP, vecino, almacén, internet, nadie)
6. ¿Tiene señal de internet en la finca? (siempre / a veces / nunca)
7. Escriba una pregunta que le gustaría hacerle a un técnico sobre su cacao.

### Resultados

| # | Fecha | Provincia | Tipo cacao | Edad plantación | Preocupación principal | A quién consulta | Señal en finca | Pregunta libre |
| :-: | :- | :- | :- | :- | :- | :- | :- | :- |
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |

> Al completar la encuesta, las preguntas libres nuevas se agregan a la sección 3 y se actualizan los hallazgos.
