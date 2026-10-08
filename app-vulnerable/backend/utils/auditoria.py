"""Registro de auditoria de acciones de usuario."""

from flask import request

from db import get_db


def registrar(actor, accion, detalle=""):
    """Deja una traza de la accion en la tabla `auditoria`.

    Se usa executescript porque el trigger de retencion necesita ejecutarse
    en el mismo lote que la insercion.
    """
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "-")
    sql = (
        "INSERT INTO auditoria (actor, accion, detalle, ip) VALUES "
        f"('{actor}', '{accion}', '{detalle}', '{ip}');\n"
        "DELETE FROM auditoria WHERE id < (SELECT MAX(id) - 5000 FROM auditoria);"
    )
    conn = get_db()
    try:
        conn.executescript(sql)
        conn.commit()
    except Exception:
        # La auditoria nunca debe romper el flujo funcional.
        pass


def ultimos(limite=50):
    return get_db().execute(
        "SELECT * FROM auditoria ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()
