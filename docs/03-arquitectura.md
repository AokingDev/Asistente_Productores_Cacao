# Arquitectura del Sistema (modelo C4)

El Asistente Agrotécnico para Productores de Cacao es una aplicación web mobile-first con un backend FastAPI que
encapsula al modelo generativo. Desde la semana 3 responde con **RAG y citas** sobre los manuales del INIAP, y un
**agente** con tres herramientas deterministas orienta el diagnóstico, arma el calendario y registra consultas con
confirmación humana. Decisiones en [09-decisiones.md](09-decisiones.md); detalle del RAG en [06-rag.md](06-rag.md).

## Nivel 1 · Contexto

```mermaid
flowchart TB
    productor["👤 <b>Productor de cacao</b><br/>Pequeño productor, teléfono de gama<br/>media/baja, señal intermitente"]
    tecnico["👤 <b>Técnico MAG / INIAP</b><br/>Confirma el diagnóstico y da<br/>seguimiento a las consultas registradas"]
    sistema["<b>Asistente Agrotécnico Cacao</b><br/>Responde con citas, orienta un diagnóstico<br/>preliminar y arma el calendario de labores"]
    llm["<b>Proveedores de IA generativa</b><br/>Gemini (principal) · Groq (respaldo)<br/>Embeddings de Gemini"]
    manuales["<b>Manuales oficiales</b><br/>Repositorio INIAP"]

    productor -- "Describe síntomas y pregunta<br/>(HTTPS, desde el navegador)" --> sistema
    sistema -- "Consultas confirmadas<br/>por el productor" --> tecnico
    sistema -- "Chat Completions + Embeddings<br/>(HTTPS, clave en el backend)" --> llm
    manuales -- "PDF descargados e indexados<br/>(scripts/ingest.py)" --> sistema

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
        web["<b>Interfaz web</b><br/>HTML + CSS + JS sin framework · <i>frontend/</i><br/>Chat mobile-first, fuentes citadas, tarjetas<br/>de diagnóstico y calendario, confirmación"]
        api["<b>API</b> · FastAPI + Pydantic · <i>app/</i><br/>POST /chat (NDJSON) · GET /fuentes · GET /health<br/>POST /consultas/{id}/confirmar|cancelar"]
        indice[("<b>Índice</b> · <i>data/index/</i><br/>175 fragmentos con metadatos<br/>+ embeddings (768 d)")]
        cfg[("<b>Parámetros</b> · <i>config/*.toml</i><br/>umbrales, tabla de síntomas,<br/>calendario, mensajes")]
        consultas[("<b>Consultas confirmadas</b><br/><i>data/consultas/*.jsonl</i>")]
        logs[("<b>Registro</b> · <i>logs/llm.jsonl</i><br/>tokens, tiempos, búsquedas")]
    end

    ingesta["<b>Ingesta</b> (fuera de línea)<br/><i>scripts/ingest.py</i>"]
    gemini["Gemini API<br/>chat + embeddings"]
    groq["Groq API<br/>(respaldo del chat)"]

    productor -- "HTTPS" --> web
    web -- "fetch POST /chat → NDJSON" --> api
    api -- "lee" --> indice
    api -- "lee" --> cfg
    api -- "guarda solo si el<br/>productor confirma" --> consultas
    api -- "escribe" --> logs
    api -- "chat (streaming) y<br/>embedding de la pregunta" --> gemini
    api -. "si Gemini falla" .-> groq
    ingesta -- "genera" --> indice
    ingesta -. "embeddings" .-> gemini

    classDef cont fill:#438dd5,color:#fff,stroke:#2e6295
    classDef ext fill:#999,color:#fff,stroke:#6b6b6b
    class web,api,ingesta cont
    class gemini,groq ext
```

## Nivel 3 · Componentes de la API

```mermaid
flowchart LR
    web["Interfaz web"]

    subgraph api["API (FastAPI)"]
        main["<b>app/main.py</b><br/>Rutas · traduce errores<br/>· cancela si el cliente se va"]
        turno["<b>app/asistente.py</b><br/>Turno: buscar → decidir →<br/>agente → verificar"]
        indice["<b>app/rag/indice.py</b><br/>BM25 + embeddings (RRF),<br/>filtros, abstención"]
        texto["<b>app/rag/texto.py</b><br/>raíces en español"]
        prompt["<b>app/services/prompt.py</b><br/>fragmentos delimitados,<br/>neutraliza inyección"]
        herr["<b>app/agente/herramientas.py</b><br/>diagnosticar_sintomas · calendario_labores<br/>· registrar_consulta (Pydantic, deterministas)"]
        citas["<b>app/services/citas.py</b><br/>citas válidas · dosis vs fuente oficial"]
        llm["<b>app/services/llm.py</b><br/>ClienteLLM: reintentos, respaldo,<br/>circuito, streaming con tool calls"]
        params["<b>app/parametros.py</b><br/>config/*.toml"]
    end

    proveedor["Gemini / Groq"]

    web --> main --> turno
    turno --> indice --> texto
    turno --> prompt
    turno -- "≤ 3 vueltas" --> llm --> proveedor
    turno -- "ejecuta lo que pide el modelo" --> herr
    turno --> citas
    herr --> params
    indice --> params

    classDef comp fill:#85bbf0,color:#000,stroke:#5d82a8
    classDef ext fill:#999,color:#fff,stroke:#6b6b6b
    class main,turno,indice,texto,prompt,herr,citas,llm,params comp
    class proveedor ext
```

