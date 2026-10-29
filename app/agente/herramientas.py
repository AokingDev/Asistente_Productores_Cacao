"""Herramientas del agente: esquema Pydantic + implementación DETERMINISTA (sin modelo).

El modelo decide cuándo usarlas y con qué argumentos; el código calcula el resultado con las
tablas de config/ (validadas con los manuales, con documento y página). Idea fuerza del curso:
el modelo propone, el código dispone.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.parametros import cargar, documentos, url_pagina
from app.rag.texto import contiene_frase, sin_tildes, terminos_contenido

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FuenteCitada(Estricto):
    documento: str
    pagina: int
    url: str | None


def _fuentes(lista: list[dict]) -> list[FuenteCitada]:
    docs = documentos()
    return [FuenteCitada(documento=docs[f["doc"]]["titulo"], pagina=f["pagina"], url=url_pagina(f["doc"], f["pagina"]))
            for f in lista]


# ====================================================================== diagnosticar_sintomas
class DiagnosticarSintomas(Estricto):
    """Orienta un diagnóstico PRELIMINAR comparando los síntomas descritos con la tabla validada."""
    sintomas: str = Field(min_length=3, max_length=1000,
                          description="Síntomas que describe el productor, con sus propias palabras")
    parte_afectada: Literal["mazorca", "hoja", "rama", "brote", "flor", "tronco", "raiz", "arbol", "no_indica"] = Field(
        default="no_indica", description="Parte de la planta afectada, si el productor la dice")


class Alternativa(Estricto):
    id: str
    nombre: str
    tipo: str
    puntaje: float
    confianza: Literal["alta", "media", "baja"]
    signos_coincidentes: list[str]
    para_confirmar: str
    manejo_cultural: str
    fuentes: list[FuenteCitada]


class ResultadoDiagnostico(Estricto):
    alternativas: list[Alternativa]
    hay_varias: bool = Field(description="True si más de una causa es compatible: mostrarlas todas")
    sin_coincidencias: bool
    advertencia: str


def diagnosticar_sintomas(args: DiagnosticarSintomas, tabla: dict | None = None, p: dict | None = None) -> ResultadoDiagnostico:
    tabla = tabla or cargar("sintomas")
    p = p or cargar("agente")["diagnostico"]
    texto = terminos_contenido(args.sintomas)
    plano = sin_tildes(args.sintomas)
    puntuados = []
    for prob in tabla["problema"]:
        coincidentes, puntaje = [], 0.0
        for signo in prob["signo"]:
            if any(contiene_frase(texto, clave) for clave in signo["claves"]):
                coincidentes.append(signo["texto"])
                puntaje += signo["peso"]
        if any(sin_tildes(n) in plano for n in prob.get("nombres_locales", [])):
            puntaje += p["bonus_nombre_local"]
        if args.parte_afectada != "no_indica" and args.parte_afectada not in prob["partes"]:
            puntaje *= p["penalizacion_parte"]
        if puntaje >= p["umbral_minimo"] and coincidentes:
            puntuados.append((puntaje, prob, coincidentes))

    puntuados.sort(key=lambda x: (-x[0], x[1]["id"]))
    alternativas = []
    if puntuados:
        mejor = puntuados[0][0]
        segundo = puntuados[1][0] if len(puntuados) > 1 else 0
        for i, (puntaje, prob, coinc) in enumerate(puntuados[:p["max_alternativas"]]):
            if puntaje < p["fraccion_alternativas"] * mejor:
                break
            if i == 0 and puntaje >= p["puntaje_confianza_alta"] and puntaje - segundo >= p["margen_confianza_alta"]:
                confianza = "alta"
            elif puntaje >= p["puntaje_confianza_media"]:
                confianza = "media"
            else:
                confianza = "baja"
            alternativas.append(Alternativa(
                id=prob["id"], nombre=prob["nombre"], tipo=prob["tipo"], puntaje=round(puntaje, 2), confianza=confianza,
                signos_coincidentes=coinc, para_confirmar=prob["diferencial"], manejo_cultural=prob["manejo_cultural"],
                fuentes=_fuentes(prob["fuentes"])))
    return ResultadoDiagnostico(
        alternativas=alternativas, hay_varias=len(alternativas) > 1, sin_coincidencias=not alternativas,
        advertencia="Diagnóstico preliminar por síntomas descritos: confírmelo con un técnico del MAG o del INIAP.")


# ====================================================================== calendario_labores
class CalendarioLabores(Estricto):
    """Calendario de labores culturales de los próximos 12 meses según la etapa del cultivo."""
    etapa: Literal["vivero", "plantacion_joven", "produccion"] = Field(
        description="vivero (en fundas), plantacion_joven (hasta 2 años) o produccion (desde el 2.º año)")
    fecha: date = Field(description="Fecha de referencia (AAAA-MM-DD); normalmente hoy")
    region: Literal["costa", "amazonia"] = Field(default="costa", description="Región del cultivo")


class LaborProgramada(Estricto):
    id: str
    labor: str
    frecuencia: str
    descripcion: str
    meses: list[str]
    este_mes: bool
    fuentes: list[FuenteCitada]


class ResultadoCalendario(Estricto):
    etapa: str
    region: str
    desde: str
    hasta: str
    este_mes: str
    labores: list[LaborProgramada]
    nota_region: str
    fuentes_region: list[FuenteCitada]


def calendario_labores(args: CalendarioLabores, cal: dict | None = None) -> ResultadoCalendario:
    cal = cal or cargar("calendario")
    region = cal["regiones"][args.region]
    # 12 meses desde el mes de la fecha de referencia
    meses = [((args.fecha.month - 1 + i) % 12) + 1 for i in range(12)]
    labores = []
    for labor in cal["labor"]:
        if args.etapa not in labor["etapas"]:
            continue
        cuando = labor["cuando"]
        if cuando["tipo"] == "todo_el_anio":
            aplica = set(range(1, 13))
        elif cuando["tipo"] == "meses":
            aplica = set(cuando["meses"])
        elif cuando["tipo"] == "epoca":
            aplica = set(region[cuando["epoca"]])
        else:
            raise ValueError(f"tipo de «cuando» desconocido: {cuando['tipo']}")
        labores.append(LaborProgramada(
            id=labor["id"], labor=labor["nombre"], frecuencia=labor["frecuencia"], descripcion=labor["descripcion"],
            meses=[MESES[m - 1] for m in meses if m in aplica], este_mes=args.fecha.month in aplica,
            fuentes=_fuentes(labor["fuentes"])))
    fin = date(args.fecha.year + (args.fecha.month + 10) // 12, (args.fecha.month + 10) % 12 + 1, 1)
    return ResultadoCalendario(
        etapa=cal["etapas"][args.etapa], region=region["nombre"],
        desde=f"{MESES[args.fecha.month - 1]} {args.fecha.year}", hasta=f"{MESES[fin.month - 1]} {fin.year}",
        este_mes=MESES[args.fecha.month - 1], labores=labores,
        nota_region=region["nota"], fuentes_region=_fuentes(region["fuentes"]))


# ====================================================================== registrar_consulta
class RegistrarConsulta(Estricto):
    """Propone registrar la consulta para seguimiento de un técnico. NO guarda nada: el productor
    debe confirmar en la pantalla (confirmación humana)."""
    resumen: str = Field(min_length=5, max_length=500, description="Resumen de la consulta en una o dos oraciones")
    sintomas: str | None = Field(default=None, max_length=500)
    diagnostico_preliminar: str | None = Field(default=None, max_length=200)
    provincia: str | None = Field(default=None, max_length=60)
    etapa: Literal["vivero", "plantacion_joven", "produccion", "no_indica"] = "no_indica"
    motivo: Literal["seguimiento_tecnico", "registro_personal"] = "seguimiento_tecnico"


class PropuestaRegistro(Estricto):
    id: str
    estado: Literal["pendiente_confirmacion"]
    datos: RegistrarConsulta
    expira: str
    mensaje: str


class Pendientes:
    """Propuestas de registro esperando la confirmación del productor (en memoria, con caducidad)."""

    def __init__(self, minutos: int, maximo: int):
        self.minutos, self.maximo = minutos, maximo
        self._items: dict[str, tuple[datetime, RegistrarConsulta]] = {}

    def proponer(self, datos: RegistrarConsulta) -> PropuestaRegistro:
        self._limpiar()
        if len(self._items) >= self.maximo:
            self._items.pop(next(iter(self._items)))
        ident = uuid.uuid4().hex[:12]
        expira = datetime.now(timezone.utc) + timedelta(minutes=self.minutos)
        self._items[ident] = (expira, datos)
        return PropuestaRegistro(id=ident, estado="pendiente_confirmacion", datos=datos,
                                 expira=expira.isoformat(timespec="seconds"),
                                 mensaje="Se pidió al productor que confirme en pantalla. Aún NO está registrada.")

    def tomar(self, ident: str) -> RegistrarConsulta | None:
        self._limpiar()
        item = self._items.pop(ident, None)
        return item[1] if item else None

    def _limpiar(self) -> None:
        ahora = datetime.now(timezone.utc)
        for k in [k for k, (exp, _) in self._items.items() if exp < ahora]:
            del self._items[k]


_pendientes: Pendientes | None = None


def pendientes() -> Pendientes:
    global _pendientes
    if _pendientes is None:
        c = cargar("agente")["consultas"]
        _pendientes = Pendientes(c["minutos_para_confirmar"], c["max_pendientes"])
    return _pendientes


def registrar_consulta(args: RegistrarConsulta) -> PropuestaRegistro:
    return pendientes().proponer(args)


# ====================================================================== catálogo para el modelo
HERRAMIENTAS = {
    "diagnosticar_sintomas": (DiagnosticarSintomas, diagnosticar_sintomas,
        "Compara los síntomas que describe el productor con la tabla validada de enfermedades y plagas del cacao "
        "(manuales del INIAP) y devuelve las causas compatibles, con su confianza, el dato para confirmar y el manejo "
        "cultural. Úsala SIEMPRE que el productor describa algo que ve en su planta."),
    "calendario_labores": (CalendarioLabores, calendario_labores,
        "Devuelve el calendario de labores culturales de los próximos 12 meses según la etapa del cultivo, la fecha y la "
        "región. Úsala cuando pregunte qué labores hacer, cuándo podar, abonar, regar o cosechar."),
    "registrar_consulta": (RegistrarConsulta, registrar_consulta,
        "Propone registrar la consulta para que un técnico le dé seguimiento. NO registra: el productor debe confirmar "
        "en la pantalla. Úsala solo si el productor pide seguimiento, que lo contacte un técnico o guardar su caso."),
}


def definiciones() -> list[dict]:
    """Herramientas en el formato de la API (JSON Schema generado desde Pydantic)."""
    salida = []
    for nombre, (esquema, _, descripcion) in HERRAMIENTAS.items():
        schema = esquema.model_json_schema()
        schema.pop("title", None)
        schema.pop("description", None)
        salida.append({"type": "function", "function": {"name": nombre, "description": descripcion, "parameters": schema}})
    return salida


class ErrorHerramienta(Exception):
    pass


def ejecutar(nombre: str, argumentos: str | dict) -> BaseModel:
    """Valida los argumentos del modelo con Pydantic y ejecuta la herramienta. Si el modelo pide una
    herramienta que no existe o manda argumentos inválidos, se lanza ErrorHerramienta (se le devuelve el
    error para que corrija; nunca se ejecuta nada sin validar)."""
    if nombre not in HERRAMIENTAS:
        raise ErrorHerramienta(f"La herramienta «{nombre}» no existe.")
    esquema, funcion, _ = HERRAMIENTAS[nombre]
    try:
        args = esquema.model_validate_json(argumentos) if isinstance(argumentos, str) else esquema.model_validate(argumentos)
    except ValidationError as e:
        errores = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
        raise ErrorHerramienta(f"Argumentos inválidos para {nombre}: {errores}") from e
    return funcion(args)
