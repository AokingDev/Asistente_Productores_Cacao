"""Límite de peticiones por IP en /chat: 429 con Retry-After, sin llamar al modelo."""
from fastapi.testclient import TestClient

from app import limite
from app.limite import LimitePorIP
from app.main import app, obtener_indice, obtener_llm
from tests.dobles import LLMFalso, indice_prueba


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_permite_hasta_el_limite_y_luego_pide_esperar():
    reloj = Reloj()
    lim = LimitePorIP(3, reloj=reloj)
    assert [lim.espera("1.1.1.1") for _ in range(3)] == [0, 0, 0]
    reloj.t += 10
    assert lim.espera("1.1.1.1") == 50          # la primera de la ventana vence en 50 s
    assert lim.espera("2.2.2.2") == 0           # otra IP no se ve afectada


def test_la_ventana_se_desliza_y_olvida_ips_inactivas():
    reloj = Reloj()
    lim = LimitePorIP(1, reloj=reloj)
    assert lim.espera("1.1.1.1") == 0
    assert lim.espera("1.1.1.1") > 0
    reloj.t += 60
    assert lim.espera("2.2.2.2") == 0
    assert "1.1.1.1" not in lim._llamadas       # la memoria no crece sin control
    assert lim.espera("1.1.1.1") == 0


def test_cero_desactiva_el_limite():
    lim = LimitePorIP(0)
    assert all(lim.espera("1.1.1.1") == 0 for _ in range(100))


def test_chat_responde_429_con_retry_after(monkeypatch):
    monkeypatch.setattr(limite, "_limite", LimitePorIP(2))
    llm = LLMFalso([])                           # si el límite falla y llega al modelo, la prueba lo nota
    app.dependency_overrides[obtener_llm] = lambda: llm
    app.dependency_overrides[obtener_indice] = indice_prueba
    try:
        cliente = TestClient(app)
        ip = {"X-Forwarded-For": "1.2.3.4, 203.0.113.9"}
        fuera = {"mensaje": "¿Quién ganó el mundial de fútbol de 2022?"}   # se abstiene sin modelo
        assert [cliente.post("/chat", json=fuera, headers=ip).status_code for _ in range(2)] == [200, 200]
        r = cliente.post("/chat", json=fuera, headers=ip)
        assert r.status_code == 429
        assert int(r.headers["retry-after"]) > 0
        assert "espere" in r.json()["detail"].lower()
        # Cambiar el primer valor de X-Forwarded-For no salta el límite: cuenta el que agrega el proxy
        assert cliente.post("/chat", json=fuera, headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.9"}).status_code == 429
        assert cliente.post("/chat", json=fuera, headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
