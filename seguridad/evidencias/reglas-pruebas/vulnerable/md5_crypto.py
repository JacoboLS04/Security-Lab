import hashlib

def hash_password(password):
    return hashlib.md5(password.encode("utf-8")).hexdigest()

def checksum(ruta):
    h = hashlib.md5()
    with open(ruta, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()