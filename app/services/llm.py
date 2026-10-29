"""Servicio de IA: la ÚNICA parte del sistema que habla con el modelo.

Base: kit de integración del seminario (semana 2). Qué resuelve este módulo:
  1. Encapsula al proveedor: los endpoints llaman a ClienteLLM y no saben si detrás
     está Gemini o Groq.
  2. Pide la salida en JSON con un esquema y la VALIDA con Pydantic.
  3. Pone límites: tiempo de espera, máximo de tokens y número de intentos.
  4. Maneja los errores del proveedor: 429 (límite de solicitudes), tiempo agotado,
     caída del servicio y respuesta vacía, con reintentos y espera exponencial.
  5. Si el principal no responde, pasa al proveedor de respaldo.
  6. Deja un registro (log) por solicitud con tokens y tiempo de respuesta.

Adaptación del grupo 9: el chat es conversacional, así que `generar_stream` aplica la
MISMA política de reintentos y respaldo que las llamadas normales (hasta recibir el
primer trozo) y registra tokens y tiempos al terminar el flujo.

Idea fuerza: el modelo propone, el código dispone.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, Iterator, TypeVar

import openai
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import RAIZ, Config, Proveedor, cargar_config

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

# ---------------------------------------------------------------- registro (log)
DIR_LOGS = Path(os.getenv("LLM_LOG_DIR") or RAIZ / "logs")
DIR_LOGS.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("llm")
if not log.handlers:
    log.setLevel(logging.INFO)
    _f = logging.FileHandler(DIR_LOGS / "llm.jsonl", encoding="utf-8")
    _f.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_f)
    _c = logging.StreamHandler()
    _c.setFormatter(logging.Formatter("  [llm] %(message)s"))
    log.addHandler(_c)


def _registrar(**datos) -> None:
    # Nunca se registra el texto del usuario: puede tener datos personales.
    datos = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **datos}
    log.info(json.dumps(datos, ensure_ascii=False))


# ---------------------------------------------------------------- errores propios
class ErrorLLM(Exception):
    """Error que el endpoint puede traducir a un mensaje claro para el usuario."""

    mensaje_usuario = "El asistente no pudo responder. Inténtelo de nuevo."


class ProveedorNoDisponible(ErrorLLM):
    mensaje_usuario = "El asistente no está disponible en este momento. Intente de nuevo en unos minutos."


class SalidaInvalida(ErrorLLM):
    mensaje_usuario = "No pudimos procesar la respuesta automáticamente. Intente con otra pregunta."


class FlujoInterrumpido(ErrorLLM):
    mensaje_usuario = "La respuesta se cortó a la mitad. Vuelva a enviar su pregunta."


class _FalloProveedor(Exception):
    """Interno: este proveedor se rindió; probar con el siguiente."""


class _RespuestaVacia(Exception):
    """El proveedor respondió 200 pero sin contenido."""


# Errores que vale la pena reintentar: son pasajeros.
REINTENTABLES = (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError)
# Errores que NO se arreglan reintentando con el mismo proveedor: clave mala, modelo
# inexistente, solicitud mal formada. Se pasa directo al respaldo.
DEFINITIVOS = (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError, openai.BadRequestError)

ESPERA_MAXIMA_S = 20  # si el proveedor pide esperar más que esto, mejor ir al respaldo


@dataclass
class Resultado(Generic[T]):
    datos: T | str
    proveedor: str
    modelo: str
    tokens_entrada: int | None
    tokens_salida: int | None
    latencia_ms: int
    intentos: int


def espera_exponencial(intento: int, base: float = 1.0) -> float:
    """1 s, 2 s, 4 s… La mitad es fija y la otra mitad al azar ("jitter"),
    para que cien clientes que fallaron juntos no vuelvan a chocar juntos."""
    tope = base * 2 ** (intento - 1)
    return tope / 2 + random.uniform(0, tope / 2)


def _retry_after(error: Exception) -> float | None:
    """Segundos que el proveedor pide esperar (cabecera Retry-After), si los dice."""
    respuesta = getattr(error, "response", None)
    valor = respuesta.headers.get("retry-after") if respuesta is not None else None
    try:
        if valor is not None:
            return float(valor)
    except ValueError:
        pass
    # Gemini no manda la cabecera: lo dice en el mensaje («Please retry in 1h37m10.1s»). Sin leerlo, se
    # reintentaba 3 veces en 4 s y cada intento gastaba una de las 20 solicitudes diarias del plan gratuito.
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m(?!s))?(?:([\d.]+)s)?", _mensaje(error))
    if m and any(m.groups()):
        h, mi, s = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(s or 0)
    return None


def _detalle(error: Exception) -> str | None:
    """Motivo que da el proveedor (p. ej. qué cuota se agotó y de qué modelo), recortado. No incluye texto del usuario.
    Se quita el texto genérico del inicio para que la métrica agotada quepa en el registro."""
    texto = re.sub(r"^You exceeded your current quota.*?(?=\* Quota exceeded)", "", _mensaje(error))
    texto = texto.replace("generativelanguage.googleapis.com/", "")
    return texto[:300] or None


def _mensaje(error: Exception) -> str:
    cuerpo = getattr(error, "body", None)
    if isinstance(cuerpo, list) and cuerpo:
        cuerpo = cuerpo[0]
    if isinstance(cuerpo, dict):
        cuerpo = cuerpo.get("error", cuerpo)
        cuerpo = cuerpo.get("message") if isinstance(cuerpo, dict) else cuerpo
    return " ".join(str(cuerpo or getattr(error, "message", "") or "").split())


def _limpiar_json(texto: str) -> str:
    """Algunos modelos envuelven el JSON en ```json … ```. Se lo quitamos."""
    texto = texto.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", texto, re.S)
    return m.group(1) if m else texto


def _texto_trozo(trozo) -> str:
    return (trozo.choices[0].delta.content or "") if getattr(trozo, "choices", None) else ""


def _llamadas_trozo(trozo) -> list:
    return (getattr(trozo.choices[0].delta, "tool_calls", None) or []) if getattr(trozo, "choices", None) else []


def acumular_llamadas(llamadas: list[dict], deltas: list) -> None:
    """Arma las llamadas a herramientas que llegan en trozos.

    OpenAI/Groq mandan `index` y los argumentos en pedazos; Gemini manda cada llamada completa con
    `index=None` y un campo extra (`extra_content.google.thought_signature`) que hay que devolverle
    tal cual en la siguiente vuelta: sin él responde 400."""
    for d in deltas:
        if d.index is None:
            if d.id and (not llamadas or llamadas[-1]["id"] != d.id):
                llamadas.append({"id": "", "nombre": "", "argumentos": "", "extra": {}})
            if not llamadas:
                llamadas.append({"id": "", "nombre": "", "argumentos": "", "extra": {}})
            actual = llamadas[-1]
        else:
            while len(llamadas) <= d.index:
                llamadas.append({"id": "", "nombre": "", "argumentos": "", "extra": {}})
            actual = llamadas[d.index]
        if d.id:
            actual["id"] = d.id
        f = getattr(d, "function", None)
        if f is not None:
            if f.name:
                actual["nombre"] = f.name
            if f.arguments:
                actual["argumentos"] += f.arguments
        extra = getattr(d, "model_extra", None) or {}
        actual["extra"].update({k: v for k, v in extra.items() if v is not None and k not in ("index", "type")})


class Flujo:
    """Respuesta en streaming ya abierta (el primer trozo ya llegó).

    Se itera para recibir el texto. Al terminar deja tokens y tiempos en sus atributos
    y en logs/llm.jsonl. Si el proveedor corta a la mitad lanza FlujoInterrumpido: a esa
    altura ya no se puede cambiar de proveedor sin repetir texto al usuario.
    """

    def __init__(self, proveedor: Proveedor, primero: str, resto: Iterator, uso, t0: float, intentos: int,
                 cerrar: Callable[[], None] | None = None, llamadas: list[dict] | None = None):
        self.proveedor, self.modelo = proveedor.nombre, proveedor.modelo
        self.intentos = intentos
        self.primer_trozo_ms = int((time.monotonic() - t0) * 1000)
        self.latencia_ms: int | None = None
        self.tokens_entrada: int | None = None
        self.tokens_salida: int | None = None
        self.llamadas: list[dict] = llamadas or []   # herramientas que pidió el modelo (se completan al terminar)
        self._primero, self._resto, self._uso, self._t0 = primero, resto, uso, t0
        self._cerrar = cerrar
        self._cancelado = False

    def _anotar_uso(self, uso) -> None:
        if uso is not None:
            self.tokens_entrada = getattr(uso, "prompt_tokens", None)
            self.tokens_salida = getattr(uso, "completion_tokens", None)

    def cancelar(self) -> None:
        """El usuario pulsó «Detener» o cerró la página. Corta la conexión con el proveedor para
        que deje de generar (y de cobrar) tokens. Se puede llamar desde otro hilo."""
        if self._cancelado or self.latencia_ms is not None:
            return
        self._cancelado = True
        _registrar(evento="stream_cancelado", proveedor=self.proveedor, modelo=self.modelo,
                   latencia_ms=int((time.monotonic() - self._t0) * 1000), tokens_salida=self.tokens_salida)
        if self._cerrar:
            try:
                self._cerrar()
            except Exception:  # noqa: BLE001 — cerrar es un «mejor esfuerzo»
                pass

    def __iter__(self) -> Iterator[str]:
        self._anotar_uso(self._uso)
        try:
            if self._primero:
                yield self._primero
            for trozo in self._resto:
                if self._cancelado:
                    return
                self._anotar_uso(getattr(trozo, "usage", None))
                acumular_llamadas(self.llamadas, _llamadas_trozo(trozo))
                texto = _texto_trozo(trozo)
                if texto:
                    yield texto
        except GeneratorExit:
            self.cancelar()
            raise
        except Exception as e:  # noqa: BLE001
            if self._cancelado:  # la conexión la cerramos nosotros al cancelar
                return
            _registrar(evento="stream_cortado", proveedor=self.proveedor, tipo=type(e).__name__,
                       latencia_ms=int((time.monotonic() - self._t0) * 1000))
            raise FlujoInterrumpido() from e
        if self._cancelado:
            return
        self.latencia_ms = int((time.monotonic() - self._t0) * 1000)
        _registrar(evento="ok", modo="stream", proveedor=self.proveedor, modelo=self.modelo, intento=self.intentos,
                   primer_trozo_ms=self.primer_trozo_ms, latencia_ms=self.latencia_ms,
                   tokens_entrada=self.tokens_entrada, tokens_salida=self.tokens_salida,
                   herramientas=[c["nombre"] for c in self.llamadas] or None)


class ClienteLLM:
    def __init__(self, config: Config | None = None, clientes: dict | None = None,
                 dormir: Callable[[float], None] = time.sleep):
        self.config = config or cargar_config()
        self.proveedores: list[Proveedor] = [p for p in (self.config.principal, self.config.respaldo) if p]
        self.dormir = dormir  # en las pruebas se reemplaza para no esperar de verdad
        self._fallo_hasta: dict[str, float] = {}
        self._clientes = clientes or {
            p.nombre: OpenAI(api_key=p.api_key, base_url=p.base_url,
                             timeout=self.config.timeout_s, max_retries=0)  # los reintentos los hacemos nosotros
            for p in self.proveedores
        }

    # ------------------------------------------------------------ política de reintentos
    def _opciones(self, p: Proveedor, extra: dict) -> dict:
        opciones = {"max_tokens": self.config.max_tokens, **extra}
        if self.config.razonamiento and p.nombre != "simulado":
            opciones["reasoning_effort"] = self.config.razonamiento
        return opciones

    def _con_reintentos(self, p: Proveedor, operacion: Callable[[], R]) -> tuple[R, int]:
        """Ejecuta `operacion` contra el proveedor `p` con reintentos y espera exponencial.
        Devuelve (resultado, intento). Si se rinde, lanza _FalloProveedor."""
        for intento in range(1, self.config.reintentos + 1):
            try:
                return operacion(), intento
            except DEFINITIVOS as e:
                _registrar(evento="error_definitivo", proveedor=p.nombre, modelo=p.modelo, intento=intento,
                           tipo=type(e).__name__, estado_http=getattr(e, "status_code", None), detalle=_detalle(e))
                raise _FalloProveedor() from e
            except openai.APITimeoutError as e:
                # Un tiempo agotado no suele arreglarse esperando: si hay respaldo, se va a él de inmediato
                # (antes se esperaban 3 × LLM_TIMEOUT_S = 90 s con Gemini caído).
                if len(self.proveedores) > 1 and p.nombre != self.proveedores[-1].nombre:
                    _registrar(evento="tiempo_agotado", proveedor=p.nombre, intento=intento, accion="pasa_al_respaldo")
                    raise _FalloProveedor() from e
                _registrar(evento="reintento" if intento < self.config.reintentos else "agotado", proveedor=p.nombre,
                           intento=intento, tipo=type(e).__name__)
                if intento == self.config.reintentos:
                    raise _FalloProveedor() from e
                self.dormir(espera_exponencial(intento))
            except (*REINTENTABLES, _RespuestaVacia) as e:
                pedida = _retry_after(e)
                # Si el proveedor dice cuánto esperar, se respeta y se suma un poco de azar
                espera = pedida + random.uniform(0, 0.5) if pedida is not None else espera_exponencial(intento)
                _registrar(evento="reintento" if intento < self.config.reintentos else "agotado",
                           proveedor=p.nombre, modelo=p.modelo, intento=intento, tipo=type(e).__name__,
                           estado_http=getattr(e, "status_code", None), espera_s=round(espera, 2), detalle=_detalle(e))
                if intento == self.config.reintentos or espera > ESPERA_MAXIMA_S:
                    raise _FalloProveedor() from e
                self.dormir(espera)
        raise _FalloProveedor()

    def _con_respaldo(self, operacion: Callable[[Proveedor], R], preferido: str | None = None) -> R:
        """Prueba los proveedores en orden: primero el `preferido`, luego los que no fallaron hace poco
        (interruptor de circuito: un proveedor que falló pasa al final durante `enfriamiento_s`)."""
        ahora = time.monotonic()
        orden = sorted(self.proveedores, key=lambda p: (p.nombre != preferido if preferido else False,
                                                         self._fallo_hasta.get(p.nombre, 0) > ahora))
        for p in orden:
            try:
                resultado = operacion(p)
                self._fallo_hasta.pop(p.nombre, None)
                return resultado
            except _FalloProveedor:
                if self.config.enfriamiento_s:
                    self._fallo_hasta[p.nombre] = time.monotonic() + self.config.enfriamiento_s
                    _registrar(evento="proveedor_en_espera", proveedor=p.nombre, segundos=self.config.enfriamiento_s)
                continue
        _registrar(evento="sin_proveedor")
        raise ProveedorNoDisponible()

    # ------------------------------------------------------------ llamada normal
    def _llamar(self, p: Proveedor, mensajes: list[dict], extra: dict) -> tuple[object, int, int]:
        cliente = self._clientes[p.nombre]
        opciones = self._opciones(p, extra)

        def una_vez():
            t0 = time.monotonic()
            r = cliente.chat.completions.create(model=p.modelo, messages=mensajes, **opciones)
            contenido = (r.choices[0].message.content or "") if r.choices else ""
            if not contenido.strip():
                raise _RespuestaVacia()
            return r, int((time.monotonic() - t0) * 1000)

        (r, ms), intento = self._con_reintentos(p, una_vez)
        uso = getattr(r, "usage", None)
        _registrar(evento="ok", modo="completo", proveedor=p.nombre, modelo=p.modelo, intento=intento, latencia_ms=ms,
                   tokens_entrada=getattr(uso, "prompt_tokens", None),
                   tokens_salida=getattr(uso, "completion_tokens", None),
                   fin=r.choices[0].finish_reason)
        return r, ms, intento

    def _completar(self, mensajes: list[dict], extra: dict):
        return self._con_respaldo(lambda p: (p, *self._llamar(p, mensajes, extra)))

    # ------------------------------------------------------------ API pública
    def generar_texto(self, system: str, mensajes: list[dict]) -> Resultado[str]:
        """Respuesta de texto libre completa. mensajes = historial."""
        p, r, ms, intentos = self._completar([{"role": "system", "content": system}, *mensajes], {})
        uso = getattr(r, "usage", None)
        return Resultado(r.choices[0].message.content, p.nombre, p.modelo,
                         getattr(uso, "prompt_tokens", None), getattr(uso, "completion_tokens", None), ms, intentos)

    def generar_json(self, system: str, usuario: str, esquema: type[T]) -> Resultado[T]:
        """Pide JSON con un esquema y lo valida. Si no cumple, pide UNA corrección."""
        formato = {"response_format": {"type": "json_schema", "json_schema": {
            "name": esquema.__name__, "strict": True, "schema": esquema.model_json_schema()}}}
        mensajes = [{"role": "system", "content": system}, {"role": "user", "content": usuario}]
        p, r, ms, intentos = self._completar(mensajes, formato)
        texto = r.choices[0].message.content
        try:
            datos = esquema.model_validate_json(_limpiar_json(texto))
        except ValidationError as e:
            _registrar(evento="salida_invalida", proveedor=p.nombre, errores=e.error_count())
            correccion = mensajes + [
                {"role": "assistant", "content": texto},
                {"role": "user", "content": "Tu respuesta no cumple el esquema. Errores:\n"
                    + "\n".join(f"- {'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
                    + "\nDevuelve SOLO el JSON corregido."},
            ]
            p, r, ms2, _ = self._completar(correccion, formato)
            ms += ms2
            try:
                datos = esquema.model_validate_json(_limpiar_json(r.choices[0].message.content))
            except ValidationError as e2:
                _registrar(evento="salida_invalida_final", proveedor=p.nombre, errores=e2.error_count())
                raise SalidaInvalida() from e2
        uso = getattr(r, "usage", None)
        return Resultado(datos, p.nombre, p.modelo, getattr(uso, "prompt_tokens", None),
                         getattr(uso, "completion_tokens", None), ms, intentos)

    def generar_stream(self, system: str, mensajes: list[dict] | Callable[[str], list[dict]],
                       herramientas: list[dict] | None = None, preferido: str | None = None) -> Flujo:
        """Streaming para el chat. Abre el flujo con reintentos y respaldo hasta recibir el primer
        trozo con texto o con una llamada a herramienta; los errores de esa fase se lanzan AQUÍ
        (antes de responderle al navegador), así el endpoint puede devolver un 503 claro.

        `mensajes` puede ser una función proveedor → mensajes: el agente la usa para devolverle a
        cada proveedor solo los campos de sus propias llamadas (p. ej. la firma de Gemini).
        `preferido` pone primero a ese proveedor (todas las vueltas del agente con el mismo)."""

        def abrir(p: Proveedor) -> Flujo:
            cliente = self._clientes[p.nombre]
            extra = {"stream": True, "stream_options": {"include_usage": True}}
            if herramientas:
                extra["tools"] = herramientas
            opciones = self._opciones(p, extra)
            completos = [{"role": "system", "content": system},
                         *(mensajes(p.nombre) if callable(mensajes) else mensajes)]

            def una_vez():
                t0 = time.monotonic()
                crudo = cliente.chat.completions.create(model=p.modelo, messages=completos, **opciones)
                resto = iter(crudo)
                uso, llamadas = None, []
                for trozo in resto:  # los modelos de razonamiento pueden mandar trozos vacíos al inicio
                    uso = getattr(trozo, "usage", None) or uso
                    acumular_llamadas(llamadas, _llamadas_trozo(trozo))
                    texto = _texto_trozo(trozo)
                    if texto or llamadas:
                        return texto, resto, uso, t0, getattr(crudo, "close", None), llamadas
                raise _RespuestaVacia()

            (primero, resto, uso, t0, cerrar, llamadas), intento = self._con_reintentos(p, una_vez)
            return Flujo(p, primero, resto, uso, t0, intento, cerrar, llamadas)

        return self._con_respaldo(abrir, preferido)


def cargar_prompt(nombre: str) -> str:
    """Los prompts viven en archivos versionados, no escondidos en el código."""
    return (Path(__file__).resolve().parent.parent / "prompts" / f"{nombre}.md").read_text(encoding="utf-8")
