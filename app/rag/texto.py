"""Normalización de texto en español: la usan BM25, la cobertura de la abstención y el diagnóstico.

«Manchas cafés» y «mancha café» deben coincidir: se quitan tildes, se pasa a minúsculas, se
descartan palabras vacías y cada palabra se reduce a su raíz (Snowball en español).
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import snowballstemmer

_stemmer = snowballstemmer.stemmer("spanish")
_PALABRA = re.compile(r"[a-z0-9ñ]+(?:-[a-z0-9]+)*")

# Palabras sin contenido para buscar (artículos, preposiciones, verbos auxiliares y muletillas).
VACIAS = frozenset("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun bajo bien cada cierta
como con contra cual cuales cuando cuanto cuantos cuanta cuantas de del desde donde dos e el
ella ellas ellos en entre era eran es esa esas ese eso esos esta estan estas este esto estos
estoy fue fueron ha hace hacen hacer hacia han hasta hay he la las le les lo los mas me mi mis
mucho muchos muy nada ni no nos nuestra nuestro o otra otras otro otros para pero poco por porque
puede pueden puedo que quien se sea ser si sin sobre solo son su sus tambien tan tanto te tengo
tiene tienen todo todos tu tus un una unas uno unos usted ustedes y ya yo debo deberia quiero
quisiera saber decir dice dicen favor gracias hola buenos buenas dias tardes noches ayuda ayudeme
mio mia esta este estan estaba estaban tener tenia ahora mismo cosa cosas veces vez
""".split())

# Códigos de clones: «EET-103», «EET 103» y «eet103» deben ser la misma palabra.
_CODIGO_CLON = re.compile(r"\b(eetp|eet|ccn|ics|imc|scc|sca)[\s-]?(\d{1,4})\b")


def sin_tildes(texto: str) -> str:
    """Minúsculas, sin tildes y con «ñ» → «n» (en el teléfono muchos escriben «pequenas»)."""
    return "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))


@lru_cache(maxsize=20000)
def raiz(palabra: str) -> str:
    return _stemmer.stemWord(palabra)


def palabras(texto: str) -> list[str]:
    return _PALABRA.findall(_CODIGO_CLON.sub(r"\1\2", sin_tildes(texto)))


def terminos(texto: str, quitar_vacias: bool = True) -> list[str]:
    """Raíces de las palabras con contenido, en orden (con repeticiones)."""
    return [raiz(p) for p in palabras(texto) if not (quitar_vacias and (p in VACIAS or len(p) < 2))]


def terminos_contenido(texto: str) -> set[str]:
    return set(terminos(texto))


def contiene_frase(terminos_texto: set[str], frase: str) -> bool:
    """True si todas las palabras con contenido de `frase` están en el texto (por raíz)."""
    requeridos = terminos(frase)
    return bool(requeridos) and all(t in terminos_texto for t in requeridos)
