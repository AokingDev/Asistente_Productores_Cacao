"""Verificaciones deterministas sobre la respuesta del modelo (el código dispone):

1. Citas: qué fragmentos [n] citó y si existen.
2. Dosis: toda cantidad de producto (cc, ml, l, g, kg, partes, %) debe aparecer en los fragmentos que
   el sistema le entregó al modelo. Si no aparece, se emite una alerta (indicador del caso: el 100 % de
   las recomendaciones de agroquímicos debe limitarse a la fuente oficial, con cita).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.texto import sin_tildes

_CITA = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
# «2.000» y «1 500» son miles (formato ecuatoriano); «0,5» y «1.5» son decimales.
_NUMERO = r"(\d{1,3}(?:[. ]\d{3})+(?![\d,])|\d+(?:[.,]\d+)?)"
# Una cantidad en contexto de rendimiento o producción no es una dosis de producto.
_CONTEXTO_NO_DOSIS = re.compile(r"(rendimiento|produce|produccion|cosecha|qq|quintal|extrae|pesa|indice)"
                                r"(?:[^.\n]|\.(?=\d)){0,40}$")   # el punto de «2.000» no corta el contexto
_UNIDADES = {
    "cc": "ml", "ml": "ml", "mililitro": "ml", "mililitros": "ml", "centimetros cubicos": "ml",
    "l": "l", "lt": "l", "lts": "l", "litro": "l", "litros": "l",
    "g": "g", "gr": "g", "gramo": "g", "gramos": "g",
    "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogramo": "kg", "kilogramos": "kg",
    "parte": "partes", "partes": "partes", "%": "%", "por ciento": "%",
    "lb": "lb", "libra": "lb", "libras": "lb",
}
_UNIDAD = r"(" + "|".join(sorted(map(re.escape, _UNIDADES), key=len, reverse=True)) + r")(?![a-z])"
_DOSIS = re.compile(_NUMERO + r"\s*" + _UNIDAD, re.I)
# Los manuales escriben «una parte de formol y seis de agua»; el modelo, «1 parte … 6 de agua».
_PALABRAS = {"un": "1", "una": "1", "uno": "1", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6",
             "siete": "7", "ocho": "8", "nueve": "9", "diez": "10", "medio": "0.5", "media": "0.5"}
_PALABRA_DOSIS = re.compile(r"\b(" + "|".join(_PALABRAS) + r")(?=\s+" + _UNIDAD + ")", re.I)


@dataclass(frozen=True)
class Dosis:
    cantidad: str
    unidad: str
    texto: str


def citas(texto: str) -> list[int]:
    """Números de fragmento citados, en orden de aparición y sin repetir."""
    vistos: list[int] = []
    for grupo in _CITA.findall(texto):
        for n in re.split(r"\s*[,;]\s*", grupo):
            if n.isdigit() and int(n) not in vistos:
                vistos.append(int(n))
    return vistos


def citas_validas(texto: str, n_fragmentos: int) -> tuple[list[int], list[int]]:
    todas = citas(texto)
    return [n for n in todas if 1 <= n <= n_fragmentos], [n for n in todas if not 1 <= n <= n_fragmentos]


def extraer_dosis(texto: str) -> list[Dosis]:
    plano = _PALABRA_DOSIS.sub(lambda m: _PALABRAS[m.group(1).lower()], sin_tildes(texto))
    salida = []
    for m in _DOSIS.finditer(plano):
        if _CONTEXTO_NO_DOSIS.search(plano[max(0, m.start() - 60):m.start()]):
            continue
        crudo = m.group(1)
        cantidad = re.sub(r"[. ]", "", crudo) if re.fullmatch(r"\d{1,3}(?:[. ]\d{3})+", crudo) else crudo.replace(",", ".")
        unidad = _UNIDADES[m.group(2).lower()]
        salida.append(Dosis(cantidad.rstrip("0").rstrip(".") if "." in cantidad else cantidad, unidad,
                            plano[max(0, m.start() - 30):m.end() + 10].strip()))
    return salida


def dosis_no_respaldadas(respuesta: str, textos_fuente: list[str]) -> list[Dosis]:
    """Dosis de la respuesta que NO aparecen (misma cantidad y unidad) en ningún texto fuente."""
    respaldadas = {(d.cantidad, d.unidad) for t in textos_fuente for d in extraer_dosis(t)}
    return [d for d in extraer_dosis(respuesta) if (d.cantidad, d.unidad) not in respaldadas]


def menciona_dosis(texto: str) -> bool:
    return bool(extraer_dosis(texto))
