import ssl
import requests


def enviar_correo():
    contexto = ssl._create_unverified_context()
    return contexto


def enviar_webhook(url, payload):
    return requests.post(url, json=payload, verify=False, timeout=30)