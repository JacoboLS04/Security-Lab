import base64
from Crypto.Cipher import AES

CLAVE = b"OptiplantKey2024"

def cifrar(texto):
    cipher = AES.new(CLAVE, AES.MODE_ECB)
    relleno = 16 - (len(texto) % 16)
    datos = (texto + chr(relleno) * relleno).encode("utf-8")
    return base64.b64encode(cipher.encrypt(datos)).decode("ascii")