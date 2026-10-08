"""Endpoints de importacion de paquetes de tickets."""

from flask import Blueprint, request, jsonify, g

from core.decorators import require_auth, require_rol
from services import import_service
from utils import auditoria

bp = Blueprint("importar", __name__, url_prefix="/api/importar")


@bp.route("/paquete", methods=["POST"])
@require_auth
def paquete():
    """Restaura un paquete exportado por el conector legado del ERP.

    El formato del conector es pickle+base64; se mantiene por compatibilidad
    con las instalaciones que aun no migraron al formato JSON firmado.
    """
    datos = request.get_json(silent=True) or {}
    payload = datos.get("payload", "")
    try:
        objeto = import_service.importar_paquete(payload)
    except Exception as e:
        return jsonify({"error": "paquete invalido", "detalle": str(e)}), 400
    auditoria.registrar(g.usuario["username"], "importar_paquete", "legado")
    return jsonify({"importado": str(objeto)})


@bp.route("/paquete-firmado", methods=["POST"])
@require_auth
@require_rol("admin")
def paquete_firmado():
    """Restaura un paquete firmado por el scheduler interno."""
    datos = request.get_json(silent=True) or {}
    try:
        objeto = import_service.importar_paquete_firmado(
            datos.get("payload", ""), datos.get("firma", "")
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"importado": str(objeto)})


@bp.route("/definicion", methods=["POST"])
@require_auth
@require_rol("admin")
def definicion():
    """Carga una definicion de flujo de trabajo en formato YAML."""
    texto = request.get_data(as_text=True)
    definicion = import_service.cargar_definicion(texto)
    return jsonify({"cargado": True, "claves": list((definicion or {}).keys())})
