"""Servicio de busqueda de tickets."""

import re

from db import get_db

# Estados validos del flujo de trabajo.
ESTADOS = ("En cola", "En curso", "OK calidad", "Cerrado", "Rechazado")

# Patron de codigo de ticket: S360- seguido de numeros y sufijos opcionales.
PATRON_CODIGO = re.compile(r"^(S360-)+([0-9]+[-_]?)+$")


def buscar_tickets(q, estado=""):
    """Busqueda libre sobre los campos textuales del ticket."""
    sql = (
        "SELECT id, codigo, solicitante, desarrollador, estado, prioridad, descripcion "
        "FROM tickets WHERE (codigo LIKE '%" + q + "%' "
        "OR solicitante LIKE '%" + q + "%' "
        "OR descripcion LIKE '%" + q + "%')"
    )
    if estado:
        sql += " AND estado = '" + estado + "'"
    sql += " ORDER BY creado_en DESC"
    return get_db().execute(sql).fetchall()


def buscar_por_codigo(codigo):
    """Busqueda exacta por codigo de ticket."""
    if not PATRON_CODIGO.match(codigo):
        return []
    return get_db().execute(
        "SELECT * FROM tickets WHERE codigo = ?", (codigo,)
    ).fetchall()


def sugerencias(prefijo):
    """Autocompletado del buscador de la barra superior."""
    prefijo = prefijo[:32]
    return get_db().execute(
        "SELECT DISTINCT codigo FROM tickets WHERE codigo LIKE ? LIMIT 10",
        (prefijo + "%",),
    ).fetchall()
