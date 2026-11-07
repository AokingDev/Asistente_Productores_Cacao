import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Las pruebas no escriben en el log real (logs/llm.jsonl)
os.environ.setdefault("LLM_LOG_DIR", tempfile.mkdtemp(prefix="llm-logs-"))
# El límite por IP se prueba aparte (test_limite.py); aquí no debe cortar a las demás pruebas
os.environ.setdefault("LIMITE_POR_MINUTO", "0")
