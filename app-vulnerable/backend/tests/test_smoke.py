"""Pruebas de humo de la API (funcionalidad basica)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from db import init_db  # noqa: E402


def cliente():
    app.config["TESTING"] = True
    with app.app_context():
        init_db()
    return app.test_client()


def test_health():
    c = cliente()
    assert c.get("/api/health").status_code == 200


def test_login_ok():
    c = cliente()
    r = c.post("/api/auth/login", json={"username": "admin", "password": "Optiplant2024!"})
    assert r.status_code == 200
    assert "token" in r.get_json()


def test_buscar_publico():
    c = cliente()
    assert c.get("/api/tickets/buscar?q=S360").status_code == 200
