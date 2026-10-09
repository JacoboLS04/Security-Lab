# VULNERABLE - snippet minimal para probar la regla opc-python-sql-construccion-manual.

import sqlite3

def buscar(q, estado=""):
    sql = (
        "SELECT id, codigo, solicitante, desarrollador, estado, prioridad, descripcion "
        "FROM tickets WHERE (codigo LIKE '%" + q + "%' "
        "OR solicitante LIKE '%" + q + "%' "
        "OR descripcion LIKE '%" + q + "%')"
    )
    if estado:
        sql += " AND estado = '" + estado + "'"
    return sqlite3.connect("tickets.db").execute(sql).fetchall()