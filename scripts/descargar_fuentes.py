"""Descarga los manuales oficiales a data/raw/ y verifica su integridad (SHA-256).

Uso:  python scripts/descargar_fuentes.py
Los PDF no se versionan en Git por su tamaño (ver data/raw/README.md).
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

FUENTES = [
    {
        "archivo": "INIAP_guia_manejo_integrado_cacao.pdf",
        "url": "https://repositorio.iniap.gob.ec/server/api/core/bitstreams/ca109fb0-20aa-4946-82be-5deb55b83a2f/content",
        "sha256": "b9b9957668f37fec3ae2e27eb6af2f392bea3565f46508e3dd5a90c8f19313d7",
    },
    {
        "archivo": "INIAP_manual76_cultivo_cacao_amazonia.pdf",
        "url": "http://canacacao.org/wp-content/uploads/Manual-cultivo-Cacao-Ecuador.pdf",
        "sha256": "b7728f5b3026fd6a3d3d33a4eadf25790258d9b1eed30f1b053267d83b704819",
    },
    {
        "archivo": "INIAP_catalogo_cultivares_cacao.pdf",
        "url": "https://repositorio.iniap.gob.ec/server/api/core/bitstreams/f92da475-087c-49e9-89f7-1770a71a4ff4/content",
        "sha256": "866cf19c0d06c1fdb6348246d01bcaa544a797e20c4d717403755ef6943f937c",
    },
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    errores = 0
    for fuente in FUENTES:
        destino = RAW_DIR / fuente["archivo"]
        if not destino.exists():
            print(f"Descargando {fuente['archivo']} ...")
            urllib.request.urlretrieve(fuente["url"], destino)
        ok = sha256(destino) == fuente["sha256"]
        print(f"  {'OK ' if ok else 'ERR'} {fuente['archivo']}")
        errores += not ok
    if errores:
        print("Hay archivos con hash distinto: la fuente pudo cambiar. Verificar vigencia y actualizar el catálogo.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
