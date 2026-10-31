"""Verificación de citas y de dosis (indicador: 100 % de las dosis limitadas a la fuente oficial)."""
from app.services.citas import citas, citas_validas, dosis_no_respaldadas, extraer_dosis

FUENTE = "Se puede realizar una aplicación dirigida de clorpirifos (3cc/l). Pasta: 1 kg de cal mas 5 kg de oxicloruro."


def test_citas_en_orden_y_sin_repetir():
    assert citas("Uno [2]. Dos [1][2]. Tres [3, 4]; cuatro [1; 5]") == [2, 1, 3, 4, 5]


def test_citas_inexistentes_se_detectan():
    assert citas_validas("Dato [1] y [7]", 5) == ([1], [7])


def test_extrae_cantidades_con_distintas_escrituras():
    d = {(x.cantidad, x.unidad) for x in extraer_dosis("3 cc por litro, 0,5 cc/l, 1,5 litros, 2 g, 10 partes, 4 libras")}
    assert d == {("3", "ml"), ("0.5", "ml"), ("1.5", "l"), ("2", "g"), ("10", "partes"), ("4", "lb")}


def test_no_confunde_medidas_que_no_son_dosis():
    assert extraer_dosis("a los 10 a 16 meses, corona de 1 a 1,5 m, 60 mm de riego, 4 a 6 qq/ha") == []


def test_rendimientos_no_son_dosis():
    # falso positivo de la 1.ª corrida de la evaluación (P14 y P15)
    assert extraer_dosis("tiene un rendimiento de 2.000 a 2.500 kg/ha") == []
    assert extraer_dosis("El CCN-51 alcanza un rendimiento de 1 500 a 2 760 kg / ha") == []


def test_miles_con_punto_o_espacio():
    assert [(d.cantidad, d.unidad) for d in extraer_dosis("aplique 1.000 g y luego 2 500 ml")] == [("1000", "g"), ("2500", "ml")]


def test_dosis_de_la_fuente_esta_respaldada():
    assert dosis_no_respaldadas("Aplique clorpirifos 3 cc por litro [2].", [FUENTE]) == []


def test_dosis_inventada_no_esta_respaldada():
    malas = dosis_no_respaldadas("Use 5 litros de glifosato por bomba.", [FUENTE])
    assert [(d.cantidad, d.unidad) for d in malas] == [("5", "l")]


def test_misma_cifra_con_otra_unidad_no_cuenta():
    assert dosis_no_respaldadas("Aplique 3 litros.", [FUENTE])


def test_cantidad_escrita_en_palabras_respalda_la_cifra():
    # falso positivo de la 2.ª corrida (P05): la guía escribe la proporción en palabras
    fuente = "Desinfectar las herramientas con alcohol o formol diluido (una parte de formol y seis de agua)."
    assert dosis_no_respaldadas("Formol diluido: 1 parte de formol y 6 de agua [1].", [fuente]) == []
    assert [(d.cantidad, d.unidad) for d in extraer_dosis("media libra y dos litros")] == [("0.5", "lb"), ("2", "l")]
