"""Embeddings con Gemini (API compatible con OpenAI). Si fallan, el RAG sigue solo con BM25.

Los vectores se normalizan (norma 1) para que la similitud coseno sea un producto punto.
"""
from __future__ import annotations

import os
import re
import time
from collections import deque
from functools import lru_cache

import numpy as np
import openai
from openai import OpenAI

from app.config import CATALOGO
from app.parametros import cargar
from app.services.llm import _registrar


class EmbeddingsNoDisponibles(Exception):
    """No hay clave de Gemini o el servicio no respondió."""


class ClienteEmbeddings:
    def __init__(self, cliente: OpenAI | None = None, parametros: dict | None = None):
        self.p = parametros or cargar("rag")["embeddings"]
        clave = os.getenv("GEMINI_API_KEY", "").strip()
        if cliente is None and not clave:
            raise EmbeddingsNoDisponibles("Falta GEMINI_API_KEY: la búsqueda funcionará solo con BM25.")
        self._enviados: deque[tuple[float, int]] = deque()   # (momento, textos) del último minuto
        self._cliente = cliente or OpenAI(api_key=clave, base_url=CATALOGO["gemini"]["base_url"],
                                          timeout=self.p["timeout_s"], max_retries=0)

    @property
    def modelo(self) -> str:
        return self.p["modelo"]

    def embeber(self, textos: list[str]) -> np.ndarray:
        """Matriz (n, dimensiones) normalizada. Reintenta errores pasajeros con espera corta."""
        filas: list[list[float]] = []
        for i in range(0, len(textos), self.p["lote"]):
            lote = textos[i:i + self.p["lote"]]
            self._esperar_cupo(len(lote))
            for intento in range(1, self.p["reintentos"] + 2):
                t0 = time.monotonic()
                try:
                    r = self._cliente.embeddings.create(model=self.modelo, input=lote, dimensions=self.p["dimensiones"])
                    datos = list(r.data)
                    if all(d.index is not None for d in datos):     # Gemini devuelve index=None: se respeta el orden
                        datos.sort(key=lambda d: d.index)
                    if len(datos) != len(lote):
                        raise EmbeddingsNoDisponibles(f"se pidieron {len(lote)} vectores y llegaron {len(datos)}")
                    filas.extend(d.embedding for d in datos)
                    _registrar(evento="embeddings_ok", modelo=self.modelo, textos=len(lote),
                               latencia_ms=int((time.monotonic() - t0) * 1000))
                    break
                except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError,
                        openai.InternalServerError) as e:
                    _registrar(evento="embeddings_reintento", intento=intento, tipo=type(e).__name__)
                    pedida = _espera_pedida(e)
                    if intento > self.p["reintentos"] or (pedida or 0) > 60:
                        raise EmbeddingsNoDisponibles(type(e).__name__) from e
                    time.sleep(pedida + 1 if pedida else min(2 ** intento, 8))
                except openai.APIError as e:
                    _registrar(evento="embeddings_error", tipo=type(e).__name__)
                    raise EmbeddingsNoDisponibles(type(e).__name__) from e
        m = np.asarray(filas, dtype=np.float32)
        return m / np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-12, None)

    def _esperar_cupo(self, n: int) -> None:
        """Respeta el límite de textos por minuto del nivel gratuito (ventana deslizante de 60 s)."""
        limite = self.p.get("textos_por_minuto")
        if not limite:
            return
        while True:
            ahora = time.monotonic()
            while self._enviados and ahora - self._enviados[0][0] > 60:
                self._enviados.popleft()
            usados = sum(c for _, c in self._enviados)
            if usados + n <= limite:
                self._enviados.append((ahora, n))
                return
            time.sleep(60 - (ahora - self._enviados[0][0]) + 0.5)

    @lru_cache(maxsize=512)
    def embeber_consulta(self, texto: str) -> np.ndarray:
        """Una consulta (cacheada: la misma pregunta no gasta cuota dos veces)."""
        return self.embeber([texto])[0]


def _espera_pedida(error: Exception) -> float | None:
    """Segundos que pide esperar el proveedor: cabecera Retry-After o «retry in 18.3s» en el mensaje."""
    respuesta = getattr(error, "response", None)
    valor = respuesta.headers.get("retry-after") if respuesta is not None else None
    if valor:
        try:
            return float(valor)
        except ValueError:
            pass
    m = re.search(r"retry in ([\d.]+)s", str(error))
    return float(m.group(1)) if m else None
