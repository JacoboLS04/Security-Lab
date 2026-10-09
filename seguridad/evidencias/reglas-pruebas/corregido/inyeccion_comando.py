import os
import subprocess
import shlex

OPC_PING_OK = ("127.0.0.1", "10.0.2.15", "172.19.0.1")


def ping(host):
    if host not in OPC_PING_OK:
        return {"error": "host no permitido"}
    subprocess.check_output(["ping", "-c", "1", host], stderr=subprocess.STDOUT, timeout=10)


def convertir(ruta, formato):
    subprocess.run(["libreoffice", "--headless", "--convert-to", formato, ruta])


def limpiar():
    os.remove("/tmp/x.bak")