"""Índice de fragmentos: búsqueda híbrida (BM25 + embeddings) con filtros por metadatos.

El índice lo genera scripts/ingest.py en data/index/ (se versiona en Git: el despliegue no
necesita los PDF). Si los embeddings no están disponibles, la búsqueda sigue solo con BM25.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.config import RAIZ
from app.parametros import cargar
from app.rag.embeddings import ClienteEmbeddings, EmbeddingsNoDisponibles
from app.rag.texto import terminos, terminos_contenido
from app.services.llm import _registrar


def dir_indice() -> Path:
    return Path(os.getenv("RAG_INDICE") or RAIZ / "data" / "index")


@dataclass
class Fragmento:
    id: str
    doc_id: str
    documento: str
    institucion: str
    seccion: str
    ruta: str
    paginas: list[int]
    tema: str
    temas: list[str]
    vigencia: str
    url: str
    texto: str
    anio: str = ""

    @property
    def pagina(self) -> int:
        return self.paginas[0] if self.paginas else 0

    def cita(self) -> str:
        pags = f"p. {self.paginas[0]}" if len(self.paginas) == 1 else f"pp. {self.paginas[0]}-{self.paginas[-1]}"
        return f"{self.documento}, {self.seccion}, {pags}"


@dataclass
class Resultado:
    fragmento: Fragmento
    puntaje: float                 # puntaje fusionado (RRF)
    coseno: float | None = None    # similitud semántica (None si no hubo embeddings)
    bm25: float = 0.0
    cobertura: float = 0.0         # fracción de términos de la consulta presentes en el fragmento


@dataclass
class Busqueda:
    consulta: str
    resultados: list[Resultado]
    modo: str                      # "hibrida" | "bm25"
    terminos_consulta: int
    decision: str = "suficiente"   # "suficiente" | "insuficiente" | "conversacional"
    motivo: str = ""
    filtros: dict = field(default_factory=dict)

    @property
    def mejor_coseno(self) -> float | None:
        cos = [r.coseno for r in self.resultados if r.coseno is not None]
        return max(cos) if cos else None

    @property
    def mejor_cobertura(self) -> float:
        return max((r.cobertura for r in self.resultados), default=0.0)


class BM25:
    """BM25 Okapi clásico sobre raíces en español (k1=1.5, b=0.75)."""

    def __init__(self, documentos: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in documentos]
        self.largo = [len(d) for d in documentos]
        self.promedio = sum(self.largo) / max(len(self.largo), 1)
        df = Counter(t for d in documentos for t in set(d))
        n = len(documentos)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def puntajes(self, consulta: list[str]) -> np.ndarray:
        s = np.zeros(len(self.tf), dtype=np.float32)
        for t in set(consulta):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, tf in enumerate(self.tf):
                f = tf.get(t)
                if f:
                    s[i] += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.largo[i] / self.promedio))
        return s


class Indice:
    def __init__(self, fragmentos: list[Fragmento], vectores: np.ndarray | None, manifiesto: dict,
                 embeddings: ClienteEmbeddings | None = None, parametros: dict | None = None):
        self.fragmentos = fragmentos
        self.vectores = vectores
        self.manifiesto = manifiesto
        self.p = parametros or cargar("rag")["recuperacion"]
        self._emb = embeddings
        self._terminos = [terminos(f"{f.seccion} {f.texto}") for f in fragmentos]
        self._conjuntos = [set(t) for t in self._terminos]
        self.bm25 = BM25(self._terminos)

    # ---------------------------------------------------------------- carga
    @classmethod
    def cargar(cls, carpeta: Path | None = None, embeddings: ClienteEmbeddings | None = None) -> "Indice":
        carpeta = carpeta or dir_indice()
        if not (carpeta / "fragmentos.jsonl").exists():
            raise FileNotFoundError(f"No hay índice en {carpeta}. Ejecute: python scripts/ingest.py")
        with open(carpeta / "fragmentos.jsonl", encoding="utf-8") as f:
            fragmentos = [Fragmento(**json.loads(linea)) for linea in f if linea.strip()]
        manifiesto = json.loads((carpeta / "manifest.json").read_text(encoding="utf-8"))
        ruta_vec = carpeta / "embeddings.npy"
        vectores = np.load(ruta_vec) if ruta_vec.exists() else None
        if embeddings is None and vectores is not None:
            try:
                embeddings = ClienteEmbeddings()
            except EmbeddingsNoDisponibles:
                embeddings = None
        return cls(fragmentos, vectores, manifiesto, embeddings)

    @property
    def tiene_embeddings(self) -> bool:
        return self.vectores is not None and self._emb is not None

    # ---------------------------------------------------------------- búsqueda
    def _permitidos(self, filtros: dict) -> np.ndarray:
        ok = np.ones(len(self.fragmentos), dtype=bool)
        if filtros.get("tema"):
            ok &= np.array([filtros["tema"] in f.temas for f in self.fragmentos])
        if filtros.get("documento"):
            ok &= np.array([f.doc_id == filtros["documento"] for f in self.fragmentos])
        return ok

    def buscar(self, consulta: str, filtros: dict | None = None, k: int | None = None) -> Busqueda:
        filtros = {c: v for c, v in (filtros or {}).items() if v}
        k = k or self.p["top_k"]
        q_terminos = terminos(consulta)
        q_conjunto = set(q_terminos)
        permitidos = self._permitidos(filtros)
        n_cand = self.p["candidatos"]

        # 1) BM25
        s_bm25 = self.bm25.puntajes(q_terminos)
        s_bm25[~permitidos] = -1
        rank_bm25 = [i for i in np.argsort(-s_bm25)[:n_cand] if s_bm25[i] > 0]

        # 2) Embeddings (si están disponibles)
        cosenos, rank_sem, modo = None, [], "bm25"
        if self.tiene_embeddings:
            try:
                q = self._emb.embeber_consulta(consulta)
                cosenos = self.vectores @ q
                c = np.where(permitidos, cosenos, -1.0)
                rank_sem = list(np.argsort(-c)[:n_cand])
                modo = "hibrida"
            except EmbeddingsNoDisponibles as e:
                _registrar(evento="busqueda_sin_embeddings", motivo=str(e))

        # 3) Fusión por Reciprocal Rank Fusion
        rrf: dict[int, float] = {}
        for lista in (rank_bm25, rank_sem):
            for pos, i in enumerate(lista):
                rrf[int(i)] = rrf.get(int(i), 0.0) + 1.0 / (self.p["rrf_k"] + pos + 1)

        resultados, por_seccion = [], Counter()
        for i in sorted(rrf, key=rrf.get, reverse=True):
            f = self.fragmentos[i]
            clave = (f.doc_id, f.ruta)
            if por_seccion[clave] >= self.p["max_por_seccion"]:
                continue
            por_seccion[clave] += 1
            cobertura = len(q_conjunto & self._conjuntos[i]) / len(q_conjunto) if q_conjunto else 0.0
            resultados.append(Resultado(f, rrf[i], float(cosenos[i]) if cosenos is not None else None,
                                        float(s_bm25[i]), cobertura))
            if len(resultados) == k:
                break

        b = Busqueda(consulta, resultados, modo, len(q_conjunto), filtros=filtros)
        self._decidir(b)
        return b

    def _decidir(self, b: Busqueda) -> None:
        """Abstención determinista: el código decide si hay base para responder (no el modelo)."""
        if b.terminos_consulta < self.p["min_terminos_contenido"]:
            b.decision, b.motivo = "conversacional", "mensaje sin términos de contenido (saludo o pedido vago)"
        elif not b.resultados:
            b.decision, b.motivo = "insuficiente", "ningún fragmento coincide"
        elif b.modo == "hibrida":
            ok = b.mejor_coseno >= self.p["umbral_coseno"]
            b.decision = "suficiente" if ok else "insuficiente"
            b.motivo = f"coseno máximo {b.mejor_coseno:.3f} (umbral {self.p['umbral_coseno']})"
        else:
            ok = b.mejor_cobertura >= self.p["umbral_cobertura"]
            b.decision = "suficiente" if ok else "insuficiente"
            b.motivo = f"cobertura máxima {b.mejor_cobertura:.2f} (umbral {self.p['umbral_cobertura']})"


@lru_cache
def indice_global() -> Indice:
    return Indice.cargar()


def asignar_temas(seccion: str, texto: str, temas_cfg: dict | None = None) -> list[str]:
    """Temas de un fragmento por palabras clave (título pesa 3, texto 1). Lo usa la ingesta."""
    from app.rag.texto import sin_tildes

    temas_cfg = temas_cfg or cargar("rag")["temas"]
    titulo, cuerpo = sin_tildes(seccion), sin_tildes(texto)
    puntos = {}
    for tema, cfg in temas_cfg.items():
        p = sum(3 * titulo.count(c) + cuerpo.count(c) for c in cfg["claves"])
        if p:
            puntos[tema] = p
    if not puntos:
        return ["general"]
    mejor = max(puntos.values())
    return [t for t, p in sorted(puntos.items(), key=lambda x: -x[1]) if p >= max(2, 0.4 * mejor)] or [max(puntos, key=puntos.get)]


def conjunto_terminos(texto: str) -> set[str]:
    return terminos_contenido(texto)
