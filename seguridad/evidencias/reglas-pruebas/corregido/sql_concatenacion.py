import sqlite3


def buscar(q, estado=""):
    sql = (
        "SELECT id, codigo, solicitante, desarrollador, estado, prioridad, descripcion "
        "FROM tickets WHERE (codigo LIKE ? OR solicitante LIKE ? OR descripcion LIKE ?)"
    )
    if estado:
        sql += " AND estado = ?"
    params = ["%" + q + "%", "%" + q + "%", "%" + q + "%"]
    if estado:
        params.append(estado)
    return sqlite3.connect("tickets.db").execute(sql, params).fetchall()