"""Un turno de conversación: buscar → decidir → agente con herramientas → verificar.

Produce eventos (dicts con «tipo») que el endpoint envía como NDJSON y que eval/run_eval.py consume:
    fuentes · herramienta · confirmacion · texto · alerta · aviso · error · fin
"""
from __future__ import annotations

import json
import re
import threading
from typing import Iterator

from app.agente.herramientas import (DiagnosticarSintomas, ErrorHerramienta, PropuestaRegistro, definiciones,
                                     diagnosticar_sintomas, ejecutar)
from app.parametros import cargar, documentos
from app.rag.indice import Busqueda, Indice
from app.rag.texto import contiene_frase, sin_tildes, terminos_contenido
from app.schemas import MAX_HISTORIAL, ChatSolicitud
from app.services import citas
from app.services.llm import ClienteLLM, ErrorLLM, Flujo, _registrar, cargar_prompt
from app.services.prompt import construir_mensajes

MIN_TERMINOS_SIN_CONTEXTO = 6   # un mensaje más corto puede ser un seguimiento («¿y cada cuánto?»)


def consulta_de_busqueda(solicitud: ChatSolicitud) -> str:
    """La pregunta actual; si es corta, se le suma la pregunta anterior del productor para no perder el tema.
    Si nombra un problema de la tabla validada («monilla»), se agrega su nombre técnico: así palabras como
    «litros» o «bomba» no arrastran la búsqueda hacia otros temas (fallo P11 de la 1.ª evaluación)."""
    actual = solicitud.mensaje
    if len(terminos_contenido(actual)) < MIN_TERMINOS_SIN_CONTEXTO:
        previas = [m.content for m in solicitud.historial if m.role == "user"]
        if previas:
            actual = f"{previas[-1]} {actual}"
    plano = sin_tildes(actual)
    nombres = [p["nombre"] for p in cargar("sintomas")["problema"]
               if any(re.search(rf"\b{re.escape(sin_tildes(n))}\b", plano) for n in p.get("nombres_locales", []))]
    return f"{actual} ({'; '.join(nombres)})" if nombres else actual


def en_cuarentena(busqueda: Busqueda) -> list[str]:
    """Saca de los resultados los fragmentos con frases dirigidas al asistente (inyección indirecta)."""
    patrones = [re.compile(p) for p in cargar("rag")["seguridad"]["patrones_inyeccion"]]
    sospechosos = [r for r in busqueda.resultados if any(p.search(sin_tildes(r.fragmento.texto)) for p in patrones)]
    if sospechosos:
        busqueda.resultados = [r for r in busqueda.resultados if r not in sospechosos]
        if not busqueda.resultados and busqueda.decision == "suficiente":
            busqueda.decision, busqueda.motivo = "insuficiente", "solo había fragmentos en cuarentena"
    return [r.fragmento.id for r in sospechosos]


def fuentes_publicas(busqueda: Busqueda) -> list[dict]:
    return [{"n": n, "id": r.fragmento.id, "documento": r.fragmento.documento, "institucion": r.fragmento.institucion,
             "anio": r.fragmento.anio, "seccion": r.fragmento.seccion, "ruta": r.fragmento.ruta,
             "paginas": r.fragmento.paginas, "tema": r.fragmento.tema, "vigencia": r.fragmento.vigencia,
             "url": f"{r.fragmento.url}#page={r.fragmento.pagina}" if r.fragmento.url else None,
             "extracto": r.fragmento.texto[:280], "coseno": round(r.coseno, 3) if r.coseno is not None else None}
            for n, r in enumerate(busqueda.resultados, start=1)]


