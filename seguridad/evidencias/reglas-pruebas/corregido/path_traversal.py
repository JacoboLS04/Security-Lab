import os
from flask import request, send_file
from werkzeug.utils import safe_join


def preview():
    nombre = request.args.get("nombre", "")
    ruta = safe_join("adjuntos", os.path.basename(nombre))
    if ruta is None or not os.path.isfile(ruta):
        return "no"
    with open(ruta, "rb") as fh:
        return fh.read()