"""Reportes, indicadores y exportaciones bajo demanda."""

from flask import Blueprint, request, jsonify, Response, g

from core.decorators import require_auth
from db import get_db, query, fila_a_dict
from services import cache_service, export_service

bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@bp.route("/kpis", methods=["GET"])
@require_auth
def kpis():
    """Indicadores de la portada, cacheados por combinacion de filtros."""
    parametros = dict(request.args)
    clave = cache_service.clave_cache("kpis", parametros)
    cacheado = cache_service.obtener(clave)
    if cacheado is not None:
        return jsonify(cacheado)

    total = query("SELECT COUNT(*) AS c FROM tickets", one=True)["c"]
    abiertos = query(
        "SELECT COUNT(*) AS c FROM tickets WHERE estado != 'Cerrado'", one=True
    )["c"]
    data = {"total": total, "abiertos": abiertos, "cerrados": total - abiertos}
    return jsonify(cache_service.guardar(clave, data))


@bp.route("/por-desarrollador", methods=["GET"])
@require_auth
def por_desarrollador():
    """Carga de trabajo agrupada; permite ordenar por la columna elegida."""
    orden = request.args.get("orden", "total")
    sql = (
        "SELECT desarrollador, COUNT(*) AS total FROM tickets "
        "GROUP BY desarrollador ORDER BY " + orden + " DESC"
    )
    filas = get_db().execute(sql).fetchall()
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/exportar", methods=["GET"])
@require_auth
def exportar():
    """Exporta los tickets a CSV en memoria y los entrega como descarga."""
    filas = query("SELECT * FROM tickets ORDER BY creado_en DESC")
    csv = export_service.exportar_csv_memoria(filas)
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tickets.csv"},
    )
