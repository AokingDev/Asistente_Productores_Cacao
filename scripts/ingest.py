"""Ingesta reproducible de la base de conocimiento.

    python scripts/ingest.py                    # extrae, limpia, fragmenta, genera embeddings y guarda
    python scripts/ingest.py --sin-embeddings   # solo fragmentos (la búsqueda usará BM25)
    python scripts/ingest.py --revisar          # además escribe data/processed/secciones.md para revisar

Pasos: (1) verifica que los PDF sean los catalogados (SHA-256), (2) extrae cada línea con su fuente
tipográfica, (3) limpia encabezados, pies y guiones de corte, (4) arma secciones según las reglas de
config/fuentes.toml, (5) fragmenta sin cruzar secciones (config/rag.toml), (6) asigna metadatos
(documento, sección, páginas, tema, vigencia, URL), (7) genera embeddings y (8) guarda en data/index/.

Mismos PDF + misma configuración = mismos fragmentos (orden e ids deterministas).
Requiere: pip install -r requirements-ingest.txt
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pymupdf  # noqa: E402

from app.parametros import cargar  # noqa: E402
from app.rag.indice import asignar_temas  # noqa: E402
from scripts.descargar_fuentes import FUENTES, sha256  # noqa: E402

DIR_RAW = RAIZ / "data" / "raw"


# ====================================================================== 1. extracción
@dataclass
class Linea:
    pagina: int
    tipo: str          # cuerpo | notas | practica | marca_practica | modulo | capitulo | seccion | subseccion | clon | aux
    texto: str
    tamano: float
    mitad: int = 0     # 0 = página completa / izquierda, 1 = derecha (Manual 76 tiene dos páginas por hoja)


def limpiar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto)          # ligaduras: «ﬁ» → «fi»
    texto = texto.replace("­", "").replace("´", "").replace("’", "'")
    texto = re.sub(r"^LL\s+", "- ", texto)                  # viñeta del Manual 76
    return re.sub(r"\s+", " ", texto).strip()


def _coincide(regla: dict, fuente: str, tamano: float, negrita: bool, texto: str) -> bool:
    if regla.get("fuente") and regla["fuente"].lower() not in fuente.lower():
        return False
    if not (regla["min"] <= tamano <= regla["max"]):
        return False
    if regla.get("negrita") and not negrita:
        return False
    if regla.get("solo_mayusculas") and not (texto.upper() == texto and re.search(r"[A-ZÁÉÍÓÚÑ]{3}", texto)):
        return False
    if regla.get("texto") and not re.match(regla["texto"], texto, re.I):
        return False
    return True


def extraer_lineas(doc_cfg: dict) -> tuple[list[Linea], dict[int, int]]:
    """Líneas clasificadas por tipo, en orden de lectura, y el módulo de cada página (si aplica)."""
    pdf = pymupdf.open(DIR_RAW / doc_cfg["archivo"])
    ignorar = [re.compile(p) for p in doc_cfg.get("ignorar", [])]
    reglas = doc_cfg.get("titulos", {})
    excluir = set(doc_cfg.get("paginas_excluir", []))
    dos_por_hoja = doc_cfg["estrategia"] == "manual"
    lineas, modulo_de = [], {}

    for n, pagina in enumerate(pdf, start=1):
        if n in excluir:
            continue
        medio = pagina.rect.width / 2
        crudas = []
        por_posicion = doc_cfg.get("orden", "posicion") == "posicion"
        for bloque in pagina.get_text("dict", sort=por_posicion)["blocks"]:
            for l in bloque.get("lines", []):
                spans = [s for s in l["spans"] if s["text"].strip()]
                if not spans:
                    continue
                texto = limpiar(" ".join(s["text"] for s in spans))
                if not texto:
                    continue
                mayor = max(spans, key=lambda s: s["size"])
                negrita = bool(mayor["flags"] & 16) or "bold" in mayor["font"].lower() or "semibo" in mayor["font"].lower()
                mitad = int(l["bbox"][0] >= medio - 5) if dos_por_hoja else 0
                crudas.append((mitad, l["bbox"][1], l["bbox"][0], texto, mayor["font"], round(mayor["size"], 1), negrita))
        if por_posicion:
            crudas.sort(key=lambda c: (c[0], round(c[1]), c[2]))
        vistas = set()
        for mitad, _, _, texto, fuente, tamano, negrita in crudas:
            m = re.match(r"^M[ÓO]DULO (\d+)$", texto)
            if m:
                modulo_de[n] = int(m.group(1))
            if any(p.search(texto) for p in ignorar):
                continue
            if len(texto) > 25 and (mitad, texto) in vistas:      # texto duplicado en capas del PDF
                continue
            vistas.add((mitad, texto))
            tipo = "cuerpo"
            for nombre, regla in reglas.items():
                if _coincide(regla, fuente, tamano, negrita, texto):
                    tipo = nombre
                    break
            if tipo == "cuerpo" and dos_por_hoja and 15.5 <= tamano <= 16.5 and not negrita:
                tipo = "aux"                                   # encabezado corrido del capítulo
            lineas.append(Linea(n, tipo, texto, tamano, mitad))
    return lineas, modulo_de


# ====================================================================== 2. secciones
@dataclass
class Seccion:
    ruta: list[str]
    lineas: list[tuple[str, int]] = field(default_factory=list)   # (texto, página)

    @property
    def titulo(self) -> str:
        return self.ruta[-1]

    def agregar(self, texto: str, pagina: int) -> None:
        self.lineas.append((texto, pagina))


def unir_lineas(lineas: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Une líneas cortadas en párrafos y repara las palabras partidas con guion («necro-» + «sis»).
    Devuelve palabras con su página."""
    palabras: list[tuple[str, int]] = []
    for texto, pagina in lineas:
        for p in texto.split():
            if palabras and palabras[-1][0].endswith("-") and len(palabras[-1][0]) > 2 and p[:1].islower():
                palabras[-1] = (palabras[-1][0][:-1] + p, palabras[-1][1])
            else:
                palabras.append((p, pagina))
    return palabras


