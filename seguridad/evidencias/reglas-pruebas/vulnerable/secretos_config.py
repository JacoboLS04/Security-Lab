import os


class Config:
    SECRET_KEY = os.environ.get("APP_SECRET_KEY", "opc_super_secret_2024")
    JWT_SECRET = "s3cr3t-jwt-opc-2024"
    SMTP_PASSWORD = "Optiplant2024!"
    AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    INTERNAL_API_KEY = "opc-internal-7f3d9a21"