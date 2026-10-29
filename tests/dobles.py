"""Dobles compartidos por las pruebas: un índice pequeño en memoria (solo BM25, sin API) y un modelo
falso que sigue un guion (texto o llamadas a herramientas)."""
from __future__ import annotations

import json

from app.rag.indice import Fragmento, Indice
from app.services.llm import FlujoInterrumpido


def frag(ident, seccion, texto, doc="guia_iniap", paginas=(119,), temas=("enfermedades",)) -> Fragmento:
    return Fragmento(id=ident, doc_id=doc, documento="Guía INIAP de manejo integrado" if doc == "guia_iniap" else "Manual 76",
                     institucion="INIAP", seccion=seccion, ruta=f"Módulo 3 > {seccion}", paginas=list(paginas),
                     tema=temas[0], temas=list(temas), vigencia="Edición 2017", url="https://ejemplo.test/doc.pdf",
                     texto=texto, anio="2015")


FRAGMENTOS = [
    frag("f1", "Moniliasis", "La moniliasis afecta a las mazorcas en cualquier estado. Aparecen manchas pardas y luego una "
         "felpa blanca cremosa de esporas. Control cultural: remoción semanal de mazorcas enfermas."),
    frag("f2", "Chinche de la mazorca", "El chinche causa manchas circulares en mazorcas pequeñas. Bajo buena sombra (25% "
         "de luz solar) disminuye el ataque. Se puede realizar una aplicación dirigida de clorpirifos (3cc/l).",
         paginas=(112,), temas=("plagas",)),
    frag("f3", "Poda de formación", "La poda de formación se realiza cuando los árboles tengan entre 10 a 16 meses de "
         "sembrados; se dejan de tres a cuatro ejes en los clones.", paginas=(101,), temas=("poda",)),
    frag("f4", "Tiempo de fermentación", "Cacao tipo Nacional o sus híbridos, cuatro a cinco días de fermentación. "
         "CCN-51 requiere de cinco hasta seis días.", doc="manual76", paginas=(19,), temas=("poscosecha",)),
    frag("f5", "Clon EET-103", "Clon EET-103. Rendimiento kg/ha: 2.000 a 2.500. Escoba de bruja: susceptible. "
         "Monilla: moderadamente susceptible.", doc="catalogo_cultivares", paginas=(29,), temas=("variedades",)),
]


def indice_prueba(fragmentos=None) -> Indice:
    return Indice(fragmentos or FRAGMENTOS, None, {"creado": "prueba"}, embeddings=None)


def llamada(nombre: str, argumentos: dict, ident: str = "c1", extra: dict | None = None) -> dict:
    return {"id": ident, "nombre": nombre, "argumentos": json.dumps(argumentos, ensure_ascii=False), "extra": extra or {}}


class FlujoFalso:
    def __init__(self, trozos=(), llamadas=None, proveedor="groq", cortar=False):
        self.trozos, self.cortar = list(trozos), cortar
        self.llamadas = llamadas or []
        self.proveedor, self.modelo = proveedor, f"{proveedor}-modelo"
        self.latencia_ms = self.tokens_entrada = self.tokens_salida = None
        self.cancelado = False

    def __iter__(self):
        yield from self.trozos
        if self.cortar:
            raise FlujoInterrumpido()
        self.latencia_ms, self.tokens_entrada, self.tokens_salida = 120, 30, 12

    def cancelar(self):
        self.cancelado = True


class LLMFalso:
    """Imita a ClienteLLM.generar_stream siguiendo un guion de FlujoFalso (uno por vuelta del agente)."""

    def __init__(self, guion=None, error=None):
        self.guion, self.error, self.llamadas = list(guion or []), error, []

    def generar_stream(self, system, mensajes, herramientas=None, preferido=None):
        self.llamadas.append({
            "system": system, "herramientas": herramientas, "preferido": preferido,
            "mensajes": mensajes("groq") if callable(mensajes) else mensajes,
            "mensajes_gemini": mensajes("gemini") if callable(mensajes) else mensajes,
        })
        if self.error:
            raise self.error
        return self.guion.pop(0)
