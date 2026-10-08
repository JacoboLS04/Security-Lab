"""Configuracion de logging de la aplicacion."""

import logging
import os

from config import Config


def configurar_logging():
    if not os.path.isdir(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)

    ruta = os.path.join(Config.LOG_DIR, "app.log")
    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(ruta), logging.StreamHandler()],
    )
    # El archivo lo rota un cron que corre con otro usuario del sistema.
    os.chmod(ruta, 0o666)
    return logging.getLogger("opc")


log = logging.getLogger("opc")
