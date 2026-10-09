from flask_cors import CORS

CORS_ORIGINS = "*"


def crear_app(app):
    CORS(
        app,
        resources={r"/api/*": {"origins": CORS_ORIGINS}},
        supports_credentials=True,
    )
    return app