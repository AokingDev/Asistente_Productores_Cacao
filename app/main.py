"""API del Asistente Agrotécnico para Productores de Cacao.

Ejecutar:  uvicorn app.main:app --reload     y abrir http://127.0.0.1:8000
           (interfaz del chat)  ·  http://127.0.0.1:8000/docs  (documentación de la API)
"""
import json
from functools import lru_cache
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import APP_NOMBRE, APP_VERSION, RAIZ, ErrorConfiguracion, cargar_config
from app.schemas import ChatSolicitud
from app.services.llm import ClienteLLM, ErrorLLM, Flujo, ProveedorNoDisponible, _registrar, cargar_prompt

PROMPT = "system_v3"  # versión ganadora de la comparación (docs/05-prompts.md)

app = FastAPI(
    title=APP_NOMBRE,
    version=APP_VERSION,
    description="Chat de orientación agrotécnica para productores de cacao. "
                "RAG sobre manuales del INIAP y el MAG con citas.",
)


@lru_cache
def obtener_llm() -> ClienteLLM:
    return ClienteLLM()


@app.exception_handler(ErrorConfiguracion)
def falta_configuracion(_: Request, e: ErrorConfiguracion):
    # El detalle (qué variable falta) va al log del servidor, no al productor.
    _registrar(evento="error_configuracion", detalle=str(e))
    return JSONResponse(status_code=503, content={"detail": "El asistente aún no está configurado. Avise al equipo técnico."})


@app.get("/health", tags=["sistema"])
def health():
    """Estado del servicio. Dice qué proveedor está configurado, nunca la clave."""
    try:
        cfg = cargar_config()
        llm = {"principal": cfg.principal.nombre, "respaldo": cfg.respaldo.nombre if cfg.respaldo else None}
    except ErrorConfiguracion:
        llm = None
    return {"estado": "ok", "servicio": APP_NOMBRE, "version": APP_VERSION, "prompt": PROMPT, "llm": llm}


def _evento(**datos) -> str:
    return json.dumps(datos, ensure_ascii=False) + "\n"


async def _eventos(flujo: Flujo) -> AsyncIterator[str]:
    """Convierte el flujo del modelo en eventos NDJSON. Si el navegador se desconecta (el
    productor pulsó «Detener» o cerró la página) se cancela el flujo: sin esto la conexión con
    el proveedor quedaría abierta y el modelo seguiría generando tokens."""
    trozos = iter(flujo)
    termino = False
    try:
        # El SDK del proveedor es síncrono: cada trozo se espera en un hilo aparte.
        while (texto := await run_in_threadpool(next, trozos, None)) is not None:
            yield _evento(tipo="texto", texto=texto)
        termino = True
    except ErrorLLM as e:
        termino = True
        yield _evento(tipo="error", mensaje=e.mensaje_usuario)
        return
    finally:
        if not termino:
            flujo.cancelar()
    yield _evento(tipo="fin", proveedor=flujo.proveedor, modelo=flujo.modelo, latencia_ms=flujo.latencia_ms,
                  tokens_entrada=flujo.tokens_entrada, tokens_salida=flujo.tokens_salida)


@app.post("/chat", tags=["chat"], responses={
    200: {"content": {"application/x-ndjson": {}},
          "description": 'Una línea JSON por evento: {"tipo":"texto"|"fin"|"error", ...}'},
    503: {"description": "Ningún proveedor del modelo respondió"},
})
def chat(solicitud: ChatSolicitud, llm: ClienteLLM = Depends(obtener_llm)):
    """Responde en streaming (NDJSON). El historial lo guarda el navegador y lo reenvía;
    el servidor solo usa los últimos turnos."""
    try:
        flujo = llm.generar_stream(cargar_prompt(PROMPT), solicitud.mensajes_para_modelo())
    except ProveedorNoDisponible as e:
        # Nunca se muestra el error crudo del proveedor: un mensaje claro y un 503.
        raise HTTPException(status_code=503, detail=e.mensaje_usuario)
    return StreamingResponse(_eventos(flujo), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# Interfaz web (al final, para que no tape las rutas de la API)
app.mount("/", StaticFiles(directory=RAIZ / "frontend", html=True), name="frontend")
