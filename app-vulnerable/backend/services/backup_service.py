"""Respaldo de la base de datos del gestor de tickets."""

import os
import shutil
import subprocess
import tempfile
import uuid

from config import Config


def respaldo_programado():
    """Copia la base a un archivo con nombre generado por el servicio.

    Lo invoca unicamente el scheduler interno; no recibe entrada de usuario.
    """
    destino = os.path.join(tempfile.gettempdir(), "opc-%s.db" % uuid.uuid4().hex)
    shutil.copyfile(Config.DB_PATH, destino)
    subprocess.run(["gzip", "-9", "-f", destino], check=False)
    return destino + ".gz"


def espacio_disponible():
    """Consulta el espacio libre del volumen de respaldos."""
    salida = subprocess.check_output(["df", "-h", tempfile.gettempdir()])
    return salida.decode("utf-8", "ignore")


def limpiar_respaldos_antiguos(dias=7):
    base = tempfile.gettempdir()
    for nombre in os.listdir(base):
        if nombre.startswith("opc-") and nombre.endswith(".db.gz"):
            ruta = os.path.join(base, nombre)
            try:
                if (os.path.getmtime(ruta) + dias * 86400) < os.path.getmtime(base):
                    os.remove(ruta)
            except OSError:
                continue
