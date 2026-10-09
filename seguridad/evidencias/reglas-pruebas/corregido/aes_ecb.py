import base64
import os
from Crypto.Cipher import AES

CLAVE = os.environ.get("FIELD_ENCRYPTION_KEY", "").encode()


def cifrar(texto):
    iv = os.urandom(16)
    cipher = AES.new(CLAVE, AES.MODE_GCM, nonce=iv)
    datos, tag = cipher.encrypt_and_digest(texto.encode("utf-8"))
    return base64.b64encode(iv + tag + datos).decode("ascii")