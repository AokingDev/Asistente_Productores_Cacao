# Arquitectura del Sistema y Flujo de Datos

El "Asistente Agrotécnico para Productores de Cacao" utiliza una arquitectura basada en **RAG (Retrieval-Augmented Generation)**. Este enfoque permite que el modelo de lenguaje (LLM) genere respuestas precisas utilizando únicamente nuestra base de conocimiento oficial.

## Diagrama de Arquitectura

```mermaid
graph TD
    subgraph Usuarios
        A[Productor Cacaotero]
    end

    subgraph Frontend
        B[App Móvil/Web <br> Angular + Ionic]
    end

    subgraph Backend
        C[API REST <br> Spring Boot]
    end

    subgraph Base Vectorial
        E[(Base Vectorial <br> Pinecone / ChromaDB)]
    end

    subgraph IA Generativa
        F[Modelo LLM <br> Gemini Flash]
    end

    subgraph Fuentes de Conocimiento
        G[Manuales Oficiales INIAP / MAG]
    end

    %% Ingesta de datos
    G -.->|Genera embeddings| E

    %% Flujo de la consulta
    A -->|1. Envía síntoma| B
    B -->|2. Petición POST| C
    C -->|3. Busca en manuales| E
    E -->|4. Retorna fragmentos| C
    C -->|5. Prompt + Contexto| F
    F -->|6. Respuesta generada| C
    C -->|7. Envía respuesta| B
    B -->|8. Muestra en pantalla| A
```