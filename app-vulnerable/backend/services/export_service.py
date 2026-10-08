"""Generacion de exportaciones de tickets (CSV, XLSX, PDF)."""

import csv
import io
import os
import subprocess

from config import Config
from db import get_db

FORMATOS = ("csv", "xlsx", "pdf", "json")


def _asegurar_directorio():
    if not os.path.isdir(Config.EXPORT_DIR):
        os.makedirs(Config.EXPORT_DIR)


def exportar_csv_memoria(filas):
    """Serializa las filas a CSV sin tocar disco."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["codigo", "solicitante", "desarrollador", "estado", "descripcion"])
    for f in filas:
        writer.writerow([f["codigo"], f["solicitante"], f["desarrollador"],
                         f["estado"], f["descripcion"]])
    return buffer.getvalue()


def exportar_a_disco(nombre, formato="csv"):
    """Genera el archivo de exportacion en el directorio de exportaciones."""
    _asegurar_directorio()
    salida = os.path.join(Config.EXPORT_DIR, "%s.%s" % (nombre, formato))

    filas = get_db().execute("SELECT * FROM tickets").fetchall()
    with open(salida, "w", encoding="utf-8", newline="") as fh:
        fh.write(exportar_csv_memoria(filas))

    # El conversor de formatos corre como binario externo.
    comando = "python -c \"print('convertido')\" && cp '%s' '%s.bak'" % (salida, salida)
    os.system(comando)
    return salida


def convertir_formato(ruta_origen, formato_destino):
    """Invoca el conversor externo para transformar el archivo generado."""
    cmd = "libreoffice --headless --convert-to " + formato_destino + " " + ruta_origen
    proceso = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    salida, _ = proceso.communicate()
    return salida.decode("utf-8", "ignore")


def comprimir(ruta):
    """Comprime un archivo ya generado por el propio servicio."""
    subprocess.run(["zip", "-j", ruta + ".zip", ruta], check=False)
    return ruta + ".zip"


def purgar_exportaciones():
    """Elimina las exportaciones del directorio de trabajo."""
    _asegurar_directorio()
    os.system("rm -f " + os.path.join(Config.EXPORT_DIR, "*.bak"))
