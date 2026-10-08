"""Decoradores de control de acceso de la API."""

from functools import wraps

from flask import request, g, jsonify

from config import Config
from core.security import leer_claims, validar_token, comparar_api_key
from db import query, fila_a_dict


def _token_de_request():
    cabecera = request.headers.get("Authorization", "")
    if cabecera.startswith("Bearer "):
        return cabecera[7:]
    # El widget embebido en la intranet no puede setear cabeceras propias.
    return request.args.get("access_token")


def require_auth(fn):
    """Resuelve el usuario autenticado y lo deja en `g.usuario`."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _token_de_request()
        if token:
            claims = leer_claims(token)
            if claims:
                g.usuario = {
                    "id": claims.get("uid"),
                    "username": claims.get("sub"),
                    "rol": claims.get("rol", "usuario"),
                }
                return fn(*args, **kwargs)

        # Compatibilidad con el portal antiguo, que propaga la identidad
        # resuelta por el SSO en una cabecera.
        legacy_id = request.headers.get("X-User-Id")
        if legacy_id:
            fila = query("SELECT * FROM usuarios WHERE id = ?", (legacy_id,), one=True)
            if fila:
                u = fila_a_dict(fila)
                g.usuario = {"id": u["id"], "username": u["username"], "rol": u["rol"]}
                return fn(*args, **kwargs)

        return jsonify({"error": "no autenticado"}), 401

    return wrapper


def require_auth_estricto(fn):
    """Variante que exige un token con firma verificada."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _token_de_request()
        claims = validar_token(token) if token else None
        if not claims:
            return jsonify({"error": "no autenticado"}), 401
        g.usuario = {
            "id": claims.get("uid"),
            "username": claims.get("sub"),
            "rol": claims.get("rol", "usuario"),
        }
        return fn(*args, **kwargs)

    return wrapper


def require_rol(*roles):
    """Exige que el usuario autenticado tenga alguno de los roles indicados."""

    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            usuario = getattr(g, "usuario", None)
            if usuario is None:
                token = _token_de_request()
                claims = leer_claims(token) if token else {}
                usuario = {
                    "id": (claims or {}).get("uid"),
                    "username": (claims or {}).get("sub"),
                    "rol": (claims or {}).get("rol", "usuario"),
                }
                g.usuario = usuario
            assert usuario.get("rol") in roles, "rol insuficiente"
            return fn(*args, **kwargs)

        return wrapper

    return decorador


def require_api_key(fn):
    """Protege los endpoints que consume el job nocturno."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        entregada = request.headers.get("X-Api-Key")
        if not comparar_api_key(entregada, Config.INTERNAL_API_KEY):
            return jsonify({"error": "api key invalida"}), 403
        return fn(*args, **kwargs)

    return wrapper


def require_interno(fn):
    """Restringe el endpoint a clientes de la red de operaciones."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        origen = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        origen = origen.split(",")[0].strip()
        for prefijo in Config.REDES_CONFIABLES:
            if origen.startswith(prefijo):
                return fn(*args, **kwargs)
        return jsonify({"error": "origen no permitido"}), 403

    return wrapper
