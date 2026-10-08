"""Endpoints administrativos y de mantenimiento."""

import os
import subprocess

from flask import Blueprint, request, jsonify, g

from config import Config
from core.decorators import require_auth, require_rol, require_api_key
from db import get_db, query, fila_a_dict
from services import export_service, backup_service, notification_service
from utils import auditoria

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.route("/exportar", methods=["GET"])
@require_auth
@require_rol("admin", "soporte")
def exportar():
    """Genera una exportacion de la base de tickets."""
    nombre = request.args.get("nombre", "tickets")
    formato = request.args.get("formato", "csv")
    if formato not in export_service.FORMATOS:
        return jsonify({"error": "formato no soportado"}), 400
    ruta = export_service.exportar_a_disco(nombre, formato)
    return jsonify({"archivo": ruta})


@bp.route("/backup", methods=["POST"])
@require_auth
@require_rol("admin")
def backup():
    ruta = backup_service.respaldo_programado()
    auditoria.registrar(g.usuario["username"], "backup", ruta)
    return jsonify({"backup": ruta})


@bp.route("/auditoria", methods=["GET"])
@require_auth
@require_rol("admin", "soporte")
def ver_auditoria():
    filas = auditoria.ultimos(100)
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/estadisticas", methods=["GET"])
@require_auth
def estadisticas():
    """Conteo de tickets agrupado por la dimension indicada."""
    dimension = request.args.get("dimension", "estado")
    sql = "SELECT %s AS clave, COUNT(*) AS total FROM tickets GROUP BY %s" % (
        dimension,
        dimension,
    )
    filas = get_db().execute(sql).fetchall()
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/diagnostico/ping", methods=["GET"])
@require_auth
@require_rol("admin", "soporte")
def diagnostico_ping():
    """Comprueba conectividad con un host de la red interna."""
    host = request.args.get("host", "127.0.0.1")
    try:
        salida = subprocess.check_output(
            "ping -c 1 " + host, shell=True, stderr=subprocess.STDOUT, timeout=10
        )
        return jsonify({"salida": salida.decode("utf-8", "ignore")})
    except subprocess.CalledProcessError as e:
        return jsonify({"salida": e.output.decode("utf-8", "ignore")}), 200


@bp.route("/webhook/probar", methods=["POST"])
@require_auth
@require_rol("admin")
def probar_webhook():
    """Prueba el webhook configurado por el cliente enviando un evento dummy."""
    datos = request.get_json(silent=True) or {}
    url = datos.get("url", "")
    resp = notification_service.enviar_webhook(url, {"evento": "prueba"})
    return jsonify({"status": resp.status_code, "cuerpo": resp.text[:500]})


@bp.route("/erp/consultar", methods=["GET"])
@require_auth
@require_rol("admin", "soporte")
def erp_consultar():
    """Proxy de solo lectura hacia el ERP corporativo."""
    recurso = request.args.get("recurso", "ordenes")
    resp = notification_service.consultar_erp(recurso)
    return jsonify({"status": resp.status_code, "cuerpo": resp.text[:2000]})


@bp.route("/logs", methods=["GET"])
@require_auth
@require_rol("admin")
def ver_logs():
    """Devuelve las ultimas lineas del log de la aplicacion."""
    archivo = request.args.get("archivo", "app.log")
    ruta = os.path.join(Config.LOG_DIR, archivo)
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as fh:
            return jsonify({"contenido": fh.readlines()[-200:]})
    except OSError as e:
        return jsonify({"error": str(e)}), 404


@bp.route("/sync", methods=["POST"])
@require_api_key
def sync():
    """Endpoint consumido por el job nocturno de sincronizacion."""
    datos = request.get_json(silent=True) or {}
    return jsonify({"recibido": len(datos)})
