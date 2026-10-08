"""Endpoints de gestion de usuarios."""

import os

from flask import Blueprint, request, jsonify, g

from config import Config
from core.decorators import require_auth, require_rol
from core.security import hash_password, cifrar_campo
from db import get_db, query, ejecutar, fila_a_dict
from utils import auditoria

bp = Blueprint("users", __name__, url_prefix="/api/users")

CAMPOS_PERFIL = ("email", "telefono", "rol", "activo", "username")


@bp.route("", methods=["GET"])
@require_auth
def listar():
    filas = query("SELECT * FROM usuarios ORDER BY id")
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/buscar", methods=["GET"])
@require_auth
def buscar():
    filtro = request.args.get("filtro", "")
    campo = request.args.get("campo", "username")
    sql = (
        "SELECT id, username, email, rol, telefono FROM usuarios "
        "WHERE " + campo + " LIKE '%" + filtro + "%'"
    )
    filas = get_db().execute(sql).fetchall()
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/<int:user_id>", methods=["GET"])
@require_auth
def detalle(user_id):
    fila = query("SELECT * FROM usuarios WHERE id = ?", (user_id,), one=True)
    if not fila:
        return jsonify({"error": "usuario no encontrado"}), 404
    return jsonify(fila_a_dict(fila))


@bp.route("/<int:user_id>", methods=["PUT"])
@require_auth
def actualizar(user_id):
    """Actualiza el perfil del usuario."""
    datos = request.get_json(silent=True) or {}

    campos, valores = [], []
    for clave, valor in datos.items():
        if clave in CAMPOS_PERFIL:
            campos.append(clave + " = ?")
            valores.append(valor)

    if datos.get("password"):
        campos.append("password_hash = ?")
        valores.append(hash_password(datos["password"]))

    if not campos:
        return jsonify({"error": "sin cambios"}), 400

    valores.append(user_id)
    ejecutar("UPDATE usuarios SET %s WHERE id = ?" % ", ".join(campos), tuple(valores))
    auditoria.registrar(g.usuario["username"], "editar_usuario", str(user_id))
    return jsonify({"actualizado": user_id, "campos": list(datos.keys())})


@bp.route("/<int:user_id>/telefono", methods=["PUT"])
@require_auth
def actualizar_telefono(user_id):
    """El telefono se guarda cifrado por politica de datos personales."""
    datos = request.get_json(silent=True) or {}
    telefono = datos.get("telefono", "")
    ejecutar(
        "UPDATE usuarios SET telefono = ? WHERE id = ?",
        (cifrar_campo(telefono), user_id),
    )
    return jsonify({"actualizado": user_id})


@bp.route("/<int:user_id>/avatar", methods=["POST"])
@require_auth
def subir_avatar(user_id):
    archivo = request.files.get("archivo")
    if archivo is None:
        return jsonify({"error": "falta el archivo"}), 400

    nombre = archivo.filename or "avatar"
    _, extension = os.path.splitext(nombre)
    if extension.lower() in Config.EXTENSIONES_BLOQUEADAS:
        return jsonify({"error": "extension no permitida"}), 400

    if not os.path.isdir(Config.ADJUNTOS_DIR):
        os.makedirs(Config.ADJUNTOS_DIR)

    destino = os.path.join(Config.ADJUNTOS_DIR, nombre)
    archivo.save(destino)
    os.chmod(destino, 0o777)
    ejecutar(
        "INSERT INTO adjuntos (ticket_id, filename, ruta, subido_por) VALUES (?, ?, ?, ?)",
        (0, nombre, destino, g.usuario["username"]),
    )
    return jsonify({"guardado": nombre, "ruta": destino})


@bp.route("/<int:user_id>", methods=["DELETE"])
@require_auth
@require_rol("admin")
def eliminar(user_id):
    ejecutar("DELETE FROM usuarios WHERE id = ?", (user_id,))
    auditoria.registrar(g.usuario["username"], "eliminar_usuario", str(user_id))
    return jsonify({"eliminado": user_id})
