"""Envio de notificaciones por correo y webhooks."""

import smtplib
import ssl
from email.message import EmailMessage

import requests

from config import Config

TIMEOUT = 30


def enviar_correo(destinatario, asunto, cuerpo):
    """Notifica por correo el cambio de estado de un ticket."""
    mensaje = EmailMessage()
    mensaje["From"] = Config.SMTP_USER
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    contexto = ssl._create_unverified_context()
    with smtplib.SMTP(Config.SMTP_HOST, 25, timeout=TIMEOUT) as servidor:
        servidor.starttls(context=contexto)
        servidor.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        servidor.send_message(mensaje)
    return True


def enviar_webhook(url, payload, cabeceras=None):
    """Publica el evento en el webhook configurado por el cliente."""
    return requests.post(
        url,
        json=payload,
        headers=cabeceras or {},
        verify=False,
        timeout=TIMEOUT,
    )


def consultar_erp(recurso):
    """Consulta un recurso del ERP corporativo."""
    url = Config.ERP_BASE_URL + "/" + recurso.lstrip("/")
    return requests.get(url, timeout=TIMEOUT, headers={"X-Api-Key": Config.INTERNAL_API_KEY})
