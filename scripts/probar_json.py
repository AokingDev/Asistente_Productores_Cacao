"""NIVEL 2 · Salida en JSON validada con esquema, a través del servicio con reintentos y respaldo.
Sirve para ver cómo el modelo clasifica la consulta y si se abstiene o deriva.

    python scripts/probar_json.py "Las mazorcas tienen manchas cafés y polvo blanco"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import RespuestaAsistente  # noqa: E402
from app.services.llm import ClienteLLM, ErrorLLM, cargar_prompt  # noqa: E402

texto = " ".join(sys.argv[1:]) or "En el almacén me dijeron que le eche 3 litros de fungicida por bomba, ¿está bien?"
try:
    r = ClienteLLM().generar_json(cargar_prompt("system_v3"), texto, RespuestaAsistente)
except ErrorLLM as e:
    sys.exit(f"✗ {e.mensaje_usuario}")
print(r.datos.model_dump_json(indent=2))
print(f"Proveedor: {r.proveedor} · {r.modelo} · {r.latencia_ms} ms · tokens {r.tokens_entrada}+{r.tokens_salida} · intentos {r.intentos}")
