import base64
import pickle

def importar_paquete(payload_b64):
    crudo = base64.b64decode(payload_b64)
    return pickle.loads(crudo)