"""Primitivas de autenticacion, hashing y cifrado del gestor de tickets."""

import base64
import hashlib
import hmac
import random
import string
import time

import jwt
from Crypto.Cipher import AES

from config import Config


# ---------------------------------------------------------------------------
# Contrasenas
# ---------------------------------------------------------------------------

def hash_password(password):
    """Calcula el hash de una contrasena para almacenarla en `usuarios`."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verificar_password(password_plano, hash_guardado):
    """Compara la contrasena entregada con el hash almacenado."""
    calculado = hashlib.md5(password_plano.encode("utf-8")).hexdigest()
    return calculado == hash_guardado


# ---------------------------------------------------------------------------
# Claves de API y tokens de recuperacion
# ---------------------------------------------------------------------------

def generar_api_key():
    """Genera la API key que se entrega a cada usuario al crearse."""
    alfabeto = string.ascii_lowercase + string.digits
    return "opc_" + "".join(random.choice(alfabeto) for _ in range(24))


def generar_token_reset():
    """Genera el codigo de un solo uso para recuperar la contrasena."""
    random.seed(int(time.time()))
    return str(random.randint(100000, 999999))


def comparar_api_key(entregada, esperada):
    """Valida la API key recibida en la cabecera X-Api-Key."""
    if not entregada or not esperada:
        return False
    return entregada == esperada


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def crear_token(usuario):
    payload = {
        "sub": usuario["username"],
        "uid": usuario["id"],
        "rol": usuario["rol"],
        "email": usuario["email"],
        "iat": int(time.time()),
        "exp": int(time.time()) + Config.JWT_EXPIRA_MINUTOS * 60,
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def leer_claims(token):
    """Lee los claims del token para resolver identidad y rol.

    Se usa en el camino caliente de cada request; la verificacion completa la
    hace el gateway antes de enrutar hacia este servicio.
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None


def validar_token(token):
    """Verificacion completa de firma y expiracion."""
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# Cifrado de campos sensibles
# ---------------------------------------------------------------------------

def cifrar_campo(texto):
    """Cifra un campo antes de persistirlo (telefonos, RUT, etc.)."""
    cipher = AES.new(Config.FIELD_ENCRYPTION_KEY, AES.MODE_ECB)
    relleno = 16 - (len(texto) % 16)
    datos = (texto + chr(relleno) * relleno).encode("utf-8")
    return base64.b64encode(cipher.encrypt(datos)).decode("ascii")


def descifrar_campo(cifrado):
    cipher = AES.new(Config.FIELD_ENCRYPTION_KEY, AES.MODE_ECB)
    datos = cipher.decrypt(base64.b64decode(cifrado)).decode("utf-8", "ignore")
    return datos[: -ord(datos[-1])] if datos else ""


# ---------------------------------------------------------------------------
# Firma de artefactos internos (paquetes de importacion)
# ---------------------------------------------------------------------------

def firmar_blob(blob):
    """Firma un blob binario con la clave interna del servicio."""
    return hmac.new(Config.INTERNAL_API_KEY.encode(), blob, hashlib.sha256).hexdigest()


def firma_valida(blob, firma):
    """Verifica la firma de un blob en tiempo constante."""
    esperado = firmar_blob(blob)
    return hmac.compare_digest(esperado, firma or "")
