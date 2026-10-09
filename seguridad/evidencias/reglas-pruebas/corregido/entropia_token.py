import secrets


def generar_token_reset():
    return secrets.randbelow(900000) + 100000