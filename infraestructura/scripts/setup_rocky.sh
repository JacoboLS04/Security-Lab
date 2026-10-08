#!/usr/bin/env bash
# =============================================================================
# Preparacion de una VM Rocky Linux 8/9 (o AlmaLinux/RHEL) para el despliegue
# 3.1/3.2 de OPC Tickets.
#
# Uso (como root o con sudo):
#   sudo bash scripts/setup_rocky.sh
#
# Hace:
#   1. Instala Docker CE (repositorio oficial: usa el canal "centos", el
#      estandar para derivados de RHEL).
#   2. Habilita el servicio Docker en systemd.
#   3. Configura firewalld (SSH + 8080 del balanceador).
#   4. Deja el usuario actual en el grupo `docker`. SELinux permanece
#      ENFORCING: no se relaja, el compose ya etiqueta los volumenes con :z.
# =============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: ejecutar como root (sudo bash $0)" >&2
    exit 1
fi

. /etc/os-release
case "${ID:-}" in
    rocky|almalinux|rhel|centos)
        : # distribucion RHEL-compatible
        ;;
    *)
        echo "ERROR: se esperaba Rocky/AlmaLinux/RHEL." >&2
        echo "Detectado: ${PRETTY_NAME:-desconocido}" >&2
        exit 1
        ;;
esac

echo "==> [1/4] Repositorio oficial de Docker"
if command -v dnf >/dev/null 2>&1; then
    dnf -y install dnf-plugins-core
    dnf -y config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
else
    echo "ERROR: no se encuentra dnf." >&2
    exit 1
fi

echo "==> [2/4] Instalacion de Docker"
dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> [3/4] Arranque de Docker y firewalld"
systemctl enable --now docker
systemctl enable --now firewalld

echo "==> [4/4] Firewall (SSH + 8080) y grupo docker"
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG docker "$SUDO_USER"
fi

echo
echo "Estado de SELinux (debe permanecer Enforcing):"
getenforce || true

echo
echo "Listo. Verificar:"
echo "  docker --version && docker compose version"
echo "  firewall-cmd --list-ports"
echo
echo "Siguientes pasos (desde el directorio del repositorio clonado):"
echo "  cd infraestructura"
echo "  cp .env.example .env   # y ajustar APP_SECRET_KEY"
echo "  docker compose up -d --build"
echo
echo "Nota SELinux: el volumen de nginx usa la opcion :z, que Docker etiqueta"
echo "como container_file_t automaticamente. Si montaras volumenes propios,"
echo "tendrias que etiquetarlos con: chcon -Rt container_file_t <ruta>"