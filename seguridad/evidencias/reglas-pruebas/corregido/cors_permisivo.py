from flask_cors import CORS

ORIGENES_PERMITIDOS = ["https://tickets.opc.example"]


def crear_app(app):
    CORS(
        app,
        resources={r"/api/*": {"origins": ORIGENES_PERMITIDOS}},
        supports_credentials=True,
    )
    return app