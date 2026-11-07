"""Límite de peticiones por IP para /chat (misión 7 del taller de despliegue).

Cada pregunta gasta cuota gratuita de Gemini/Groq: sin este límite, una sola persona (o un script) podría agotarla
para todos. Ventana deslizante en memoria: basta porque la app corre con máximo 1 réplica (ADR-020); con varias
réplicas haría falta un almacén compartido (Redis).

LIMITE_POR_MINUTO (variable de entorno): preguntas por minuto por IP. 0 lo apaga. Por defecto 20.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from math import ceil

from fastapi import HTTPException, Request

from app.services.llm import _registrar

MENSAJE = "Hizo muchas preguntas seguidas. Espere un momento e intente de nuevo."


class LimitePorIP:
    def __init__(self, por_minuto: int, ventana_s: float = 60, reloj=time.monotonic):
        self.por_minuto = por_minuto
        self.ventana_s = ventana_s
        self.reloj = reloj
        self._llamadas: dict[str, deque[float]] = {}
        self._candado = threading.Lock()  # /chat corre en varios hilos a la vez

    def espera(self, ip: str) -> float:
        """Registra la petición y devuelve 0 si se permite, o los segundos que faltan para poder preguntar."""
        if self.por_minuto <= 0:
            return 0
        ahora = self.reloj()
        with self._candado:
            # Se olvidan las IP sin actividad reciente: la memoria no crece sin control.
            for otra in [k for k, v in self._llamadas.items() if v[-1] <= ahora - self.ventana_s]:
                del self._llamadas[otra]
            llamadas = self._llamadas.setdefault(ip, deque())
            while llamadas and llamadas[0] <= ahora - self.ventana_s:
                llamadas.popleft()
            if len(llamadas) >= self.por_minuto:
                return llamadas[0] + self.ventana_s - ahora
            llamadas.append(ahora)
            return 0


def ip_cliente(request: Request) -> str:
    """En Azure Container Apps la app está detrás de un proxy (Envoy) que AGREGA la IP real al final de
    X-Forwarded-For. Se usa el último valor: los anteriores los puede inventar el cliente para saltarse el límite."""
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada.strip():
        return reenviada.split(",")[-1].strip()
    return request.client.host if request.client else "desconocida"


_limite = LimitePorIP(int(os.getenv("LIMITE_POR_MINUTO", "20")))


def limitar(request: Request) -> None:
    """Dependencia de FastAPI: responde 429 con Retry-After si la IP se pasó del límite."""
    espera = _limite.espera(ip_cliente(request))
    if espera > 0:
        _registrar(evento="limite_ip", espera_s=round(espera, 1))  # sin la IP: es un dato personal
        raise HTTPException(status_code=429, detail=MENSAJE, headers={"Retry-After": str(ceil(espera))})
