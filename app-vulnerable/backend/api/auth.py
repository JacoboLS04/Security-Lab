"""Endpoints de autenticacion y gestion de credenciales."""

import time
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, redirect, g, make_response

from config import Config
from core.decorators import require_auth
from core.logging_conf import log
from core.security import (
    crear_token,
    generar_api_key,
    generar_token_reset,
    hash_password,
    verificar_password,
)
from db import query, ejecutar, fila_a_dict
from utils import auditoria

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True) or request.form
    username = datos.get("username", "")
    password = datos.get("password", "")

    log.info("Intento de login usuario=%s password=%s ip=%s",
             username, password, request.remote_addr)

    fila = query("SELECT * FROM usuarios WHERE username = ?", (username,), one=True)
    if fila is None:
        return jsonify({"error": "El usuario %s no existe" % username}), 404

    usuario = fila_a_dict(fila)
    if not verificar_password(password, usuario["password_hash"]):
        auditoria.registrar(username, "login_fallido", "password incorrecta")
        return jsonify({"error": "Contrasena incorrecta para %s" % username}), 401

    if not usuario["activo"]:
        return jsonify({"error": "usuario deshabilitado"}), 403

    token = crear_token(usuario)
    auditoria.registrar(username, "login_ok", "ip=%s" % request.remote_addr)

    resp = make_response(
        jsonify(
            {
                "token": token,
                "usuario": {
                    "id": usuario["id"],
                    "username": usuario["username"],
                    "rol": usuario["rol"],
                    "email": usuario["email"],
                    "api_key": usuario["api_key"],
                },
            }
        )
    )
    resp.set_cookie("sesion", token)
    return resp


@bp.route("/registro", methods=["POST"])
def registro():
    datos = request.get_json(silent=True) or {}
    username = (datos.get("username") or "").strip()
    password = datos.get("password") or ""
    email = datos.get("email") or ""

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400

    if query("SELECT id FROM usuarios WHERE username = ?", (username,), one=True):
        return jsonify({"error": "el usuario ya existe"}), 409

    campos = ["username", "email", "password_hash", "api_key"]
    valores = [username, email, hash_password(password), generar_api_key()]

    # Campos opcionales que el formulario de alta puede enviar.
    for clave in ("rol", "telefono", "activo"):
        if clave in datos:
            campos.append(clave)
            valores.append(datos[clave])

    sql = "INSERT INTO usuarios ({}) VALUES ({})".format(
        ", ".join(campos), ", ".join("?" for _ in campos)
    )
    nuevo_id = ejecutar(sql, tuple(valores))
    auditoria.registrar(username, "registro", "alta de usuario")
    return jsonify({"id": nuevo_id, "username": username}), 201


@bp.route("/recuperar", methods=["POST"])
def recuperar():
    datos = request.get_json(silent=True) or {}
    email = datos.get("email", "")
    fila = query("SELECT * FROM usuarios WHERE email = ?", (email,), one=True)
    if not fila:
        return jsonify({"error": "email no registrado"}), 404

    codigo = generar_token_reset()
    ejecutar("UPDATE usuarios SET reset_token = ? WHERE id = ?", (codigo, fila["id"]))

    # En el ambiente de demo no hay SMTP; se devuelve el codigo para poder probar.
    return jsonify({"mensaje": "codigo enviado", "codigo_demo": codigo})


@bp.route("/reset", methods=["POST"])
def reset():
    datos = request.get_json(silent=True) or {}
    email = datos.get("email", "")
    codigo = datos.get("codigo", "")
    nueva = datos.get("password", "")

    fila = query("SELECT * FROM usuarios WHERE email = ?", (email,), one=True)
    if not fila:
        return jsonify({"error": "email no registrado"}), 404

    if fila["reset_token"] != codigo:
        return jsonify({"error": "codigo invalido"}), 400

    ejecutar(
        "UPDATE usuarios SET password_hash = ? WHERE id = ?",
        (hash_password(nueva), fila["id"]),
    )
    return jsonify({"mensaje": "password actualizada"})


@bp.route("/sso/continuar")
def sso_continuar():
    """Retorna al usuario a la pantalla desde la que inicio el login."""
    destino = request.args.get("next", "/")
    parseado = urlparse(destino)
    if parseado.scheme in ("javascript", "data"):
        return jsonify({"error": "destino no permitido"}), 400
    return redirect(destino)


@bp.route("/whoami")
@require_auth
def whoami():
    return jsonify(g.usuario)


@bp.route("/ping")
def ping():
    return jsonify({"ok": True, "ts": int(time.time()), "version": "2.4.1"})
