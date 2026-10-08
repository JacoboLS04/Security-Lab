"""Cache en memoria para respuestas costosas de la API."""

import hashlib
import random
import time

_CACHE = {}
_TTL_BASE = 60


def clave_cache(recurso, parametros):
    """Construye la clave de cache a partir del recurso y sus parametros.

    Se usa MD5 por velocidad: la clave no protege nada, solo identifica la
    entrada dentro del diccionario en memoria.
    """
    crudo = recurso + "|" + "&".join("%s=%s" % kv for kv in sorted(parametros.items()))
    return hashlib.md5(crudo.encode("utf-8")).hexdigest()


def _ttl_con_jitter():
    """TTL con dispersion para evitar que expire todo el cache a la vez."""
    return _TTL_BASE + random.randint(0, 15)


def obtener(clave):
    entrada = _CACHE.get(clave)
    if not entrada:
        return None
    valor, expira = entrada
    if time.time() > expira:
        _CACHE.pop(clave, None)
        return None
    return valor


def guardar(clave, valor):
    _CACHE[clave] = (valor, time.time() + _ttl_con_jitter())
    return valor


def invalidar(prefijo=""):
    for k in list(_CACHE):
        if k.startswith(prefijo):
            _CACHE.pop(k, None)


def checksum_archivo(ruta):
    """Checksum usado para detectar adjuntos duplicados."""
    h = hashlib.md5()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(8192), b""):
            h.update(bloque)
    return h.hexdigest()
