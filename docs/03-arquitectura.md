# Arquitectura del Sistema (modelo C4)

El Asistente Agrotécnico para Productores de Cacao es una aplicación web mobile-first con un backend FastAPI que
encapsula al modelo generativo. En la semana 2 funciona como **chat con streaming**; en la semana 3 se agregan el
**RAG con citas** sobre los manuales del INIAP/MAG y el **agente** con sus tres herramientas.

> Convención: los elementos con borde punteado se implementan en la semana 3. Decisiones en
> [09-decisiones.md](09-decisiones.md).

## Nivel 1 · Contexto

```mermaid
flowchart TB
    productor["👤 <b>Productor de cacao</b><br/>Pequeño productor, teléfono de gama<br/>media/baja, señal intermitente"]
    tecnico["👤 <b>Técnico MAG / INIAP</b><br/>Confirma el diagnóstico en campo"]
    sistema["<b>Asistente Agrotécnico Cacao</b><br/>Responde consultas, orienta un diagnóstico<br/>preliminar y arma el calendario de labores"]
    llm["<b>Proveedor de IA generativa</b><br/>Gemini (principal) · Groq (respaldo)"]
    manuales["<b>Manuales oficiales</b><br/>Repositorio INIAP · MAG"]

    productor -- "Describe síntomas y pregunta<br/>(HTTPS, desde el navegador)" --> sistema
    sistema -- "Recomienda confirmar con" --> tecnico
    sistema -- "Chat Completions API<br/>(HTTPS, clave en el backend)" --> llm
    manuales -. "PDF descargados e indexados<br/>(semana 3)" .-> sistema

    classDef persona fill:#08427b,color:#fff,stroke:#052e56
    classDef sist fill:#1168bd,color:#fff,stroke:#0b4884
    classDef ext fill:#999,color:#fff,stroke:#6b6b6b
    class productor,tecnico persona
    class sistema sist
    class llm,manuales ext
```

## Nivel 2 · Contenedores

```mermaid
flowchart TB
    productor["👤 Productor"]

    subgraph sistema["Asistente Agrotécnico Cacao (un solo servicio desplegable)"]
        web["<b>Interfaz web</b><br/>HTML + CSS + JS sin framework<br/><i>frontend/</i><br/>Chat mobile-first (360 px), historial<br/>en localStorage, streaming"]
        api["<b>API</b><br/>Python 3.11+ · FastAPI · Pydantic<br/><i>app/</i><br/>POST /chat (NDJSON) · GET /health<br/>Sirve también la interfaz web"]
        logs[("<b>Registro</b><br/>logs/llm.jsonl<br/>tokens y tiempos por solicitud")]
        vec[("<b>Base vectorial</b><br/>fragmentos de manuales<br/>con metadato tema")]:::futuro
        consultas[("<b>Registro de consultas</b><br/>registrar_consulta(datos)")]:::futuro
    end

    gemini["Gemini API<br/>(principal)"]
    groq["Groq API<br/>(respaldo)"]

    productor -- "HTTPS" --> web
    web -- "fetch POST /chat<br/>JSON → NDJSON en streaming" --> api
    api -- "escribe" --> logs
    api -- "OpenAI-compatible, streaming" --> gemini
    api -. "si Gemini falla" .-> groq
    api -. "búsqueda semántica" .-> vec
    api -. "guarda" .-> consultas

    classDef futuro stroke-dasharray: 5 5,fill:#f4f4f4,color:#555
    classDef cont fill:#438dd5,color:#fff,stroke:#2e6295
    classDef ext fill:#999,color:#fff,stroke:#6b6b6b
    class web,api cont
    class gemini,groq ext
```

## Nivel 3 · Componentes de la API

