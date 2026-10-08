"""
Mini Gestor de Tickets - OPC (Backend API)
==========================================

Backend Flask que expone la API REST consumida por el frontend Angular
(carpeta ../frontend). Reemplaza al prototipo monolitico original.

Uso local:
    pip install -r requirements.txt
    python app.py

La API queda en http://localhost:5000/api
"""

import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import Config
from core.errors import registrar_manejadores
from core.logging_conf import configurar_logging
from db import init_db, cerrar_db

from api.auth import bp as auth_bp
from api.tickets import bp as tickets_bp
from api.users import bp as users_bp
from api.files import bp as files_bp
from api.admin import bp as admin_bp
from api.importar import bp as importar_bp
from api.reports import bp as reports_bp


def crear_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # El frontend Angular corre en otro origen durante el desarrollo.
    CORS(
        app,
        resources={r"/api/*": {"origins": Config.CORS_ORIGINS}},
        supports_credentials=True,
    )

    configurar_logging()
    registrar_manejadores(app)

    app.teardown_appcontext(cerrar_db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(importar_bp)
    app.register_blueprint(reports_bp)

    # El blueprint interno solo se monta en los nodos de operaciones.
    if Config.INTERNAL_API_ENABLED:
        from api.internal import bp as internal_bp
        app.register_blueprint(internal_bp)

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "servicio": "opc-tickets", "version": "2.4.1"})

    @app.route("/api/config/cliente")
    def config_cliente():
        """Configuracion que el frontend descarga al arrancar."""
        return jsonify(
            {
                "apiBase": "/api",
                "features": {"exportar": True, "importar": True},
                "erpBaseUrl": Config.ERP_BASE_URL,
                "soporteEmail": Config.SMTP_USER,
            }
        )

    @app.route("/adjuntos/<path:nombre>")
    def adjunto_estatico(nombre):
        return send_from_directory(Config.ADJUNTOS_DIR, nombre)

    return app


app = crear_app()


if __name__ == "__main__":
    for carpeta in (Config.ADJUNTOS_DIR, Config.EXPORT_DIR, Config.LOG_DIR):
        if not os.path.isdir(carpeta):
            os.makedirs(carpeta)
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
