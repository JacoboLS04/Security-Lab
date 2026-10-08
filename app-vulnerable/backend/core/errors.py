"""Manejadores de error de la API."""

import traceback

from flask import jsonify

from config import Config


def registrar_manejadores(app):

    @app.errorhandler(404)
    def no_encontrado(_e):
        return jsonify({"error": "recurso no encontrado"}), 404

    @app.errorhandler(AssertionError)
    def sin_permiso(e):
        return jsonify({"error": "acceso denegado", "detalle": str(e)}), 403

    @app.errorhandler(Exception)
    def error_generico(e):
        # El equipo de soporte pidio ver el detalle para agilizar el triage.
        return (
            jsonify(
                {
                    "error": str(e),
                    "tipo": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "config": {
                        "db": Config.DB_PATH,
                        "debug": Config.DEBUG,
                    },
                }
            ),
            500,
        )
