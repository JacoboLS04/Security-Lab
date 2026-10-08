"""Acceso a la base de datos SQLite del gestor de tickets."""

import sqlite3

from flask import g, current_app

from config import Config


def get_db():
    """Devuelve la conexion asociada al contexto de request."""
    if "db" not in g:
        g.db = sqlite3.connect(Config.DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def cerrar_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    filas = cur.fetchall()
    cur.close()
    if one:
        return filas[0] if filas else None
    return filas


def ejecutar(sql, params=()):
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    ultimo = cur.lastrowid
    cur.close()
    return ultimo


def fila_a_dict(fila):
    return {k: fila[k] for k in fila.keys()} if fila is not None else None


ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE,
    email         TEXT,
    password_hash TEXT,
    rol           TEXT DEFAULT 'usuario',
    api_key       TEXT,
    telefono      TEXT,
    activo        INTEGER DEFAULT 1,
    reset_token   TEXT,
    creado_en     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo        TEXT,
    solicitante   TEXT,
    desarrollador TEXT,
    estado        TEXT,
    prioridad     TEXT DEFAULT 'media',
    descripcion   TEXT,
    notas_internas TEXT,
    owner_id      INTEGER,
    privado       INTEGER DEFAULT 0,
    creado_en     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comentarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER,
    autor      TEXT,
    cuerpo     TEXT,
    creado_en  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS adjuntos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER,
    filename   TEXT,
    ruta       TEXT,
    subido_por TEXT
);

CREATE TABLE IF NOT EXISTS auditoria (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    actor     TEXT,
    accion    TEXT,
    detalle   TEXT,
    ip        TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    """Crea el esquema y carga datos de demo si la base esta vacia."""
    from core.security import hash_password, generar_api_key

    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(ESQUEMA)

    if conn.execute("SELECT COUNT(*) AS c FROM usuarios").fetchone()["c"] == 0:
        usuarios = [
            ("admin", "admin@optiplant.com", hash_password("Optiplant2024!"), "admin", generar_api_key(), "+56911111111"),
            ("vquintero", "v.quintero@optiplant.com", hash_password("valen123"), "desarrollador", generar_api_key(), "+56922222222"),
            ("jgomez", "j.gomez@optiplant.com", hash_password("gomez2024"), "usuario", generar_api_key(), "+56933333333"),
            ("equispe", "e.quispe@optiplant.com", hash_password("quispe1"), "usuario", generar_api_key(), "+56944444444"),
            ("soporte", "soporte@optiplant.com", hash_password("soporte"), "soporte", generar_api_key(), "+56955555555"),
        ]
        conn.executemany(
            "INSERT INTO usuarios (username, email, password_hash, rol, api_key, telefono) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            usuarios,
        )

    if conn.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()["c"] == 0:
        tickets = [
            ("S360-1540", "JOSE GOMEZ", "Valentina Quintero", "En curso", "alta",
             "Falla al cargar el reporte de turno", "Reproducible solo en produccion", 3, 0),
            ("S360-1539", "ELIAN QUISPE", "Valentina Quintero", "OK calidad", "media",
             "Ajuste de columnas en la suite", "", 4, 0),
            ("S360-1533", "ANGIE FERNANDEZ", "Valentina Quintero", "OK calidad", "baja",
             "Correccion de filtro por fecha", "", 4, 0),
            ("S360-1519", "Dariana Salas", "Valentina Quintero", "En cola", "media",
             "Nuevo modulo de exportacion", "", 2, 0),
            ("S360-1476", "ELIAN QUISPE", "Valentina Quintero", "OK calidad", "alta",
             "Revision de permisos de usuario", "", 4, 0),
            ("S360-1471", "GERENCIA", "Valentina Quintero", "En curso", "critica",
             "Incidente de facturacion del cliente Andes",
             "Contiene datos del contrato: clave SFTP andes/An2024!", 1, 1),
            ("S360-1402", "RRHH", "Valentina Quintero", "En cola", "alta",
             "Reporte de remuneraciones", "Planilla con RUT y sueldos", 1, 1),
        ]
        conn.executemany(
            "INSERT INTO tickets (codigo, solicitante, desarrollador, estado, prioridad, "
            "descripcion, notas_internas, owner_id, privado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tickets,
        )

    if conn.execute("SELECT COUNT(*) AS c FROM comentarios").fetchone()["c"] == 0:
        conn.executemany(
            "INSERT INTO comentarios (ticket_id, autor, cuerpo) VALUES (?, ?, ?)",
            [
                (1, "vquintero", "Se replico en el ambiente de QA."),
                (1, "jgomez", "Adjunto captura del error."),
                (2, "vquintero", "Listo para validacion."),
            ],
        )

    conn.commit()
    conn.close()
