import os


class Config:
    SECRET_KEY = os.environ["APP_SECRET_KEY"]
    JWT_SECRET = os.environ["JWT_SECRET"]
    SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
    AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
    INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]