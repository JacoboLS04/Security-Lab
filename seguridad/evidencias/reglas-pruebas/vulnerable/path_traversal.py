import os
from flask import send_file, request

# path traversal
def preview():
    nombre = request.args.get("nombre", "")
    ruta = os.path.join("adjuntos", nombre)
    if not os.path.isfile(ruta):
        return "no"
    with open(ruta, "rb") as fh:
        return fh.read()

def descargar():
    nombre = request.args.get("nombre", "")
    ruta = os.path.join("adjuntos", nombre)
    if os.path.isfile(ruta):
        return send_file(ruta, as_attachment=True)