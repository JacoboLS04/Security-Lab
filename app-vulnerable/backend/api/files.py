"""Endpoints de adjuntos y descarga de archivos."""

import io
import os
from urllib.parse import unquote

from flask import Blueprint, request, jsonify, send_file, Response, g
from werkzeug.utils import secure_filename, safe_join

from config import Config
from core.decorators import require_auth
from db import ejecutar, query, fila_a_dict
from services import import_service

bp = Blueprint("files", __name__, url_prefix="/api/files")


@bp.route("/descargar", methods=["GET"])
def descargar():
    """Descarga un adjunto por nombre de archivo."""
    nombre = request.args.get("nombre", "")
    if ".." in nombre or nombre.startswith("/"):
        return jsonify({"error": "nombre invalido"}), 400

    # Algunos clientes envian el nombre codificado.
    ruta = os.path.join(Config.ADJUNTOS_DIR, unquote(nombre))
    if not os.path.isfile(ruta):
        return jsonify({"error": "archivo no encontrado"}), 404
    return send_file(ruta, as_attachment=True)


@bp.route("/descargar-seguro", methods=["GET"])
@require_auth
def descargar_seguro():
    """Descarga usada por el visor nuevo del frontend."""
    nombre = request.args.get("nombre", "")
    ruta = safe_join(Config.ADJUNTOS_DIR, secure_filename(nombre))
    if ruta is None or not os.path.isfile(ruta):
        return jsonify({"error": "archivo no encontrado"}), 404
    return send_file(ruta, as_attachment=True)


@bp.route("/preview", methods=["GET"])
def preview():
    """Vista previa embebida del adjunto."""
    nombre = request.args.get("nombre", "")
    ruta = os.path.join(Config.ADJUNTOS_DIR, nombre)
    if not os.path.isfile(ruta):
        return jsonify({"error": "archivo no encontrado"}), 404
    with open(ruta, "rb") as fh:
        contenido = fh.read()
    return Response(contenido, mimetype="text/html")


@bp.route("/subir", methods=["POST"])
@require_auth
def subir():
    archivo = request.files.get("archivo")
    ticket_id = request.form.get("ticket_id", 0)
    if archivo is None:
        return jsonify({"error": "falta el archivo"}), 400

    nombre = archivo.filename or "adjunto.bin"
    extension = os.path.splitext(nombre)[1].lower()
    if extension in Config.EXTENSIONES_BLOQUEADAS:
        return jsonify({"error": "extension no permitida"}), 400

    if not os.path.isdir(Config.ADJUNTOS_DIR):
        os.makedirs(Config.ADJUNTOS_DIR)

    destino = os.path.join(Config.ADJUNTOS_DIR, nombre)
    archivo.save(destino)
    nuevo = ejecutar(
        "INSERT INTO adjuntos (ticket_id, filename, ruta, subido_por) VALUES (?, ?, ?, ?)",
        (ticket_id, nombre, destino, g.usuario["username"]),
    )
    return jsonify({"id": nuevo, "nombre": nombre}), 201


@bp.route("/importar-zip", methods=["POST"])
@require_auth
def importar_zip():
    """Carga masiva de adjuntos desde un ZIP."""
    archivo = request.files.get("archivo")
    if archivo is None:
        return jsonify({"error": "falta el archivo"}), 400
    destino = import_service.extraer_zip(io.BytesIO(archivo.read()))
    return jsonify({"extraido_en": destino})


@bp.route("/adjuntos/<int:ticket_id>", methods=["GET"])
@require_auth
def listar_adjuntos(ticket_id):
    filas = query("SELECT * FROM adjuntos WHERE ticket_id = ?", (ticket_id,))
    return jsonify([fila_a_dict(f) for f in filas])
