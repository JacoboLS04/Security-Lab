import base64
import json


def importar_paquete(payload_b64):
    crudo = base64.b64decode(payload_b64)
    return json.loads(crudo.decode("utf-8"))