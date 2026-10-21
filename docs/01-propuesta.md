# Propuesta del Proyecto: Asistente Agrotécnico para Productores de Cacao

## Problema Real

Los pequeños y medianos productores de cacao en Ecuador sufren grandes pérdidas en sus cosechas debido a plagas y enfermedades (Moniliasis, Escoba de Bruja, Mal de Machete). El acceso a asistencia técnica del INIAP o MAG en campo es limitado, lo que lleva a diagnósticos erróneos y aplicación indebida de agroquímicos.

## Usuarios

Agricultores y productores cacaoteros que operan en campo. Utilizan teléfonos inteligentes de gama media/baja, con conectividad inestable. Requieren respuestas rápidas, prácticas y sin tecnicismos excesivos.

## Alcance

* Diagnóstico preliminar de enfermedades y plagas del cacao mediante la descripción de síntomas.
* Recomendación de labores culturales (podas, fertilización) basadas en calendarios oficiales.
* Recomendación de clones y variedades de cacao tolerantes a enfermedades.

## Alcance Negativo (Lo que NUNCA hará)

* **NO** recetará ni recomendará agroquímicos o dosis que no estén explícitamente en los manuales del INIAP/MAG.
* **NO** reemplazará la visita de un técnico agrícola profesional (siempre emitirá un descargo de responsabilidad).
* **NO** diagnosticará enfermedades de otros cultivos que no sean cacao.

## Riesgos

* **Alucinaciones del LLM:** Que el modelo invente un agroquímico o dosis inexistente. (Mitigación: Prompt estricto y RAG cerrado).
* **Disponibilidad:** Falta de internet en la finca del productor. (Mitigación: interfaz ligera y respuestas breves para conexiones lentas, historial de las últimas consultas guardado en el dispositivo para revisarlo sin conexión, y reintento automático de los mensajes cuando vuelva la señal).

## Modelo Elegido y Justificación

Se utilizará **Gemini Flash** en su versión estable vigente (familia Gemini 3.x Flash), o un modelo ligero equivalente de otro proveedor.

* **Justificación:** Son modelos altamente eficientes, rápidos y de bajo costo. Tienen una excelente capacidad para seguir instrucciones estrictas de sistema (System Prompts) y ventanas de contexto amplias, lo cual es ideal para procesar y extraer información exacta mediante RAG sin latencias altas en dispositivos móviles.