def secciones_guia(doc: dict, lineas: list[Linea], modulo_de: dict[int, int], incluir_practicas: bool) -> list[Seccion]:
    secciones: list[Seccion] = []
    modo, practica, general = None, "", ""
    actual: Seccion | None = None
    ultimo_tipo = None

    def modulo(pagina: int) -> str:
        num = modulo_de.get(pagina)
        return f"Módulo {num}: {doc['modulos'][str(num)]}" if num else "Guía"

    def nueva(pagina: int, *titulos: str) -> Seccion:
        s = Seccion([modulo(pagina), *[t for t in titulos if t]])
        secciones.append(s)
        return s

    for l in lineas:
        t = l.tipo
        if t == "modulo":
            modo, practica, general = "intro", "", ""
            actual = nueva(l.pagina, f"Introducción: {l.texto}")
        elif t == "practica":
            practica = f"{practica} {l.texto}".strip() if ultimo_tipo == "practica" else l.texto
            modo, general = "practica", ""
            actual = nueva(l.pagina, f"Práctica: {practica}") if incluir_practicas else None
            if actual is not None and ultimo_tipo == "practica":
                secciones.pop(-2)
        elif t == "marca_practica":
            modo = "practica"
        elif t == "notas":
            modo, general = "notas", ""
            actual = nueva(l.pagina, practica or "Notas técnicas")
        elif t == "subseccion" and modo == "notas":
            general = l.texto.capitalize()
            actual = nueva(l.pagina, general)
        elif t == "seccion" and modo in ("notas", "intro"):
            if re.match(r"^(Estructura del m[óo]dulo|Introducci[óo]n)$", l.texto, re.I):
                actual = None if l.texto.lower().startswith("estructura") else actual
            else:
                actual = nueva(l.pagina, general, l.texto)
        elif actual is not None and (modo in ("notas", "intro") or (modo == "practica" and incluir_practicas)):
            actual.agregar(l.texto, l.pagina)
        ultimo_tipo = t
    return secciones


def secciones_manual(doc: dict, lineas: list[Linea]) -> list[Seccion]:
    """Dos páginas impresas por hoja. El capítulo sale del «Contenido temático» impreso
    (config/fuentes.toml) según la página impresa de cada media hoja."""
    conv = doc["pagina_impresa"]
    indice = sorted(doc["capitulos"])

    def capitulo(l: Linea) -> str:
        impresa = conv["factor"] * l.pagina + conv["desfase"] + l.mitad
        return next((t for p, t in reversed(indice) if p <= impresa), indice[0][1])

    secciones: list[Seccion] = []
    actual, previo = None, None
    for l in lineas:
        if l.tipo in ("capitulo", "aux"):
            previo = l.tipo
            continue
        cap = capitulo(l)
        if l.tipo == "seccion":
            if previo == "seccion" and actual is not None and not actual.lineas:
                actual.ruta[-1] = f"{actual.ruta[-1]} {l.texto}"        # título partido en dos líneas
            else:
                actual = Seccion([cap, l.texto.rstrip(".")])
                secciones.append(actual)
        else:
            if actual is None or (len(actual.ruta) == 1 and actual.ruta[0] != cap):
                actual = Seccion([cap])
                secciones.append(actual)
            actual.agregar(l.texto, l.pagina)
        previo = l.tipo
    return secciones