```mermaid
flowchart LR
    web["Interfaz web"]

    subgraph api["API (FastAPI)"]
        main["<b>app/main.py</b><br/>Rutas /chat y /health<br/>Traduce errores a mensajes claros"]
        schemas["<b>app/schemas.py</b><br/>ChatSolicitud, Mensaje (entrada)<br/>RespuestaAsistente (salida JSON)"]
        prompts["<b>app/prompts/</b><br/>system_v1 · v2 · v3 (activo)"]
        llm["<b>app/services/llm.py</b><br/>ClienteLLM: reintentos, espera<br/>exponencial, respaldo, streaming, log"]
        config["<b>app/config.py</b><br/>Lee .env · catálogo de proveedores"]
        rag["<b>app/services/rag.py</b><br/>Recupera fragmentos + citas"]:::futuro
        agente["<b>app/services/agente.py</b><br/>diagnosticar_sintomas · calendario_labores<br/>registrar_consulta"]:::futuro
    end

    proveedor["Gemini / Groq"]

    web --> main
    main -- "valida con" --> schemas
    main -- "carga" --> prompts
    main -- "generar_stream()" --> llm
    llm -- "usa" --> config
    llm -- "HTTPS" --> proveedor
    main -.-> agente
    agente -.-> rag
    agente -.-> llm

    classDef futuro stroke-dasharray: 5 5,fill:#f4f4f4,color:#555
    classDef comp fill:#85bbf0,color:#000,stroke:#5d82a8
    classDef ext fill:#999,color:#fff,stroke:#6b6b6b
    class main,schemas,prompts,llm,config comp
    class proveedor ext
```

**Regla de dependencia:** solo `app/services/llm.py` conoce al proveedor. Cambiar de Gemini a Groq u otro proveedor
compatible es cambiar variables del `.env`; los endpoints no se tocan.

## Flujo de una consulta (`POST /chat`)

```mermaid
sequenceDiagram
    autonumber
    actor P as Productor
    participant W as Interfaz web
    participant A as API /chat
    participant L as ClienteLLM
    participant G as Gemini
    participant Q as Groq (respaldo)

    P->>W: Escribe «manchas cafés y polvo blanco»
    W->>W: Deshabilita el botón («Enviando…»)
    W->>A: POST /chat {mensaje, historial (últimos 10)}
    A->>A: Valida con Pydantic (2–1000 caracteres, roles user/assistant)
    A->>L: generar_stream(system_v3, mensajes)
    L->>G: chat.completions (stream)
    alt 429 / tiempo agotado / respuesta vacía
        L->>L: Espera exponencial (o Retry-After) y reintenta (máx. 3)
        L->>Q: Si Gemini se rinde, pasa al respaldo
    end
    G-->>L: Primer trozo de texto
    L-->>A: Flujo abierto
    loop cada trozo
        A-->>W: {"tipo":"texto","texto":"…"}
        W-->>P: Muestra el texto mientras llega
    end
    L->>L: Registra tokens y tiempos en logs/llm.jsonl
    A-->>W: {"tipo":"fin", tokens, latencia}
    W->>W: Guarda el turno en localStorage y habilita el botón
    Note over A,W: Si ningún proveedor responde antes del primer trozo → 503 con mensaje claro.<br/>Si el flujo se corta a la mitad → {"tipo":"error"} y la respuesta se marca incompleta.
```

## Atributos de calidad y cómo se atienden

| Atributo | Mecanismo | Dónde |
| :--- | :--- | :--- |
| Seguridad de la clave | Solo en `.env` / variables de la plataforma; nunca en el frontend | `app/config.py`, `.gitignore` |
| Disponibilidad | Reintentos con espera exponencial, `Retry-After`, proveedor de respaldo | `app/services/llm.py` |
| Consumo excesivo (OWASP LLM10) | Mensaje ≤ 1000 caracteres, historial ≤ 10 turnos, `max_tokens`, tiempo límite | `app/schemas.py`, `.env` |
| Inyección de prompt (LLM01) | El rol `system` solo lo pone el servidor; el prompt ordena ignorar instrucciones del usuario | `app/schemas.py`, `system_v3.md` |
| Salida insegura (LLM05) | La respuesta del modelo se escapa antes de mostrarse (sin HTML crudo) | `frontend/app.js` |
| Desinformación (LLM09) | Sin productos ni dosis; abstención explícita; aviso fijo de orientación preliminar | `system_v3.md`, `frontend/index.html` |
| Usabilidad móvil | Mobile-first 360 px, botones ≥ 44 px, historial disponible sin señal | `frontend/styles.css` |
| Observabilidad | Una línea JSON por llamada: proveedor, intento, tokens, latencia (sin texto del usuario) | `logs/llm.jsonl` |
