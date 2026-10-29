"""API del Asistente Agrotécnico para Productores de Cacao.

Ejecutar:  uvicorn app.main:app --reload     y abrir http://127.0.0.1:8000
           (interfaz del chat)  ·  http://127.0.0.1:8000/docs  (documentación de la API)
"""
import json
from functools import lru_cache
from typing import AsyncIterator, Iterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.agente import consultas
from app.agente.herramientas import pendientes
from app.asistente import Turno
from app.config import APP_NOMBRE, APP_VERSION, RAIZ, ErrorConfiguracion, cargar_config
from app.parametros import cargar, documentos, temas
from app.rag.indice import Indice, indice_global
from app.schemas import ChatSolicitud
from app.services.llm import ClienteLLM, ProveedorNoDisponible, _registrar

app = FastAPI(
    title=APP_NOMBRE,
    version=APP_VERSION,
    description="Chat de orientación agrotécnica para productores de cacao: RAG con citas sobre manuales del "
                "INIAP y agente con diagnóstico preliminar, calendario de labores y registro con confirmación.",
)


@lru_cache
def obtener_llm() -> ClienteLLM:
    return ClienteLLM()


def obtener_indice() -> Indice:
    return indice_global()


@app.exception_handler(ErrorConfiguracion)
def falta_configuracion(_: Request, e: ErrorConfiguracion):
    # El detalle (qué variable falta) va al log del servidor, no al productor.
    _registrar(evento="error_configuracion", detalle=str(e))
    return JSONResponse(status_code=503, content={"detail": "El asistente aún no está configurado. Avise al equipo técnico."})


@app.get("/health", tags=["sistema"])
def health():
    """Estado del servicio. Dice qué proveedor y qué índice están cargados, nunca las claves."""
    try:
        cfg = cargar_config()
        llm = {"principal": cfg.principal.nombre, "respaldo": cfg.respaldo.nombre if cfg.respaldo else None}
    except ErrorConfiguracion:
        llm = None
    try:
        ind = indice_global()
        indice = {"fragmentos": len(ind.fragmentos), "busqueda": "hibrida" if ind.tiene_embeddings else "bm25",
                  "creado": ind.manifiesto.get("creado")}
    except FileNotFoundError:
        indice = None
    return {"estado": "ok", "servicio": APP_NOMBRE, "version": APP_VERSION,
            "prompt": cargar("agente")["agente"]["prompt"], "llm": llm, "indice": indice}


@app.get("/fuentes", tags=["sistema"])
def fuentes():
    """Documentos de la base de conocimiento y temas para el filtro de la interfaz."""
    return {"documentos": [{"id": d["id"], "titulo": d["titulo"], "institucion": d["institucion"], "anio": d["anio"],
                            "vigencia": d["vigencia"], "url": d["url"], "cita_apa": d["cita_apa"]}
                           for d in documentos().values()],
            "temas": [{"id": k, "etiqueta": v} for k, v in temas().items()]}


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False) + "\n"


async def _ndjson(primero: dict, eventos: Iterator[dict], turno: Turno) -> AsyncIterator[str]:
    """Envía los eventos como NDJSON. Si el navegador se desconecta (el productor pulsó «Detener» o
    cerró la página) se cancela el turno: sin esto el modelo seguiría generando tokens."""
    termino = False
    try:
        yield _linea(primero)
        # El SDK del proveedor es síncrono: cada evento se espera en un hilo aparte.
        while (evento := await run_in_threadpool(next, eventos, None)) is not None:
            yield _linea(evento)
        termino = True
    finally:
        if not termino:
            turno.cancelar()


@app.post("/chat", tags=["chat"], responses={
    200: {"content": {"application/x-ndjson": {}},
          "description": 'Una línea JSON por evento: {"tipo": "fuentes"|"herramienta"|"confirmacion"|"texto"|'
                         '"alerta"|"aviso"|"error"|"fin", ...}'},
    503: {"description": "Ningún proveedor del modelo respondió"},
})
def chat(solicitud: ChatSolicitud, llm: ClienteLLM = Depends(obtener_llm), indice: Indice = Depends(obtener_indice)):
    """Busca en los manuales, decide si hay base para responder y, si la hay, responde con citas usando
    las herramientas del agente. El historial lo guarda el navegador; el servidor usa solo los últimos turnos."""
    turno = Turno(llm, indice)
    eventos = turno.responder(solicitud)
    try:
        primero = next(eventos)
    except ProveedorNoDisponible as e:
        # Nunca se muestra el error crudo del proveedor: un mensaje claro y un 503.
        raise HTTPException(status_code=503, detail=e.mensaje_usuario)
    return StreamingResponse(_ndjson(primero, eventos, turno), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/consultas/{ident}/confirmar", tags=["agente"])
def confirmar_consulta(ident: str):
    """Confirmación humana: SOLO aquí se guarda la consulta que propuso el agente."""
    datos = pendientes().tomar(ident)
    if datos is None:
        raise HTTPException(status_code=404, detail="La propuesta ya no está disponible (pasó el tiempo o ya se respondió). "
                                                    "Pida de nuevo el registro.")
    codigo = consultas.guardar(datos)
    _registrar(evento="consulta_registrada", codigo=codigo, motivo=datos.motivo)
    return {"codigo": codigo, "mensaje": f"Consulta registrada con el código {codigo}. Guárdelo para el seguimiento del técnico."}


@app.post("/consultas/{ident}/cancelar", tags=["agente"])
def cancelar_consulta(ident: str):
    pendientes().tomar(ident)
    return {"mensaje": "No se registró la consulta."}


# Interfaz web (al final, para que no tape las rutas de la API)
app.mount("/", StaticFiles(directory=RAIZ / "frontend", html=True), name="frontend")
