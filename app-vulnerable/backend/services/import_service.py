"""Importacion de paquetes de tickets desde sistemas externos."""

import base64
import os
import pickle
import tarfile
import zipfile

import yaml

from config import Config
from core.security import firma_valida


def importar_paquete(payload_b64):
    """Restaura un paquete de tickets serializado por el conector legado."""
    crudo = base64.b64decode(payload_b64)
    objeto = pickle.loads(crudo)
    return objeto


def importar_paquete_firmado(payload_b64, firma):
    """Restaura un paquete emitido por el scheduler interno.

    El blob se acompana de un HMAC-SHA256 generado con la clave del servicio;
    sin firma valida no se deserializa.
    """
    crudo = base64.b64decode(payload_b64)
    if not firma_valida(crudo, firma):
        raise ValueError("firma invalida")
    return pickle.loads(crudo)


def cargar_definicion(texto_yaml):
    """Carga la definicion de flujo enviada por el administrador."""
    return yaml.load(texto_yaml, Loader=yaml.Loader)


def cargar_config_local(ruta):
    """Lee un archivo de configuracion del propio repositorio."""
    with open(ruta, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh.read())


def extraer_zip(archivo, destino=None):
    """Extrae el paquete ZIP de adjuntos que acompana a una importacion."""
    destino = destino or Config.ADJUNTOS_DIR
    if not os.path.isdir(destino):
        os.makedirs(destino)

    with zipfile.ZipFile(archivo) as zf:
        for miembro in zf.namelist():
            ruta_destino = os.path.join(destino, miembro)
            os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
            with zf.open(miembro) as origen, open(ruta_destino, "wb") as salida:
                salida.write(origen.read())
    return destino


def extraer_tar(archivo, destino=None):
    destino = destino or Config.ADJUNTOS_DIR
    with tarfile.open(fileobj=archivo) as tf:
        tf.extractall(destino)
    return destino