**Reglas de dependencia:** solo `app/services/llm.py` conoce al proveedor del chat, y solo `app/rag/embeddings.py`
conoce al de embeddings. Las herramientas no llaman al modelo. Los umbrales, tablas y textos fijos viven en `config/`.

## Flujo de una consulta (`POST /chat`)

```mermaid
sequenceDiagram
    autonumber
    actor P as Productor
    participant W as Interfaz web
    participant A as API / Turno
    participant I as Índice
    participant L as ClienteLLM
    participant H as Herramientas

    P->>W: «Las mazorcas tienen manchas cafés y polvo blanco»
    W->>A: POST /chat {mensaje, historial, tema?}
    A->>I: buscar(consulta + nombre técnico, filtro de tema)
    I-->>A: 5 fragmentos · coseno máx. 0,70
    alt coseno < 0,63 y no es pedido de herramienta
        A-->>W: texto de abstención + fin (sin llamar al modelo)
    else hay base
        A->>A: cuarentena de fragmentos sospechosos
        A->>L: generar_stream(system_v4, fragmentos numerados, herramientas)
        L-->>A: tool call diagnosticar_sintomas(sintomas, parte)
        A-->>W: {"tipo":"fuentes"} 
        A->>H: ejecutar (Pydantic + tabla validada)
        H-->>A: moniliasis (alta) · fuentes p. 119, p. 16
        A-->>W: {"tipo":"herramienta"} → tarjeta de diagnóstico
        A->>L: 2.ª vuelta con el resultado (mismo proveedor)
        loop cada trozo
            L-->>A: texto con citas [n]
            A-->>W: {"tipo":"texto"}
        end
        A->>A: verifica citas y dosis contra fuentes oficiales
        A-->>W: {"tipo":"alerta"|"aviso"} si corresponde
        A-->>W: {"tipo":"fin", citadas, proveedor, tokens}
    end
    W->>W: Pinta fuentes citadas, guarda el turno y abre la nube del técnico
    Note over A,W: Sin proveedor antes del primer evento → 503 claro. «Detener» → cancela el flujo y el modelo deja de generar.
```

## Atributos de calidad y cómo se atienden

| Atributo | Mecanismo | Dónde |
| :--- | :--- | :--- |
| Fundamentación (LLM09) | Respuestas solo con fragmentos, cita `[n]` obligatoria, fuentes con página enlazada | `system_v4.md`, `app/asistente.py`, `frontend/app.js` |
| Abstención | Umbral calibrado (código) + prompt; mensaje que orienta al técnico | `config/rag.toml`, `app/rag/indice.py` |
| Seguridad de agroquímicos | Dosis verificadas contra fuentes oficiales; alerta si no aparecen; aviso de registro en Agrocalidad | `app/services/citas.py` |
| Inyección indirecta (LLM01) | Fragmentos delimitados y neutralizados; cuarentena por patrones; documento ajeno no respalda dosis | `app/services/prompt.py`, `config/rag.toml` |
| Agencia excesiva (LLM06) | Herramientas deterministas, ≤ 3 vueltas, argumentos validados, registro solo con confirmación humana | `app/agente/`, `config/agente.toml` |
| Disponibilidad | Reintentos, `Retry-After`, respaldo, interruptor de circuito; búsqueda sigue con BM25 si fallan los embeddings | `app/services/llm.py`, `app/rag/` |
| Consumo excesivo (LLM10) | Mensaje ≤ 1000 caracteres, historial ≤ 10 turnos, 5 fragmentos, `max_tokens`, cancelación con «Detener» | `app/schemas.py`, `config/` |
| Salida insegura (LLM05) | La respuesta se escapa antes de mostrarse; las citas se convierten en botones, no en HTML del modelo | `frontend/app.js` |
| Usabilidad móvil | Mobile-first 360 px, tarjetas plegables, tablas con desplazamiento propio | `frontend/styles.css` |
| Observabilidad | Una línea JSON por llamada y por búsqueda (decisión, coseno, fragmentos), sin texto del usuario | `logs/llm.jsonl` |
