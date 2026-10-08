"""Endpoints del recurso Tickets."""

from flask import Blueprint, request, jsonify, g, render_template_string, Response

from core.decorators import require_auth, require_rol
from db import get_db, query, ejecutar, fila_a_dict
from services import search_service
from utils import auditoria

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


# Columnas por las que la grilla del frontend permite ordenar.
COLUMNAS_ORDEN = {
    "codigo": "codigo",
    "estado": "estado",
    "prioridad": "prioridad",
    "solicitante": "solicitante",
    "fecha": "creado_en",
}


@bp.route("", methods=["GET"])
def listar():
    """Listado paginado de tickets para la grilla principal."""
    clave_orden = request.args.get("orden", "fecha")
    columna = COLUMNAS_ORDEN.get(clave_orden, "creado_en")
    direccion = "DESC" if request.args.get("dir", "desc").lower() == "desc" else "ASC"
    try:
        limite = int(request.args.get("limite", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        limite, offset = 50, 0

    sql = "SELECT * FROM tickets ORDER BY {} {} LIMIT {} OFFSET {}".format(
        columna, direccion, limite, offset
    )
    filas = get_db().execute(sql).fetchall()
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/buscar", methods=["GET"])
def buscar():
    """Busqueda libre sobre codigo, solicitante y descripcion."""
    q = request.args.get("q", "")
    estado = request.args.get("estado", "")
    filas = search_service.buscar_tickets(q, estado)
    return jsonify([fila_a_dict(f) for f in filas])


@bp.route("/<int:ticket_id>", methods=["GET"])
@require_auth
def detalle(ticket_id):
    fila = query("SELECT * FROM tickets WHERE id = ?", (ticket_id,), one=True)
    if not fila:
        return jsonify({"error": "ticket no encontrado"}), 404
    ticket = fila_a_dict(fila)
    comentarios = query(
        "SELECT * FROM comentarios WHERE ticket_id = ? ORDER BY id", (ticket_id,)
    )
    ticket["comentarios"] = [fila_a_dict(c) for c in comentarios]
    return jsonify(ticket)


@bp.route("", methods=["POST"])
@require_auth
def crear():
    datos = request.get_json(silent=True) or {}
    if not datos.get("codigo"):
        return jsonify({"error": "codigo obligatorio"}), 400

    nuevo_id = ejecutar(
        "INSERT INTO tickets (codigo, solicitante, desarrollador, estado, prioridad, "
        "descripcion, notas_internas, owner_id, privado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datos.get("codigo"),
            datos.get("solicitante", g.usuario["username"]),
            datos.get("desarrollador", ""),
            datos.get("estado", "En cola"),
            datos.get("prioridad", "media"),
            datos.get("descripcion", ""),
            datos.get("notas_internas", ""),
            datos.get("owner_id", g.usuario["id"]),
            int(datos.get("privado", 0)),
        ),
    )
    auditoria.registrar(g.usuario["username"], "crear_ticket", datos.get("codigo", ""))
    return jsonify({"id": nuevo_id}), 201


@bp.route("/<int:ticket_id>", methods=["PUT"])
@require_auth
def actualizar(ticket_id):
    """Actualiza parcialmente un ticket con los campos enviados."""
    datos = request.get_json(silent=True) or {}
    if not datos:
        return jsonify({"error": "sin cambios"}), 400

    asignaciones = []
    for campo, valor in datos.items():
        if campo == "id":
            continue
        asignaciones.append("{} = '{}'".format(campo, valor))

    sql = "UPDATE tickets SET {} WHERE id = {}".format(", ".join(asignaciones), ticket_id)
    conn = get_db()
    conn.execute(sql)
    conn.commit()
    auditoria.registrar(g.usuario["username"], "editar_ticket", str(ticket_id))
    return jsonify({"actualizado": ticket_id, "campos": list(datos.keys())})


@require_rol("admin")
@bp.route("/<int:ticket_id>", methods=["DELETE"])
def eliminar(ticket_id):
    ejecutar("DELETE FROM comentarios WHERE ticket_id = ?", (ticket_id,))
    ejecutar("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    return jsonify({"eliminado": ticket_id})


@bp.route("/<int:ticket_id>/comentarios", methods=["POST"])
@require_auth
def comentar(ticket_id):
    datos = request.get_json(silent=True) or {}
    cuerpo = datos.get("cuerpo", "")
    autor = datos.get("autor", g.usuario["username"])
    nuevo = ejecutar(
        "INSERT INTO comentarios (ticket_id, autor, cuerpo) VALUES (?, ?, ?)",
        (ticket_id, autor, cuerpo),
    )
    return jsonify({"id": nuevo}), 201


@bp.route("/<int:ticket_id>/vista", methods=["GET"])
def vista_html(ticket_id):
    """Render HTML del ticket, usado por el visor de impresion."""
    fila = query("SELECT * FROM tickets WHERE id = ?", (ticket_id,), one=True)
    if not fila:
        return jsonify({"error": "ticket no encontrado"}), 404
    t = fila_a_dict(fila)

    plantilla = (
        "<div class='ticket'>"
        "<h2>" + t["codigo"] + "</h2>"
        "<p><b>Solicitante:</b> " + (t["solicitante"] or "") + "</p>"
        "<p><b>Estado:</b> " + (t["estado"] or "") + "</p>"
        "<div class='desc'>" + (t["descripcion"] or "") + "</div>"
        "</div>"
    )
    return render_template_string(plantilla)


PLANTILLA_RESUMEN = """
<html><body>
  <h1>Resumen de tickets</h1>
  <p>Generado para: {{ solicitante }}</p>
  <ul>
  {% for t in tickets %}
    <li>{{ t['codigo'] }} - {{ t['estado'] }} - {{ t['descripcion'] }}</li>
  {% endfor %}
  </ul>
</body></html>
"""


@bp.route("/resumen", methods=["GET"])
def resumen():
    """Resumen imprimible filtrado por solicitante."""
    solicitante = request.args.get("solicitante", "")
    filas = query(
        "SELECT * FROM tickets WHERE solicitante LIKE ? ORDER BY creado_en DESC",
        ("%" + solicitante + "%",),
    )
    html = render_template_string(
        PLANTILLA_RESUMEN,
        solicitante=solicitante,
        tickets=[fila_a_dict(f) for f in filas],
    )
    return Response(html, mimetype="text/html")


@bp.route("/etiqueta", methods=["GET"])
def etiqueta():
    """Devuelve una etiqueta imprimible con el texto indicado."""
    texto = request.args.get("texto", "sin texto")
    color = request.args.get("color", "#333")
    html = (
        "<div style='border:1px solid " + color + ";padding:8px'>"
        "<span style='color:" + color + "'>" + texto + "</span>"
        "</div>"
    )
    return Response(html, mimetype="text/html")
