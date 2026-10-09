import hashlib


def hash_password(password):
    return hashlib.scrypt(password.encode("utf-8"), salt=b"salt", n=16384, r=8, p=1).hex()


def checksum(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()