import os
import subprocess

# command injection
def ping(host):
    subprocess.check_output("ping -c 1 " + host, shell=True, stderr=subprocess.STDOUT, timeout=10)

def convertir(formato, ruta):
    cmd = "libreoffice --headless --convert-to " + formato + " " + ruta
    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

def limpiar():
    os.system("rm -f /tmp/x.bak")

def tarea(interna):
    subprocess.getoutput(interna)