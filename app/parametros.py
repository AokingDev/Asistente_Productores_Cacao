"""Parámetros del negocio leídos de config/*.toml (umbrales, tablas, calendarios, mensajes).

Regla del curso: estos valores nunca van en el código ni en el prompt. Se leen una vez y se
cachean; las pruebas pueden pasar otra carpeta con CONFIG_DIR.
"""
from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from app.config import RAIZ


def dir_config() -> Path:
    return Path(os.getenv("CONFIG_DIR") or RAIZ / "config")


@lru_cache
def cargar(nombre: str) -> dict:
    """Lee config/<nombre>.toml. Falla con un mensaje claro si el archivo no existe o está mal escrito."""
    ruta = dir_config() / f"{nombre}.toml"
    try:
        with open(ruta, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"Falta el archivo de configuración {ruta}") from e
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(f"Error de formato en {ruta}: {e}") from e


def documentos() -> dict[str, dict]:
    """Catálogo de documentos por id (config/fuentes.toml)."""
    return {d["id"]: d for d in cargar("fuentes")["documento"]}


def temas() -> dict[str, str]:
    """Temas del filtro de la interfaz: {id: etiqueta}."""
    return {k: v["etiqueta"] for k, v in cargar("rag")["temas"].items()}


def url_pagina(doc_id: str, pagina: int | None) -> str | None:
    """Enlace al PDF abierto en la página citada."""
    doc = documentos().get(doc_id)
    if not doc:
        return None
    return f"{doc['url']}#page={pagina}" if pagina else doc["url"]
