"""Recuperación (BM25 sin API), filtros por metadatos y decisión de abstención."""
from app.rag.indice import asignar_temas
from app.rag.texto import terminos
from tests.dobles import indice_prueba


def test_encuentra_la_seccion_correcta():
    b = indice_prueba().buscar("¿Cuántos días se fermenta el cacao nacional?")
    assert b.resultados[0].fragmento.id == "f4" and b.decision == "suficiente" and b.modo == "bm25"


def test_filtro_por_tema():
    b = indice_prueba().buscar("manchas en mazorcas pequeñas", {"tema": "plagas"})
    assert b.resultados and all("plagas" in r.fragmento.temas for r in b.resultados)


def test_filtro_por_documento():
    b = indice_prueba().buscar("días de fermentación", {"documento": "guia_iniap"})
    assert all(r.fragmento.doc_id == "guia_iniap" for r in b.resultados)


def test_sin_relacion_se_abstiene():
    b = indice_prueba().buscar("¿Cómo preparo un ceviche de camarón?")
    assert b.decision == "insuficiente"


def test_saludo_es_conversacional():
    assert indice_prueba().buscar("hola, buenos días").decision == "conversacional"


def test_codigos_de_clon_se_normalizan():
    assert terminos("EET 103") == terminos("EET-103") == terminos("eet103")
    assert indice_prueba().buscar("rendimiento del clon EET 103").resultados[0].fragmento.id == "f5"


def test_asignar_temas_por_titulo_y_texto():
    assert asignar_temas("Moniliasis", "remoción de mazorcas enfermas con monilia")[0] == "enfermedades"
    assert asignar_temas("Tiempo de fermentación", "fermentar cuatro días")[0] == "poscosecha"
