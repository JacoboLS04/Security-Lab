#!/usr/bin/env bash
# =============================================================================
# Preparacion de una VM Debian 11/12 para el despliegue 3.1/3.2 de OPC Tickets.
#
# Uso (como root o con sudo):
#   sudo bash scripts/setup_debian.sh
#
# Hace:
#   1. Instala Docker CE (repositorio oficial de Docker).
#   2. Habilita el servicio Docker en systemd.
#   3. Configura el firewall UFW (SSH + 8080 del balanceador).
#   4. Deja el usuario actual en el grupo `docker`.
#
# Nota AppArmor: en Debian AppArmor esta activo por defecto y Docker ya
# confina los contenedores con sus propios perfiles. No requiere accion extra.
# =============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: ejecutar como root (sudo bash $0)" >&2
    exit 1
fi

. /etc/os-release
case "${ID:-}:${VERSION_CODENAME:-}" in
    debian:bullseye|debian:bookworm)
        CODENAME="${VERSION_CODENAME}"
        ;;
    *)
        echo "ERROR: se esperaba Debian 11 (bullseye) o 12 (bookworm)." >&2
        echo "Detectado: ${PRETTY_NAME:-desconocido}" >&2
        exit 1
        ;;
esac

echo "==> [1/4] Dependencias base"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg

echo "==> [2/4] Repositorio oficial de Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian ${CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> [3/4] Arranque de Docker en systemd"
systemctl enable --now docker

echo "==> [4/4] Firewall UFW (SSH + 8080)"
if command -v ufw >/dev/null 2>&1; then
    ufw allow OpenSSH
    ufw allow 8080/tcp comment "OPC Tickets - Nginx"
    # ufw --force enable activa el firewall y evita el prompt interactivo.
    ufw --force enable
else
    echo "AVISO: ufw no instalado; instalar con 'apt-get install ufw'." >&2
fi

if [ -n "${SUDO_USER:-}" ]; then
    echo "==> Añadiendo '${SUDO_USER}' al grupo docker"
    usermod -aG docker "$SUDO_USER"
fi

echo
echo "Listo. Verificar:"
echo "  docker --version && docker compose version"
echo "  sudo ufw status verbose"
echo
echo "Siguientes pasos (desde el directorio del repositorio clonado):"
echo "  cd infraestructura"
echo "  cp .env.example .env   # y ajustar APP_SECRET_KEY"
echo "  docker compose up -d --build"