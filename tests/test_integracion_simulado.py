"""Prueba de punta a punta contra el proveedor simulado (HTTP real, sin internet)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import servidor_simulado  # noqa: E402

from app.config import Config, Proveedor  # noqa: E402

# Puerto propio para no chocar con un simulador abierto a mano en el 8099
PUERTO = 8098
SIMULADO = Proveedor("simulado", f"http://127.0.0.1:{PUERTO}/v1", "no-se-necesita", "simulado-1")
from app.schemas import RespuestaAsistente  # noqa: E402
from app.services.llm import ClienteLLM  # noqa: E402


def test_json_por_http_con_429_real():
    srv = servidor_simulado.iniciar(puerto=PUERTO, limite=1, ventana=1)
    try:
        cfg = Config(principal=SIMULADO, respaldo=None, timeout_s=5, max_tokens=100, reintentos=4, razonamiento=None)
        llm = ClienteLLM(cfg)
        a = llm.generar_json("sys", "manchas en la mazorca", RespuestaAsistente)
        b = llm.generar_json("sys", "manchas en la mazorca", RespuestaAsistente)   # choca con el límite → espera y reintenta
        assert isinstance(a.datos, RespuestaAsistente) and b.intentos >= 2
    finally:
        srv.shutdown()
        srv.server_close()


def test_stream_por_http_con_429_real_y_tokens():
    srv = servidor_simulado.iniciar(puerto=PUERTO, limite=1, ventana=4)  # el 1.er stream dura ~2 s
    try:
        cfg = Config(principal=SIMULADO, respaldo=None, timeout_s=5, max_tokens=100, reintentos=4, razonamiento=None)
        llm = ClienteLLM(cfg)
        primero = "".join(llm.generar_stream("sys", [{"role": "user", "content": "manchas"}]))
        segundo = llm.generar_stream("sys", [{"role": "user", "content": "manchas"}])  # choca con el límite
        texto = "".join(segundo)
        assert primero == texto == servidor_simulado.TEXTO_SIMULADO
        assert segundo.intentos >= 2 and segundo.tokens_entrada == 42 and segundo.tokens_salida > 0
    finally:
        srv.shutdown()
        srv.server_close()
