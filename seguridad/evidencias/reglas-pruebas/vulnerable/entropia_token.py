import random
import time

def generar_token_reset():
    random.seed(int(time.time()))
    return str(random.randint(100000, 999999))