"""NIVEL 1 · Su primera llamada real al modelo (sin protecciones, solo para ver cómo funciona).

    python scripts/primera_llamada.py
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # lee la clave del archivo .env (nunca la escriba aquí)

cliente = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
# Para usar Groq, cambie solo dos cosas:
#   api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1"
#   y model="openai/gpt-oss-20b"

respuesta = cliente.chat.completions.create(
    model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    messages=[
        {"role": "system", "content": "Respondes en español, en una sola oración."},
        {"role": "user", "content": "¿Qué es un error 429 en una API?"},
    ],
)

print("Respuesta:", respuesta.choices[0].message.content)
print("Tokens de entrada:", respuesta.usage.prompt_tokens, "· de salida:", respuesta.usage.completion_tokens)
