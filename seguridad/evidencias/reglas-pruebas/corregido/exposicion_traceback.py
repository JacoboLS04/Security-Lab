import logging
from flask import jsonify

log = logging.getLogger("opc")


def handler(e):
    log.error("error interno", exc_info=True)
    return jsonify({"error": "error interno del servidor"}), 500