# Requisitos del Sistema e Historias de Usuario

## Historias de Usuario

### HU01: Diagnóstico preliminar de Moniliasis

- **Dado** un productor que observa manchas inusuales en sus mazorcas de cacao.
- **Cuando** describe síntomas como "felpa blanca" y "manchas anaranjadas" al asistente.
- **Entonces** el sistema identifica un posible caso de Moniliasis y sugiere medidas culturales basadas en el manual del INIAP.

### HU02: Consulta de labores de poda

- **Dado** un agricultor que necesita realizar el mantenimiento estacional a sus árboles.
- **Cuando** pregunta sobre cómo y en qué mes podar el cacao.
- **Entonces** el sistema le proporciona los pasos técnicos oficiales para la poda de formación y mantenimiento.

### HU03: Identificación de Escoba de Bruja

- **Dado** un usuario preocupado por la aparición de ramas engrosadas en su cultivo.
- **Cuando** ingresa la descripción de "escobas verdes, gruesas y rugosas".
- **Entonces** el sistema diagnostica un posible ataque de Escoba de Bruja y recomienda la eliminación inmediata del material afectado.

### HU04: Recolección de Datos de Finca

- **Dado** un productor que realiza su primera consulta en la aplicación.
- **Cuando** envía un saludo o una pregunta genérica sin dar contexto.
- **Entonces** el asistente solicita amablemente la provincia, cantón y la edad de la plantación antes de proceder a diagnosticar.

### HU05: Selección de Clones y Variedades (Catálogo INIAP)

- **Dado** un productor que está planificando sembrar una nueva parcela.
- **Cuando** solicita recomendaciones de variedades de cacao que sean resistentes a enfermedades.
- **Entonces** el sistema lista los cultivares recomendados extrayendo la información del Catálogo de Cultivares del INIAP.

### HU06: Descargo de Responsabilidad Fitosanitaria

- **Dado** cualquier usuario interactuando con el bot de IA.
- **Cuando** el sistema emite un diagnóstico de plaga o enfermedad.
- **Entonces** incluye automáticamente una advertencia indicando que la información es una guía referencial y que se debe consultar presencialmente a un técnico agrícola.

### HU07: Control de Plagas (Pulgones)

- **Dado** un productor con infestación de insectos en los brotes tiernos de cacao.
- **Cuando** reporta la presencia de pulgones y hormigas en las hojas.
- **Entonces** el bot recomienda el uso de trampas de color o control químico oficial especificando las dosis del manual.

### HU08: Adaptabilidad en Terreno (Responsividad Mobile-First)

- **Dado** un usuario trabajando en su finca con un teléfono móvil básico o de pantalla pequeña.
- **Cuando** abre la aplicación web/móvil del asistente.
- **Entonces** la interfaz se adapta correctamente a un ancho mínimo de 360px sin requerir hacer zoom o scroll horizontal.

## Requisitos No Funcionales (Medibles)

1. **Rendimiento (Latencia):** El tiempo de respuesta del asistente basado en el LLM no debe superar los **5 segundos en el percentil 95 (p95)** por mensaje bajo una conexión de red 3G/4G estable.
2. **Confiabilidad (Hallucination Rate):** El 100% de las respuestas técnicas, diagnósticos y recomendaciones de dosis químicas generadas por la IA deben estar fundamentadas exclusivamente en la Base de Conocimiento (RAG) de los manuales del INIAP y MAG, logrando una tasa de alucinación del 0% en temas fitosanitarios.
   * **Método de medición:** Se evalúa con un conjunto de prueba de al menos 50 preguntas (incluidas las 15 del levantamiento real de `04-fuentes.md`). Un técnico agrícola revisa cada respuesta y la marca como alucinación si contiene un dato, producto o dosis que no aparece en los fragmentos recuperados de los manuales. Tasa de alucinación = respuestas con alucinación / total de respuestas evaluadas.
3. **Usabilidad (Resolución):** La interfaz gráfica de usuario (UI) debe renderizarse y ser completamente operativa en dispositivos móviles con resoluciones de al menos 360x640 píxeles (Mobile-first).
4. **Disponibilidad:** El backend y el servicio de IA deben tener un tiempo de actividad (Uptime) del **99%** durante las horas de consulta de los agricultores (06:00 a 18:00).
