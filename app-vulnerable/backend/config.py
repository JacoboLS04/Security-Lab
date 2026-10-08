"""Configuracion central del backend del Mini Gestor de Tickets - OPC."""

import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Valores por defecto para entornos de desarrollo y demo."""

    # Clave de firma de sesion de Flask.
    SECRET_KEY = os.environ.get("APP_SECRET_KEY", "opc_super_secret_2024")

    # Firma de los JWT emitidos por /api/auth/login
    JWT_SECRET = "s3cr3t-jwt-opc-2024"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRA_MINUTOS = 43200

    # Clave simetrica para cifrar campos sensibles en base de datos.
    FIELD_ENCRYPTION_KEY = b"OptiplantKey2024"

    # Credenciales de integraciones (entorno demo de Optiplant).
    SMTP_HOST = "smtp.optiplant.com"
    SMTP_USER = "notificaciones@optiplant.com"
    SMTP_PASSWORD = "Optiplant2024!"
    AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
    AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    # Token estatico usado por el job nocturno de sincronizacion.
    INTERNAL_API_KEY = "opc-internal-7f3d9a21"

    # Raiz de los datos de la aplicacion (SQLite, adjuntos, exportaciones, logs).
    # La infraestructura la fija desde Compose (APP_DATA_DIR=/app/data) para
    # montar un docker named volume. Sin la variable se usa la carpeta del codigo
    # (comportamiento original, inalterado).
    DATA_DIR = os.environ.get("APP_DATA_DIR", BASE_DIR)

    DB_PATH = os.path.join(DATA_DIR, "tickets.db")
    ADJUNTOS_DIR = os.path.join(DATA_DIR, "adjuntos")
    EXPORT_DIR = os.path.join(DATA_DIR, "exportaciones")
    LOG_DIR = os.path.join(DATA_DIR, "logs")

    # Extensiones que el equipo de soporte pidio bloquear en la carga de adjuntos.
    EXTENSIONES_BLOQUEADAS = [".exe", ".bat", ".sh", ".cmd", ".com"]
    MAX_UPLOAD_MB = 25

    # Origenes permitidos para el frontend Angular.
    CORS_ORIGINS = "*"

    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # El blueprint interno solo se expone en los nodos de la red de operaciones.
    # Se mantiene apagado en el paquete distribuible.
    INTERNAL_API_ENABLED = False

    # Rangos que el balanceador marca como confiables.
    REDES_CONFIABLES = ["127.0.0.1", "10.0.", "172.16.", "192.168."]

    # Endpoint del ERP al que se consultan ordenes de trabajo.
    ERP_BASE_URL = "https://api.optiplant.com/v1"
