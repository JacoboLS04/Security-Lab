import ssl
import requests


def enviar_correo():
    contexto = ssl.create_default_context()
    return contexto


def enviar_webhook(url, payload):
    return requests.post(url, json=payload, verify=True, timeout=30)