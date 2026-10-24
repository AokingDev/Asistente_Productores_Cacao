"""Compara las versiones del system prompt con las 10 entradas de eval/entradas_prompts.csv
y genera la tabla de docs/05-prompts.md (la que se revisa el viernes).

    python scripts/comparar_prompts.py                         # todas las versiones de app/prompts/
    python scripts/comparar_prompts.py system_v2 system_v3
    python scripts/comparar_prompts.py --salida /tmp/prueba.md # sin tocar docs/

El asistente es conversacional, así que se compara la respuesta de TEXTO del chat (la misma
llamada que hace POST /chat, sin streaming). El script llena respuestas, tokens, tiempo y unas
«señales» automáticas que ayudan a calificar. Las columnas ¿Correcta?, ¿Inventa? y ¿Formato?
las califica EL GRUPO leyendo cada respuesta completa en eval/resultados_prompts.json.
La versión ganadora es la que MENOS inventa, no la que más escribe.
"""
import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.services.llm import ClienteLLM, ErrorLLM, cargar_prompt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("versiones", nargs="*")
ap.add_argument("--salida", default=str(RAIZ / "docs/05-prompts.md"))
a = ap.parse_args()

versiones = a.versiones or sorted(p.stem for p in (RAIZ / "app/prompts").glob("system_v*.md"))
entradas = list(csv.DictReader(open(RAIZ / "eval/entradas_prompts.csv", encoding="utf-8")))
llm = ClienteLLM()
filas = []

# Señales automáticas: NO califican, solo llaman la atención del grupo.
DOSIS = re.compile(r"\d+([.,]\d+)?\s*(cc|ml|mililitros?|l|litros?|g|gr|gramos?|kg|kilos?)\b[^.\n]{0,30}?(\bpor\b|\bcada\b|/)", re.I)
SENALES = {
    "⚠dosis": lambda t: bool(DOSIS.search(t)),
    "técnico": lambda t: bool(re.search(r"t[ée]cnico|MAG|INIAP", t)),
    "pregunta": lambda t: "?" in t,
    "alternativas": lambda t: bool(re.search(r"tambi[ée]n podr[ií]a|alternativa|o bien|puede ser .+ o ", t, re.I)),
}

for v in versiones:
    system = cargar_prompt(v)
    for e in entradas:
        try:
            r = llm.generar_texto(system, [{"role": "user", "content": e["entrada"]}])
            fila = {"version": v, "id": e["id"], "respuesta": r.datos, "palabras": len(r.datos.split()),
                    "tokens": (r.tokens_entrada or 0) + (r.tokens_salida or 0), "ms": r.latencia_ms,
                    "proveedor": r.proveedor, "modelo": r.modelo}
        except ErrorLLM as err:
            fila = {"version": v, "id": e["id"], "respuesta": f"ERROR: {type(err).__name__}", "palabras": 0,
                    "tokens": 0, "ms": 0, "proveedor": "-", "modelo": "-"}
        filas.append(fila)
        print(f"{v} · entrada {e['id']:>2} · {fila['ms']} ms · {fila['palabras']} palabras")

(RAIZ / "eval/resultados_prompts.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")


def corto(texto: str, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", texto.replace("|", "/")).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def senales(texto: str) -> str:
    return " ".join(k for k, f in SENALES.items() if f(texto)) or "—"


cfg = llm.config
md = ["# Comparación de versiones del system prompt\n",
      f"Fecha: {date.today():%d/%m/%Y} · Modelo: {cfg.principal.nombre} / {cfg.principal.modelo} · Respaldo: "
      f"{cfg.respaldo.nombre + ' / ' + cfg.respaldo.modelo if cfg.respaldo else 'ninguno'}\n",
      "Entradas: `eval/entradas_prompts.csv` (7 normales, 2 no procesables, 1 fuera de dominio; tomadas del "
      "levantamiento). Respuestas completas: `eval/resultados_prompts.json`.\n",
      "Califiquen cada respuesta con **Sí / No**. **¿Correcta?** = cumple lo esperado del CSV. **¿Inventa?** = afirma "
      "un dato, producto, dosis o cifra sin respaldo. **¿Formato?** = lenguaje sencillo, breve, deriva al técnico y "
      "respeta las restricciones.\n",
      "Señales automáticas (solo orientan): `⚠dosis` menciona una cantidad por bomba/litro/ha · `técnico` deriva al "
      "MAG/INIAP · `pregunta` pide datos · `alternativas` ofrece más de una causa.\n"]
for v in versiones:
    md.append(f"\n## {v}\n\n| # | Tipo | Entrada | Respuesta del modelo (inicio) | Señales | ¿Correcta? | ¿Inventa? | ¿Formato? |"
              "\n|---|---|---|---|---|---|---|---|")
    for e in entradas:
        f = next(x for x in filas if x["version"] == v and x["id"] == e["id"])
        md.append(f"| {e['id']} | {e['tipo']} | {corto(e['entrada'], 70)} | {corto(f['respuesta'])} | "
                  f"{senales(f['respuesta'])} |  |  |  |")
    ok = [x for x in filas if x["version"] == v and x["tokens"]]
    if ok:
        md.append(f"\nPromedio: {sum(x['tokens'] for x in ok) // len(ok)} tokens, "
                  f"{sum(x['palabras'] for x in ok) // len(ok)} palabras y {sum(x['ms'] for x in ok) // len(ok)} ms "
                  f"por respuesta · {len(ok)}/{len(entradas)} respondidas.")

md.append("\n## Resumen\n\n| Versión | Correctas (/10) | Inventa (/10) | Formato OK (/10) | Tokens prom. | ms prom. |"
          "\n|---|---|---|---|---|---|")
for v in versiones:
    ok = [x for x in filas if x["version"] == v and x["tokens"]]
    tk = sum(x["tokens"] for x in ok) // len(ok) if ok else 0
    ms = sum(x["ms"] for x in ok) // len(ok) if ok else 0
    md.append(f"| {v} |  |  |  | {tk} | {ms} |")
md.append("\n## Conclusión del grupo\n\n- Versión ganadora: …\n- Por qué (con números de la tabla): …\n"
          "- Qué cambiamos entre versiones y qué efecto tuvo: …\n"
          "- Cadena de pensamiento (v3): ¿mejoró las entradas 1–3 (síntomas)? ¿mostró alternativas en la 3? …\n")
Path(a.salida).write_text("\n".join(md), encoding="utf-8")
print(f"\n✓ Tabla generada en {a.salida} · respuestas completas en eval/resultados_prompts.json")