def secciones_catalogo(doc: dict, lineas: list[Linea]) -> list[Seccion]:
    """Introducción por secciones; cada clon en dos fragmentos: características y zonas de adaptación."""
    por_pagina: dict[int, list[Linea]] = {}
    for l in lineas:
        por_pagina.setdefault(l.pagina, []).append(l)
    paginas_clon = {p: next(l.texto for l in ls if l.tipo == "clon") for p, ls in por_pagina.items()
                    if any(l.tipo == "clon" for l in ls)}
    usadas = set(paginas_clon) | {p - 1 for p in paginas_clon} | {p + 1 for p in paginas_clon}
    secciones: list[Seccion] = []

    actual = None
    for p in sorted(por_pagina):
        if p in usadas:
            continue
        for l in por_pagina[p]:
            if l.tipo == "seccion":
                actual = Seccion(["Generalidades", l.texto])
                secciones.append(actual)
            elif actual is not None:
                actual.agregar(l.texto, l.pagina)

    for p, clon in sorted(paginas_clon.items()):
        carac = Seccion(["Clones INIAP", f"Clon {clon}: características, rendimiento y resistencia"])
        zonas = Seccion(["Clones INIAP", f"Clon {clon}: zonas de adaptación"])
        destino = carac
        for l in por_pagina.get(p - 1, []) + por_pagina[p]:
            if l.tipo in ("clon", "seccion"):
                continue
            if re.match(r"^ADAPTABILIDAD", l.texto):
                destino = zonas
            destino.agregar(l.texto, l.pagina)
        carac.lineas.insert(0, (f"Clon {clon}.", p))
        zonas.lineas.insert(0, (f"Zonas donde se adapta el clon {clon}:", p))
        secciones += [carac, zonas]
    return secciones


# ====================================================================== 3. fragmentación
def fragmentar(secciones: list[Seccion], p: dict) -> list[tuple[Seccion, list[tuple[str, int]]]]:
    """Ventanas de hasta `palabras_max` palabras con `solapamiento_palabras` de solape, cortando al final
    de una oración cuando se puede. Una sección corta (< palabras_min) se une a la anterior de la misma
    ruta padre; nunca se cruza de una sección a otra no relacionada."""
    maximo, minimo, solape = p["palabras_max"], p["palabras_min"], p["solapamiento_palabras"]
    salida: list[tuple[Seccion, list[tuple[str, int]]]] = []
    for s in secciones:
        palabras = unir_lineas(s.lineas)
        if not palabras:
            continue
        if len(palabras) < minimo and salida and salida[-1][0].ruta[:-1] == s.ruta[:-1] \
                and len(salida[-1][1]) + len(palabras) <= maximo:
            previa, pal = salida[-1]
            salida[-1] = (previa, pal + [(f"{s.titulo}:", palabras[0][1])] + palabras)
            continue
        if len(palabras) < 15:                                        # restos sin contenido («Fermentación»)
            continue
        inicio = 0
        while inicio < len(palabras):
            fin = min(inicio + maximo, len(palabras))
            if fin < len(palabras):                                   # cortar en un punto si hay uno cerca
                for j in range(fin, inicio + int(maximo * 0.7), -1):
                    if palabras[j - 1][0].endswith((".", ":", ";")):
                        fin = j
                        break
            salida.append((s, palabras[inicio:fin]))
            if fin == len(palabras):
                break
            inicio = max(fin - solape, inicio + 1)
    return salida


