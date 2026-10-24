"""Pruebas del streaming del chat con un DOBLE del modelo (sin gastar API)."""
import json
from types import SimpleNamespace as NS

import httpx
import openai
import pytest

from app.config import Config, Proveedor
from app.services.llm import ClienteLLM, FlujoInterrumpido, ProveedorNoDisponible


def trozo(texto=None, uso=None):
    choices = [NS(delta=NS(content=texto))] if texto is not None else []
    return NS(choices=choices, usage=uso)


def flujo(*textos, uso=NS(prompt_tokens=30, completion_tokens=12)):
    """Imita un stream del proveedor: trozos de texto y, al final, uno con el uso de tokens."""
    return [trozo(t) for t in textos] + [trozo(uso=uso)]


def cortado(*textos):
    def gen():
        yield from (trozo(t) for t in textos)
        raise openai.APIConnectionError(request=httpx.Request("POST", "https://x"))
    return gen()


def error_http(clase, codigo, cabeceras=None):
    req = httpx.Request("POST", "https://proveedor.test/v1/chat/completions")
    return clase("simulado", response=httpx.Response(codigo, headers=cabeceras or {}, request=req), body=None)


class Doble:
    def __init__(self, guion):
        self.guion, self.llamadas = list(guion), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.llamadas.append(kw)
        paso = self.guion.pop(0)
        if isinstance(paso, Exception):
            raise paso
        return paso


def cliente(principal, respaldo=None, reintentos=3):
    cfg = Config(principal=Proveedor("a", "u", "k", "modelo-a"),
                 respaldo=Proveedor("b", "u", "k", "modelo-b") if respaldo is not None else None,
                 timeout_s=5, max_tokens=100, reintentos=reintentos, razonamiento=None)
    esperas = []
    c = ClienteLLM(cfg, clientes={"a": principal, **({"b": respaldo} if respaldo else {})}, dormir=esperas.append)
    return c, esperas


def test_stream_entrega_el_texto_y_registra_tokens():
    d = Doble([flujo("Puede ser ", "monilla.")])
    f = cliente(d)[0].generar_stream("sys", [{"role": "user", "content": "manchas"}])
    assert "".join(f) == "Puede ser monilla."
    assert (f.tokens_entrada, f.tokens_salida) == (30, 12) and f.latencia_ms is not None
    assert d.llamadas[0]["stream"] is True and d.llamadas[0]["stream_options"] == {"include_usage": True}


def test_stream_envia_el_system_prompt_primero():
    d = Doble([flujo("ok")])
    list(cliente(d)[0].generar_stream("SOY EL SYSTEM", [{"role": "user", "content": "hola"}]))
    assert d.llamadas[0]["messages"][0] == {"role": "system", "content": "SOY EL SYSTEM"}


def test_stream_salta_trozos_vacios_iniciales():
    d = Doble([[trozo(""), trozo(None), *flujo("Hola")]])
    assert "".join(cliente(d)[0].generar_stream("sys", [])) == "Hola"


def test_stream_429_reintenta_con_retry_after():
    c, esperas = cliente(Doble([error_http(openai.RateLimitError, 429, {"retry-after": "2"}), flujo("ok")]))
    f = c.generar_stream("sys", [])
    assert "".join(f) == "ok" and f.intentos == 2 and 2.0 <= esperas[0] <= 2.5


def test_stream_vacio_se_reintenta():
    c, _ = cliente(Doble([flujo(), flujo("ahora sí")]))
    assert "".join(c.generar_stream("sys", [])) == "ahora sí"


def test_stream_tiempo_agotado_pasa_al_respaldo():
    tiempo = openai.APITimeoutError(request=httpx.Request("POST", "https://x"))
    c, _ = cliente(Doble([tiempo, tiempo, tiempo]), Doble([flujo("desde b")]))
    f = c.generar_stream("sys", [])
    assert f.proveedor == "b" and "".join(f) == "desde b"


def test_stream_todos_caidos_da_error_claro_antes_de_empezar():
    caida = lambda: error_http(openai.InternalServerError, 503)  # noqa: E731
    c, _ = cliente(Doble([caida() for _ in range(3)]), Doble([caida() for _ in range(3)]))
    with pytest.raises(ProveedorNoDisponible):
        c.generar_stream("sys", [])


def test_stream_cortado_a_la_mitad_no_cambia_de_proveedor():
    respaldo = Doble([flujo("no debería usarse")])
    c, _ = cliente(Doble([cortado("Puede ser ")]), respaldo)
    f = c.generar_stream("sys", [])
    recibido = []
    with pytest.raises(FlujoInterrumpido):
        for t in f:
            recibido.append(t)
    assert recibido == ["Puede ser "] and respaldo.llamadas == []


def test_log_no_guarda_el_texto_del_usuario(tmp_path, monkeypatch):
    import app.services.llm as llm
    registros = []
    monkeypatch.setattr(llm, "_registrar", lambda **d: registros.append(d))
    c, _ = cliente(Doble([flujo("ok")]))
    list(c.generar_stream("sys", [{"role": "user", "content": "MI CÉDULA 1712345678"}]))
    assert registros and "1712345678" not in json.dumps(registros)
    assert registros[-1]["evento"] == "ok" and registros[-1]["tokens_entrada"] == 30