class Turno:
    def __init__(self, llm: ClienteLLM, indice: Indice):
        self.llm, self.indice = llm, indice
        cfg = cargar("agente")
        self.max_iter = cfg["agente"]["max_iteraciones"]
        self.prompt = cargar_prompt(cfg["agente"]["prompt"])
        self.mensajes_cfg = cfg["mensajes"]
        self.intenciones = cfg["intenciones"]
        self._flujo: Flujo | None = None
        self._cancelado = threading.Event()
        self.busqueda: Busqueda | None = None
        self.cuarentena = 0

    def cancelar(self) -> None:
        """El productor pulsó «Detener»: se corta el flujo activo (se puede llamar desde otro hilo)."""
        self._cancelado.set()
        if self._flujo is not None:
            self._flujo.cancelar()

    # ------------------------------------------------------------------ turno completo
    def responder(self, solicitud: ChatSolicitud) -> Iterator[dict]:
        busqueda = self.indice.buscar(consulta_de_busqueda(solicitud), {"tema": solicitud.tema})
        self.busqueda = busqueda
        cuarentena = en_cuarentena(busqueda)
        self.cuarentena = len(cuarentena)
        if cuarentena:
            _registrar(evento="fragmento_en_cuarentena", fragmentos=cuarentena)
        _registrar(evento="busqueda", modo=busqueda.modo, decision=busqueda.decision, motivo=busqueda.motivo,
                   filtros=busqueda.filtros, mejor_coseno=busqueda.mejor_coseno,
                   fragmentos=[r.fragmento.id for r in busqueda.resultados])

        if busqueda.decision == "insuficiente":
            # Antes de abstenerse: ¿el mensaje es para una herramienta, que no necesita texto de los manuales?
            motivo = self._intencion_de_herramienta(solicitud.mensaje)
            if motivo is None:
                yield from self._abstenerse(busqueda)
                return
            busqueda.decision, busqueda.motivo = "solo_herramientas", f"{busqueda.motivo} · {motivo}"

        yield from self._agente(solicitud, busqueda)

    def _intencion_de_herramienta(self, mensaje: str) -> str | None:
        """Regla determinista (config/agente.toml): síntomas que reconoce la tabla validada, o pedidos de
        calendario o de registro. Si no hay ninguno, el sistema se abstiene sin llamar al modelo."""
        if not diagnosticar_sintomas(DiagnosticarSintomas(sintomas=mensaje)).sin_coincidencias:
            return "síntomas reconocidos por la tabla"
        terminos = terminos_contenido(mensaje)
        for intencion, frases in self.intenciones.items():
            if any(contiene_frase(terminos, f) for f in frases):
                return f"pedido de {intencion}"
        return None

    def _abstenerse(self, busqueda: Busqueda) -> Iterator[dict]:
        yield {"tipo": "fuentes", "fragmentos": [], "modo": busqueda.modo, "decision": busqueda.decision,
               "cuarentena": self.cuarentena}
        yield {"tipo": "texto", "texto": self.mensajes_cfg["abstencion"]}
        yield {"tipo": "fin", "proveedor": None, "modelo": None, "latencia_ms": 0, "tokens_entrada": 0,
               "tokens_salida": 0, "citadas": [], "abstencion": True, "decision": busqueda.decision,
               "motivo": busqueda.motivo, "iteraciones": 0, "herramientas": []}

    # ------------------------------------------------------------------ bucle del agente
    def _agente(self, solicitud: ChatSolicitud, busqueda: Busqueda) -> Iterator[dict]:
        con_fragmentos = busqueda.decision == "suficiente"
        historial = [m.model_dump() for m in solicitud.historial[-MAX_HISTORIAL:]]
        base = construir_mensajes(historial, solicitud.mensaje, busqueda)
        rondas: list[dict] = []          # llamadas a herramientas y sus resultados, por vuelta

        def mensajes_para(proveedor: str) -> list[dict]:
            msgs = list(base)
            for r in rondas:
                llamadas = [{"id": c["id"], "type": "function",
                             "function": {"name": c["nombre"], "arguments": c["argumentos"] or "{}"},
                             # la firma de Gemini solo se le devuelve a Gemini
                             **(c["extra"] if r["proveedor"] == proveedor else {})} for c in r["llamadas"]]
                msgs.append({"role": "assistant", "content": r["texto"] or None, "tool_calls": llamadas})
                msgs += [{"role": "tool", "tool_call_id": c["id"], "content": res} for c, res in zip(r["llamadas"], r["resultados"])]
            return msgs

        texto_total, preferido, usadas = "", None, []
        tokens_in = tokens_out = latencia = 0
        flujo = None
        fuentes_enviadas = False
        iteracion = 0
        try:
            for iteracion in range(1, self.max_iter + 1):
                ultima = iteracion == self.max_iter
                flujo = self.llm.generar_stream(self.prompt, mensajes_para, None if ultima else definiciones(), preferido)
                self._flujo, preferido = flujo, flujo.proveedor
                if not fuentes_enviadas:      # se envían después de abrir el 1.er flujo (si no hay modelo: 503 limpio)
                    yield {"tipo": "fuentes", "fragmentos": fuentes_publicas(busqueda) if con_fragmentos else [],
                           "modo": busqueda.modo, "decision": busqueda.decision, "cuarentena": self.cuarentena}
                    fuentes_enviadas = True
                texto_vuelta = ""
                for t in flujo:
                    texto_vuelta += t
                    yield {"tipo": "texto", "texto": t}
                if self._cancelado.is_set():
                    return
                texto_total += texto_vuelta
                tokens_in += flujo.tokens_entrada or 0
                tokens_out += flujo.tokens_salida or 0
                latencia += flujo.latencia_ms or 0
                if not flujo.llamadas:
                    break
                resultados = []
                for i, c in enumerate(flujo.llamadas):
                    c["id"] = c["id"] or f"llamada_{iteracion}_{i}"
                    try:
                        res = ejecutar(c["nombre"], c["argumentos"] or "{}")
                        usadas.append(c["nombre"])
                        resultados.append(res.model_dump_json())
                        yield {"tipo": "herramienta", "nombre": c["nombre"], "argumentos": _json(c["argumentos"]),
                               "resultado": res.model_dump(mode="json")}
                        if isinstance(res, PropuestaRegistro):
                            yield {"tipo": "confirmacion", "id": res.id, "datos": res.datos.model_dump(mode="json"),
                                   "expira": res.expira}
                    except ErrorHerramienta as e:
                        resultados.append(json.dumps({"error": str(e)}, ensure_ascii=False))
                        _registrar(evento="herramienta_invalida", nombre=c["nombre"], error=str(e)[:200])
                rondas.append({"proveedor": flujo.proveedor, "texto": texto_vuelta, "llamadas": flujo.llamadas,
                               "resultados": resultados})
                if texto_vuelta and not texto_vuelta.endswith("\n"):
                    yield {"tipo": "texto", "texto": "\n\n"}
        except ErrorLLM as e:
            if not fuentes_enviadas:
                raise                     # nada enviado aún: el endpoint responde 503
            yield {"tipo": "error", "mensaje": e.mensaje_usuario}
            return

        # ------------------------------------------------ verificaciones deterministas
        n_frag = len(busqueda.resultados) if con_fragmentos else 0
        validas, invalidas = citas.citas_validas(texto_total, n_frag)
        # Solo cuentan como respaldo los documentos oficiales del catálogo (un documento ajeno o envenenado no
        # puede «respaldar» una dosis: fallo de la 1.ª prueba de inyección) y los resultados de las herramientas.
        oficiales = set(documentos())
        textos_fuente = ([r.fragmento.texto for r in busqueda.resultados if r.fragmento.doc_id in oficiales]
                         + [res for r in rondas for res in r["resultados"]])
        # Las cantidades que escribió el propio productor («me dijeron 3 litros») no son recomendaciones del sistema
        del_productor = {(d.cantidad, d.unidad) for d in citas.extraer_dosis(solicitud.mensaje)}
        no_respaldadas = [d for d in citas.dosis_no_respaldadas(texto_total, textos_fuente)
                          if (d.cantidad, d.unidad) not in del_productor]
        if no_respaldadas:
            _registrar(evento="dosis_no_respaldada", dosis=[f"{d.cantidad} {d.unidad}" for d in no_respaldadas])
            yield {"tipo": "alerta", "mensaje": self.mensajes_cfg["dosis_no_respaldada"],
                   "dosis": [d.texto for d in no_respaldadas]}
        elif citas.menciona_dosis(texto_total):
            yield {"tipo": "aviso", "mensaje": self.mensajes_cfg["advertencia_dosis"]}
        yield {"tipo": "fin", "proveedor": flujo.proveedor if flujo else None, "modelo": flujo.modelo if flujo else None,
               "latencia_ms": latencia, "tokens_entrada": tokens_in, "tokens_salida": tokens_out,
               "citadas": validas, "citas_invalidas": invalidas, "abstencion": False, "decision": busqueda.decision,
               "motivo": busqueda.motivo, "iteraciones": iteracion, "herramientas": usadas}


def _json(texto: str) -> dict | str:
    try:
        return json.loads(texto or "{}")
    except json.JSONDecodeError:
        return texto