# ====================================================================== 4. principal
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sin-embeddings", action="store_true")
    ap.add_argument("--revisar", action="store_true", help="escribe data/processed/secciones.md")
    ap.add_argument("--salida", default=str(RAIZ / "data" / "index"))
    ap.add_argument("--extra", nargs="*", default=[], help="archivos .txt adicionales (pruebas de inyección)")
    a = ap.parse_args()

    fuentes_cfg = cargar("fuentes")
    rag = cargar("rag")
    pfrag = rag["fragmentacion"]

    # 1) verificar archivos
    hashes = {f["archivo"]: f["sha256"] for f in FUENTES}
    docs = fuentes_cfg["documento"]
    for d in docs:
        ruta = DIR_RAW / d["archivo"]
        if not ruta.exists():
            sys.exit(f"✗ Falta {ruta}. Ejecute: python scripts/descargar_fuentes.py")
        if d["archivo"] in hashes and sha256(ruta) != hashes[d["archivo"]]:
            sys.exit(f"✗ {d['archivo']} no coincide con el SHA-256 catalogado: la fuente cambió; revise su vigencia.")

    # 2-5) extraer, seccionar, fragmentar y anotar metadatos
    registros, revision = [], ["# Secciones extraídas (revisión de la ingesta)\n"]
    for d in docs:
        lineas, modulo_de = extraer_lineas(d)
        if d["estrategia"] == "guia":
            secciones = secciones_guia(d, lineas, modulo_de, pfrag["incluir_practicas_facilitador"])
        elif d["estrategia"] == "manual":
            secciones = secciones_manual(d, lineas)
        else:
            secciones = secciones_catalogo(d, lineas)
        trozos = fragmentar(secciones, pfrag)
        revision.append(f"\n## {d['titulo']} — {len(secciones)} secciones, {len(trozos)} fragmentos\n")
        for s, palabras in trozos:
            texto = " ".join(p for p, _ in palabras)
            paginas = sorted({pg for _, pg in palabras})
            temas = asignar_temas(" ".join(s.ruta), texto)
            registros.append({
                "id": f"{d['id']}-{len([r for r in registros if r['doc_id'] == d['id']]) + 1:04d}",
                "doc_id": d["id"], "documento": d["titulo"], "institucion": d["institucion"], "anio": d["anio"],
                "seccion": s.titulo, "ruta": " > ".join(s.ruta), "paginas": paginas,
                "tema": temas[0], "temas": temas, "vigencia": d["vigencia"], "url": d["url"], "texto": texto,
            })
            revision.append(f"- **{' > '.join(s.ruta)}** (pp. {paginas[0]}-{paginas[-1]}, {len(palabras)} palabras, "
                            f"tema {temas[0]}): {texto[:160]}…")

    for extra in a.extra:                                            # documentos de prueba (inyección)
        texto = Path(extra).read_text(encoding="utf-8")
        registros.append({"id": f"prueba-{Path(extra).stem}", "doc_id": "prueba", "documento": f"Documento de prueba ({Path(extra).name})",
                          "institucion": "Prueba de seguridad", "anio": "2026", "seccion": "Prueba", "ruta": "Prueba",
                          "paginas": [1], "tema": "enfermedades", "temas": ["enfermedades", "plagas"],
                          "vigencia": "Solo para pruebas", "url": "", "texto": " ".join(texto.split())})

    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    with open(salida / "fragmentos.jsonl", "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if a.revisar:
        (RAIZ / "data" / "processed").mkdir(parents=True, exist_ok=True)
        (RAIZ / "data" / "processed" / "secciones.md").write_text("\n".join(revision), encoding="utf-8")

    # 6) embeddings
    modelo, dims = None, None
    ruta_vec = salida / "embeddings.npy"
    if a.sin_embeddings:
        ruta_vec.unlink(missing_ok=True)
    else:
        from app.rag.embeddings import ClienteEmbeddings
        emb = ClienteEmbeddings()
        t0 = time.monotonic()
        textos = [f"{r['documento']} — {r['ruta']}\n{r['texto']}" for r in registros]
        vectores = emb.embeber(textos)
        np.save(ruta_vec, vectores.astype(np.float32))
        modelo, dims = emb.modelo, int(vectores.shape[1])
        print(f"  embeddings: {len(textos)} textos en {time.monotonic() - t0:.1f} s")

    # 7) manifiesto (qué se indexó y con qué parámetros)
    palabras = [len(r["texto"].split()) for r in registros]
    manifiesto = {
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fragmentos": len(registros),
        "palabras": {"min": min(palabras), "max": max(palabras), "promedio": round(sum(palabras) / len(palabras), 1)},
        "por_documento": {d["id"]: sum(r["doc_id"] == d["id"] for r in registros) for d in docs},
        "por_tema": {t: sum(r["tema"] == t for r in registros) for t in sorted({r["tema"] for r in registros})},
        "documentos": {d["id"]: {"archivo": d["archivo"], "sha256": hashes.get(d["archivo"])} for d in docs},
        "fragmentacion": pfrag,
        "embeddings": {"modelo": modelo, "dimensiones": dims} if modelo else None,
    }
    (salida / "manifest.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {len(registros)} fragmentos en {salida} · palabras {manifiesto['palabras']} · {manifiesto['por_documento']}")
    print(f"  temas: {manifiesto['por_tema']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
