"""Registro de consultas CONFIRMADAS por el productor (archivo JSONL, sin datos de contacto)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.agente.herramientas import RegistrarConsulta
from app.config import RAIZ
from app.parametros import cargar

_candado = threading.Lock()


def ruta_registro() -> Path:
    return RAIZ / cargar("agente")["consultas"]["archivo"]


def guardar(datos: RegistrarConsulta, ruta: Path | None = None) -> str:
    """Guarda la consulta confirmada y devuelve su código (R-0001, R-0002…)."""
    ruta = ruta or ruta_registro()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with _candado:
        n = sum(1 for _ in open(ruta, encoding="utf-8")) + 1 if ruta.exists() else 1
        codigo = f"R-{n:04d}"
        registro = {"codigo": codigo, "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "confirmado_por_productor": True, **datos.model_dump()}
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return codigo
