"""Esquemas (Pydantic) de lo que ENTRA al sistema y de lo que el MODELO debe devolver.

Reglas para que el esquema funcione con el modo estricto de Gemini y Groq:
  - extra="forbid" en cada modelo (no se aceptan campos inventados).
  - Todos los campos son obligatorios; si algo puede faltar, use `tipo | None`.
  - Nada de límites raros en el esquema (minLength, pattern…): esas reglas van en
    validadores de Python. El esquema GUÍA al modelo; la validación la hace su código.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_MENSAJE = 1000   # caracteres por mensaje del productor
MAX_HISTORIAL = 10   # mensajes previos que se reenvían al modelo


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ======================================================================
# ENTRADA · POST /chat
# ======================================================================
class Mensaje(Estricto):
    """Un turno previo de la conversación. Solo se aceptan los roles del usuario y del
    asistente: el rol "system" lo pone el servidor, nunca el cliente."""
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatSolicitud(Estricto):
    """Lo que envía el frontend. Los límites de tamaño son la defensa contra el
    consumo excesivo (OWASP LLM10)."""
    mensaje: str = Field(min_length=2, max_length=MAX_MENSAJE, description="Pregunta del productor")
    historial: list[Mensaje] = Field(default_factory=list, max_length=40,
                                     description="Turnos previos; el servidor usa solo los últimos")

    @field_validator("mensaje")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("el mensaje está vacío")
        return v

    def mensajes_para_modelo(self) -> list[dict]:
        previos = [m.model_dump() for m in self.historial[-MAX_HISTORIAL:]]
        return [*previos, {"role": "user", "content": self.mensaje}]


# ======================================================================
# SALIDA ESTRUCTURADA (scripts/probar_json.py; base de la semana 3)
# ======================================================================
class Fuente(Estricto):
    documento: str
    seccion: str | None


class RespuestaAsistente(Estricto):
    """Respuesta estructurada del asistente. En el chat se usa streaming (texto libre);
    este esquema sirve para verificar la abstención y la derivación, y desde la
    semana 3 llevará las citas de los manuales."""
    respuesta: str
    tipo: Literal["consulta", "diagnostico", "calendario", "dosis", "fuera_de_alcance", "faltan_datos"]
    se_abstiene: bool = Field(description="true si la información no está en sus fuentes o no puede darla")
    datos_faltantes: list[str] = Field(description="Datos de la finca que habría que preguntar; vacía si nada")
    derivar_a: str | None = Field(description="Técnico u oficina a la que debe acudir, si aplica")
    fuentes: list[Fuente] = Field(description="Vacía en la semana 2; con citas desde la semana 3")
