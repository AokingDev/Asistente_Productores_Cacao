"""Herramientas del agente: deterministas, validadas con Pydantic y con fuentes citadas."""
from datetime import date

import pytest

from app.agente.herramientas import (CalendarioLabores, DiagnosticarSintomas, ErrorHerramienta, Pendientes,
                                     PropuestaRegistro, RegistrarConsulta, calendario_labores, definiciones,
                                     diagnosticar_sintomas, ejecutar)


def ids(texto, parte="no_indica"):
    return [a.id for a in diagnosticar_sintomas(DiagnosticarSintomas(sintomas=texto, parte_afectada=parte)).alternativas]


# ------------------------------------------------------------------ diagnosticar_sintomas
@pytest.mark.parametrize("texto, esperado", [
    ("Las mazorcas tienen manchas cafés y ahora les sale como un polvo blanco", "moniliasis"),
    ("Mis árboles tienen ramas gruesas y deformes como escobas", "escoba_bruja"),
    ("Salen frutos raros como zanahoria y chirimoya en los cojines", "escoba_bruja"),
    ("Las mazorcas se ponen negras y duras cuando llueve mucho", "mazorca_negra"),
    ("Las hojas se secan y no se caen de la rama, y hay aserrín en el tronco", "mal_machete"),
    ("Las mazorcas pequenas tienen manchas redondas hundidas y se endurecen", "chinche_monalonion"),
    ("Algo corta las hojas en forma de media luna y hay un hormiguero", "hormiga_arriera"),
    ("Hay bichitos negros en las flores con hormigas", "pulgon"),
    ("En el vivero hay gusanos blancos en la raiz y las plantitas se mueren", "gallina_ciega"),
])
def test_diagnostico_incluye_la_causa_esperada(texto, esperado):
    assert esperado in ids(texto)


def test_diagnostico_muestra_alternativas_cuando_hay_varias_causas():
    r = diagnosticar_sintomas(DiagnosticarSintomas(sintomas="Hojas amarillas que se secan y aserrín en el tronco"))
    assert r.hay_varias and {"mal_machete", "barrenador"} <= {a.id for a in r.alternativas}


def test_diagnostico_cita_documento_y_pagina():
    a = diagnosticar_sintomas(DiagnosticarSintomas(sintomas="manchas y polvo blanco en la mazorca")).alternativas[0]
    assert a.fuentes and all(f.pagina > 0 and f.url and "#page=" in f.url for f in a.fuentes)


def test_diagnostico_sin_coincidencias_no_inventa():
    r = diagnosticar_sintomas(DiagnosticarSintomas(sintomas="mi perro está triste"))
    assert r.sin_coincidencias and r.alternativas == []


def test_parte_afectada_que_no_corresponde_baja_el_puntaje():
    normal = diagnosticar_sintomas(DiagnosticarSintomas(sintomas="polvo blanco y manchas"))
    en_raiz = diagnosticar_sintomas(DiagnosticarSintomas(sintomas="polvo blanco y manchas", parte_afectada="raiz"))
    p1 = next(a.puntaje for a in normal.alternativas if a.id == "moniliasis")
    p2 = next((a.puntaje for a in en_raiz.alternativas if a.id == "moniliasis"), 0)
    assert p2 < p1


def test_diagnostico_es_determinista():
    texto = "manchas cafés con polvo blanco y mazorcas negras"
    assert diagnosticar_sintomas(DiagnosticarSintomas(sintomas=texto)) == diagnosticar_sintomas(DiagnosticarSintomas(sintomas=texto))


# ------------------------------------------------------------------ calendario_labores
def test_calendario_empieza_en_el_mes_de_la_fecha_y_cubre_12_meses():
    r = calendario_labores(CalendarioLabores(etapa="produccion", fecha=date(2026, 10, 28)))
    assert r.desde == "octubre 2026" and r.hasta == "septiembre 2027"
    cosecha = next(l for l in r.labores if l.id == "prod_cosecha")
    assert len(cosecha.meses) == 12 and cosecha.meses[0] == "octubre"


def test_calendario_filtra_por_etapa():
    vivero = {l.id for l in calendario_labores(CalendarioLabores(etapa="vivero", fecha=date(2026, 1, 1))).labores}
    assert vivero and all(i.startswith("vivero_") for i in vivero)


def test_calendario_usa_las_epocas_de_la_region():
    costa = calendario_labores(CalendarioLabores(etapa="produccion", fecha=date(2026, 8, 1), region="costa"))
    amazonia = calendario_labores(CalendarioLabores(etapa="produccion", fecha=date(2026, 8, 1), region="amazonia"))
    poda_c = next(l for l in costa.labores if l.id == "prod_poda_mantenimiento")
    poda_a = next(l for l in amazonia.labores if l.id == "prod_poda_mantenimiento")
    assert "noviembre" in poda_c.meses and "noviembre" not in poda_a.meses   # Amazonía: julio-octubre
    assert poda_a.este_mes is True


def test_fertilizacion_joven_en_enero_marzo_mayo():
    r = calendario_labores(CalendarioLabores(etapa="plantacion_joven", fecha=date(2026, 1, 15)))
    fert = next(l for l in r.labores if l.id == "joven_fertilizacion")
    assert fert.meses == ["enero", "marzo", "mayo"] and fert.este_mes


def test_cada_labor_cita_su_fuente():
    r = calendario_labores(CalendarioLabores(etapa="produccion", fecha=date(2026, 3, 1)))
    assert all(l.fuentes for l in r.labores)


# ------------------------------------------------------------------ registrar_consulta (confirmación humana)
def test_registrar_solo_propone_no_guarda(tmp_path, monkeypatch):
    import app.agente.consultas as consultas
    monkeypatch.setattr(consultas, "ruta_registro", lambda: tmp_path / "c.jsonl")
    r = ejecutar("registrar_consulta", {"resumen": "Manchas con polvo blanco en mazorcas", "provincia": "Los Ríos"})
    assert isinstance(r, PropuestaRegistro) and r.estado == "pendiente_confirmacion"
    assert not (tmp_path / "c.jsonl").exists()


def test_pendientes_entrega_una_sola_vez_y_caduca():
    p = Pendientes(minutos=30, maximo=5)
    prop = p.proponer(RegistrarConsulta(resumen="caso de prueba"))
    assert p.tomar(prop.id).resumen == "caso de prueba" and p.tomar(prop.id) is None
    vencida = Pendientes(minutos=-1, maximo=5).proponer(RegistrarConsulta(resumen="caso viejo"))
    assert Pendientes(minutos=-1, maximo=5).tomar(vencida.id) is None


# ------------------------------------------------------------------ validación de argumentos del modelo
def test_argumentos_invalidos_se_rechazan_sin_ejecutar():
    with pytest.raises(ErrorHerramienta, match="etapa"):
        ejecutar("calendario_labores", '{"etapa": "cosechando", "fecha": "2026-10-28"}')


def test_herramienta_inexistente():
    with pytest.raises(ErrorHerramienta, match="no existe"):
        ejecutar("borrar_base_de_datos", "{}")


def test_campos_extra_se_rechazan():
    with pytest.raises(ErrorHerramienta):
        ejecutar("diagnosticar_sintomas", {"sintomas": "manchas", "dosis": "5 litros"})


def test_definiciones_para_la_api():
    defs = {d["function"]["name"]: d["function"] for d in definiciones()}
    assert set(defs) == {"diagnosticar_sintomas", "calendario_labores", "registrar_consulta"}
    assert defs["calendario_labores"]["parameters"]["properties"]["etapa"]["enum"] == ["vivero", "plantacion_joven", "produccion"]
