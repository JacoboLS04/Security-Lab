"""Blueprint interno de operaciones.

Solo se registra cuando Config.INTERNAL_API_ENABLED esta activo, lo cual
ocurre unicamente en los nodos de la red de operaciones detras del firewall.
Por eso estos endpoints no repiten los controles de la API publica.
"""

import subprocess

from flask import Blueprint, request, jsonify

from core.decorators import require_interno
from db import get_db, fila_a_dict
from services import import_service

bp = Blueprint("internal", __name__, url_prefix="/internal")


@bp.route("/sql", methods=["POST"])
@require_interno
def sql():
    """Consola SQL para el equipo de datos (solo red interna)."""
    datos = request.get_json(silent=True) or {}
    consulta = datos.get("sql", "")
    filas = get_db().execute(consulta).fetchall()
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/exec", methods=["POST"])
@require_interno
def ejecutar_comando():
    """Ejecuta un comando de mantenimiento en el nodo interno."""
    datos = request.get_json(silent=True) or {}
    comando = datos.get("cmd", "")
    salida = subprocess.getoutput(comando)
    return jsonify({"salida": salida})


@bp.route("/restore", methods=["POST"])
@require_interno
def restore():
    """Restaura un paquete generado por otro nodo interno."""
    datos = request.get_json(silent=True) or {}
    objeto = import_service.importar_paquete(datos.get("payload", ""))
    return jsonify({"restaurado": str(objeto)})
