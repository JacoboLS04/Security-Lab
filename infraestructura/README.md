# Infraestructura · OPC Tickets (Prueba técnica §3.1 y §3.2)

Despliegue con **alta disponibilidad** de la API `opc-tickets` (backend Flask de
`../app-vulnerable/backend`) usando **Docker Compose**, probado en **Debian 12**
y **Rocky Linux 9**, con **persistencia de datos mediante Docker named volumes**.

Este directorio es infraestructura: consume la aplicación original tal cual (la
única modificación, mínima y opt-in, se documenta en §1).

> Alcance: secciones 3.1 (balanceo con Docker) y 3.2 (multi-distribución).
> Este README es la guía didáctica y de operación, portable entre **Windows y
> Linux** (§3) y con la **persistencia** explicada (§13).

---

## Regla definitiva (quién hace qué)

```
            YO (manual)                          PROYECTO (automatizado)
   ┌───────────────────────────────┐   ┌──────────────────────────────────────┐
   │  ISO  →  VirtualBox  →  VM    │   │  setup_*.sh: Docker + firewall + SO  │
   │  (creación de la VM)          │   │  docker compose: Nginx + app1 + app2  │
   └───────────────────────────────┘   └──────────────────────────────────────┘
```

- **YO creo las VMs**: descargo la ISO y la creo a mano en VirtualBox.
  El proyecto **no** crea VMs, no usa Vagrant, no usa `VBoxManage`, no monta
  ISOs automáticamente, no automatiza la instalación.
- **Los scripts preparan las VMs**: `scripts/setup_debian.sh` y
  `scripts/setup_rocky.sh` se ejecutan en una VM que **ya existe y está
  instalada**; dejan Docker y firewall listos.
- **Docker despliega y persiste**: `docker compose up` levanta Nginx (balanceo),
  las 2 réplicas y los **named volumes** de datos (§13).

---

## Índice

1. [Estructura y separación](#1-estructura-y-separación)
2. [Flujo completo (9 fases)](#2-flujo-completo-9-fases)
3. [Compatibilidad Windows/Linux · ¿dónde se ejecuta cada comando?](#3-compatibilidad-windowslinux--dónde-se-ejecuta-cada-comando)
4. [FASE 1 · Descargar la ISO](#4-fase-1--descargar-la-iso)
5. [FASE 2 · Crear la VM manualmente en VirtualBox](#5-fase-2--crear-la-vm-manualmente-en-virtualbox)
   - 5.1 Especificaciones y por qué
   - 5.2 Red VirtualBox: NAT + Host-Only
   - 5.3 VirtualBox GUI · Debian 12
   - 5.4 VirtualBox GUI · Rocky Linux 9
6. [FASE 3 · Instalar el sistema operativo](#6-fase-3--instalar-el-sistema-operativo)
7. [FASE 4 · Configurar SSH](#7-fase-4--configurar-ssh)
8. [FASE 5 · Preparar el SO (`setup_debian.sh` / `setup_rocky.sh`)](#8-fase-5--preparar-el-so-setup_debiansh--setup_rockysh)
9. [FASE 6 · Clonar el repositorio](#9-fase-6--clonar-el-repositorio)
10. [FASE 7 · Docker Compose](#10-fase-7--docker-compose)
11. [FASE 8 · Arquitectura: Nginx + 2 réplicas](#11-fase-8--arquitectura-nginx--2-réplicas)
12. [FASE 9 · Pruebas: balanceo, healthchecks y failover](#12-fase-9--pruebas-balanceo-healthchecks-y-failover)
13. [Persistencia con Docker volumes](#13-persistencia-con-docker-volumes)
14. [Didáctica · Puertos y direcciones](#14-didáctica--puertos-y-direcciones)
15. [Didáctica · `compose.yaml` explicado bloque a bloque](#15-didáctica--composeyaml-explicado-bloque-a-bloque)
16. [Didáctica · `nginx.conf` explicado bloque a bloque](#16-didáctica--nginxconf-explicado-bloque-a-bloque)
17. [Didáctica · Glosario de conceptos](#17-didáctica--glosario-de-conceptos)
18. [Diferencias Debian vs Rocky/RHEL](#18-diferencias-debian-vs-rockyrhel)
19. [Estructura final, archivo por archivo](#19-estructura-final-archivo-por-archivo)

---

## 1. Estructura y separación

```
proyecto-total/
├── app-vulnerable/            # Aplicacion original (casi intacta, ver nota)
│   ├── backend/
│   └── frontend/
├── .dockerignore              # Config de BUILD Docker (raiz = contexto de build)
└── infraestructura/           # Todo lo de 3.1 / 3.2
    ├── compose.yaml           # 2 replicas + Nginx + named volumes
    ├── .env.example           # Variables (copiar a .env)
    ├── .gitignore             # Oculta .env e ISO (secretos/peso)
    ├── deploy/
    │   └── nginx.conf         # Balanceador (config completa, no-root)
    ├── docker/
    │   └── backend/
    │       └── Dockerfile     # Imagen no-root multi-stage
    ├── scripts/
    │   ├── setup_debian.sh    # Preparacion del SO (Docker + UFW)
    │   └── setup_rocky.sh     # Preparacion del SO (Docker + firewalld/SELinux)
    ├── iso/
    │   └── README.md          # ISOs recomendadas y como verificarlas
    └── README.md              # Esta documentacion
```

**Nota de auditoría (única modificación a la aplicación):**
`app-vulnerable/backend/config.py` recibe una variable opcional `APP_DATA_DIR`
que redirige los datos (SQLite, adjuntos, exportaciones, logs) a una carpeta fija
`/app/data` para poder montar el volume de persistencia (§13). **Sin la variable
el comportamiento original no cambia** (datos junto al código). No se ha tocado
ningún otro archivo de la app (ni `app.py`, ni endpoints, ni el balanceo, que se
demuestra sin tocar código). El `Dockerfile` de infraestructura crea `/app/data`.

## 2. Flujo completo (9 fases)

```
FASE 1   Descargar ISO (debian-12 / rocky-9)           [HOST]
  ↓
FASE 2   Crear VM manualmente en VirtualBox (GUI)      [HOST]
  ↓
FASE 3   Instalar Debian 12 / Rocky Linux 9            [VM]
  ↓
FASE 4   Configurar SSH (host → VM)                    [HOST → VM]
  ↓
FASE 5   Ejecutar setup (setup_debian.sh / .rocky.sh)  [SSH · VM]
  ↓
FASE 6   Clonar repositorio dentro de la VM            [SSH · VM]
  ↓
FASE 7   docker compose up -d --build                  [SSH · VM]
  ↓
FASE 8   Nginx balanceando entre app1 + app2           [SSH · VM]
  ↓
FASE 9   Pruebas (X-Replica, failover, persistencia)   [SSH · VM / HOST]
```

Las fases **1 y 2 son manuales y no se automatizan**. De la **5 en adelante**
intervienen scripts y Docker.

## 3. Compatibilidad Windows/Linux · ¿dónde se ejecuta cada comando?

**Regla: nada de este proyecto exige que el equipo anfitrión sea Linux.** Toda la
parte "Linux" (apt/dnf/docker/git) ocurre **dentro de las VMs** a las que te
conectas por SSH; en el host solo haces: GUI de VirtualBox, descargas de ISO y,
opcionalmente, `docker compose` / `curl`.

### 3.1 Etiqueta que usan todas las secciones

| Etiqueta | Dónde se ejecuta el comando |
|---|---|
| `[HOST]` | Equipo anfitrión (**Windows o Linux**): VirtualBox (GUI), descargas, curl de verificación |
| `[HOST·Win]` / `[HOST·Linux]` | Solo Windows / solo Linux (cuando difieren) |
| `[SSH · VM]` | **Dentro** de la VM **Linux** (terminal que te devolvió `ssh opc@...`) |
| `[Contenedor]` | Dentro de un contenedor Docker (`docker exec ...`) |

### 3.2 Qué se hace en cada lugar

| Acción | Dónde | Comandos |
|---|---|---|
| Descargar ISO | `[HOST]` | navegador (ver §4) |
| Crear/administrar VM | `[HOST]` | **GUI de VirtualBox** (idéntica en Windows y Linux) |
| Instalar el SO | `[VM]` | asistente gráfico |
| Ver IP, apt/dnf, systemctl, ssh, docker, git | `[SSH · VM]` | comandos **Linux normales** (si estás en SSH a una VM Debian/Rocky, no hay problema con `bash`, `chmod`, `ip`, etc.) |
| `setup_debian.sh` / `setup_rocky.sh` | `[SSH · VM]` | `sudo bash scripts/setup_debian.sh` (se invoca con `bash`, **no requiere `chmod +x`** ni Bash en el host) |
| `docker compose up -d --build` | `[SSH · VM]` | dentro de la VM (ruta recomendada del ejercicio) |
| `curl http://localhost:8080/...` | `[HOST]` o `[SSH · VM]` | ver nota de Windows en 3.3 |

> Si prefieres desplegar en tu host (Docker Desktop en Windows o Docker Engine
> en Linux) en vez de en la VM, funciona igual: el `compose.yaml` y los named
> volumes son **idénticos** en ambos. El ejercicio prefiere la VM para que se
> pruebe sobre Debian/Rocky (§3.2).

### 3.3 Diferencias Windows vs Linux (breves)

| Tema | Windows | Linux |
|---|---|---|
| Docker | **Docker Desktop** (backend WSL2) + Compose v2 incluido | Docker Engine + `docker-compose-plugin` |
| `curl` | En PowerShell, `curl` es alias de `Invoke-WebRequest` → usar **`curl.exe`** | `curl` normal |
| Bash/sed/grep | **No hacen falta en el host** (todo eso ocurre dentro de la VM por SSH) | no hacen falta tampoco (se usan dentro de la VM) |
| Separador de rutas | El bind `./deploy/nginx.conf` es **relativo** → Compose lo resuelve igual en Windows y Linux | igual |
| `:z` en volúmenes | Docker Desktop (sin SELinux) **ignora** la opción `z` | en VM Rocky (SELinux) etiqueta el archivo (`:z`); en Debian se ignora |

**No dependes en el host de**: Bash, `chmod`, `sed`, `grep`, rutas `/home/...`,
etc. Todos aparecen solo en `[SSH · VM]` (Linux dentro de la VM, que es correcto).

---

## 4. FASE 1 · Descargar la ISO

`[HOST]` · Las ISOs se descargan manualmente; el proyecto nunca lo hace. Detalle
en `iso/README.md`.

| Distribución | ISO recomendada | Origen oficial |
|---|---|---|
| Debian 12 | **Debian 12 netinst** (amd64) | <https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/> |
| Rocky Linux 9 | **Rocky 9 Minimal** (x86_64) | <https://rockylinux.org/download> |

- Verificar integridad con el `SHA256SUMS` oficial
  (`[HOST·Linux] sha256sum -c ...` / `[HOST·Win] Get-FileHash ...`).
- Si las quieres junto al proyecto: `infraestructura/iso/*.iso`. **No se suben a
  Git** (`iso/*.iso` en `.gitignore`).
- El proyecto **no depende** de su existencia: son el medio de instalación.

## 5. FASE 2 · Crear la VM manualmente en VirtualBox

### 5.1 Especificaciones y por qué

| Recurso | Valor | Por qué |
|---|---|---|
| CPU | **1 vCPU** | El objetivo es ejecutar Docker y demostrar el despliegue, no atender carga de producción. Docker Engine + 2 réplicas Flask + Nginx no-root funcionan holgados en 1 vCPU. |
| RAM | **1 GiB** | Docker + las imágenes (python slim + nginx, y el build con los wheels) caben sobradas en 1 GiB; da margen a bash y healthchecks sin comprometer el host. |
| Disco | **10 GiB** (VDI dinámico) | SO base (~2–3 GiB) + Docker/imágenes (~2–3 GiB) + repo quedan en ~6 GiB; 10 GiB da margen. VDI **dinámico** = solo ocupa lo usado. |

**Igual en Debian y Rocky** (mismo lab, misma carga).

### 5.2 Red VirtualBox: NAT + Host-Only

```
                 HOST
                  │
          ┌───────┴────────┐
          │                 │
        NAT             Host-Only
          │                 │
      Internet          HOST ↔ VM
          │                 │
          └────── VM ───────┘
```

| Adaptador | Red | Direcciones | Para qué |
|---|---|---|---|
| 1 | **NAT** | VM `10.0.2.15` · host `10.0.2.2` | Internet para la VM (instalación + pull de imágenes). La VM sale; nadie entra. |
| 2 | **Host-Only** | VM `192.168.56.x` · host `192.168.56.1` | SSH host→VM y probar el balanceo, sin exponer a la LAN. |

- **¿Por qué ambos?** Solo NAT = Internet sin acceso SSH; solo Host-Only = SSH sin
  Internet para instalar. Con los dos tienes "VM con Internet y administrable".
- **No se automatiza**: se configura en la GUI. Prepáralo en VirtualBox:
  `File → Tools → Network Manager → Host-only Networks → Create` (queda
  `vboxnet0`, `192.168.56.1/24`; VirtualBox pone DHCP en `192.168.56.2–254`).

**Comprobar la IP dentro de Linux** `[SSH · VM]`:

```bash
ip -4 addr show
# enp0s3 -> 10.0.2.15 (NAT, Internet)
# enp0s8 -> 192.168.56.x (Host-Only, SSH)
```

**Conectarse por SSH desde el host** `[HOST]`:

```bash
ssh opc@192.168.56.x
# en Windows PowerShell funciona lo mismo (cliente OpenSSH integrado)
```

### 5.3 VirtualBox GUI · Debian 12

`[HOST]` (GUI)

| Campo | Selección |
|---|---|
| Name | `opc-debian` |
| Type / Version | Linux · **Debian (64-bit)** (arquitectura amd64 = la ISO) |
| Memory | 1024 MiB · **Processors: 1** |
| Hard disk | Create a virtual hard disk now → **VDI** → *Dynamically allocated* → **10,00 GiB** |

**Settings → System**: Boot Order: **Optical** primero, luego **Hard Disk**
(arranca el instalador de la ISO y después el disco). *Enable I/O APIC* **ON**
(64-bit), *Enable PAE/NX* **ON**, *Enable VT-x/AMD-V* **ON** (si falla el arranque,
revisa la virtualización en el BIOS/UEFI real). **Enable EFI: OFF** (BIOS).

**Settings → Storage**: IDE *Empty* → *Choose a disk file...* → `debian-12.iso`.

**Settings → Network**: Adaptador 1 = **NAT** · Adaptador 2 = **Host-only**
`vboxnet0`, *Cable connected*. Display: 16 MB VRAM. Audio/USB: sin uso.

**Start** → la VM arranca desde la ISO (FASE 3).

### 5.4 VirtualBox GUI · Rocky Linux 9

Igual que Debian, con estos cambios:

| Campo | Selección |
|---|---|
| Name | `opc-rocky` |
| Type / Version | Linux · **Red Hat (64-bit)** (x86_64) |
| ISO | `rocky-9.iso` |

Resto idéntico (1024 MiB · 1 vCPU · VDI 10 GiB dinámico · Optical→Hard Disk ·
I/O APIC/VT-x ON · NAT + Host-Only). **Start**.

## 6. FASE 3 · Instalar el sistema operativo

`[VM]`

**Debian 12**: Install → idioma/teclado → red (si reniega la NAT, *Configure
network manually* con `10.0.2.15/24`, gateway `10.0.2.2`, DNS `10.0.2.3`) →
hostname `opc-debian` → usuario `opc` (root configurado: "bloquear") → partición
*Guided - entire disk* → software: **SSH server** (+ standard utilities) → grub →
reboot. Quitar la ISO de la unidad óptica.

**Rocky Linux 9**: *Install* → idioma/teclado → **Installation Destination**:
disco virtual (automático) → **Software Selection: Minimal** → **Network & Host**:
activar conexión con DHCP, hostname `opc-rocky` → **User Creation**: `opc` +
*Make administrator* → aplicación → **Reboot**. Quitar la ISO.

## 7. FASE 4 · Configurar SSH

1. `[SSH · VM]` `ip -4 addr show` → anotar la `192.168.56.x`.
2. `[HOST]` `ssh opc@192.168.56.x`
3. `[HOST]` (opcional) `ssh-copy-id opc@192.168.56.x`

En Debian se instala el "SSH server" en la FASE 3 (o `sudo apt-get install -y
openssh-server`). En Rocky Minimal, SSHD ya viene activo.

## 8. FASE 5 · Preparar el SO (`setup_debian.sh` / `setup_rocky.sh`)

Aquí **empieza la automatización** (la VM ya existe e instalada).

`[SSH · VM]`, desde el directorio del repositorio clonado/preparado:

```bash
sudo bash infraestructura/scripts/setup_debian.sh    # en la VM Debian
sudo bash infraestructura/scripts/setup_rocky.sh     # en la VM Rocky
```

**`setup_debian.sh`** → dependencias (ca-certificates, curl, gnupg) → repo oficial
Docker del codename detectado → `docker-ce` + `docker-compose-plugin` → `systemctl
enable --now docker` → UFW (SSH + 8080) → usuario al grupo `docker`.
*(AppArmor: Docker lo gestiona solo.)*

**`setup_rocky.sh`** → repo Docker (canal `centos`, compatible RHEL) →
`docker-ce` + plugin → `systemctl enable --now docker firewalld` → firewalld
(SSH + 8080) → usuario al grupo `docker`. *(SELinux: queda **Enforcing**; el
etiquetado de volúmenes lo resuelve `:z` en Compose.)*

Ambos **verifican la distribución real** y exigen root/sudo. Se invocan con
`bash` explícito: **no se necesita `chmod +x`** (válido si copias el archivo
desde Windows, puesto que los permisos no viajan con el contenido).

## 9. FASE 6 · Clonar el repositorio

`[SSH · VM]`

```bash
git clone <URL-del-repo>
cd <repo>/infraestructura
cp .env.example .env        # y ajustar APP_SECRET_KEY
```

> Se clona dentro de la VM (filesystem nativo) a propósito: evita problemas de
> etiquetado SELinux con carpetas compartidas de VirtualBox.

## 10. FASE 7 · Docker Compose

`[SSH · VM]`

```bash
docker compose up -d --build
docker compose ps     # opc-app-1, opc-app-2, opc-lb → healthy
docker compose logs -f lb
```

- `--build` construye `opc-backend:local` (Dockerfile de infraestructura); Nginx
  se descarga del registry.
- Compose crea la red privada y los **named volumes** `app-data-1` / `app-data-2`
  (ver §13).

## 11. FASE 8 · Arquitectura: Nginx + 2 réplicas

```
   Cliente ── http://<host>:8080 ─▶ Nginx (opc-lb)
                                      │  upstream: app1:5000  app2:5000
                                      │  round-robin (1-a-1)
                          ┌───────────┴───────────┐
                          ▼                        ▼
                    opc-app-1 (:5000)          opc-app-2 (:5000)
                      volume app-data-1          volume app-data-2
   (red interna de Compose: DNS app1 / app2 · sin puertos publicados)
```

- **Compose, no Swarm** (complejidad innecesaria).
- **`worker_processes 1`**: round-robin estricto y reproducible (§16).
- **Nginx no-root** → escucha en `8080` (no 80). Solo el balanceador publica
  puerto.
- **Persistencia por réplica**: cada app tiene su **propio** named volume (no
  comparten SQLite; ver §13).
- **Prueba del balanceo sin tocar la app**: cabecera `X-Replica: <ip:puerto>`.

## 12. FASE 9 · Pruebas: balanceo, healthchecks y failover

### 12.1 Balanceo

`[SSH · VM]` (los bucles son bash de la VM) o `[HOST]` (un curl suelto):

```bash
curl -si http://localhost:8080/api/health | grep -i x-replica

for i in $(seq 1 10); do curl -si http://localhost:8080/api/health | grep -i x-replica; done
# alterna 172.x.0.2:5000 / 172.x.0.3:5000 (round-robin)

docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' opc-app-1 opc-app-2

docker logs lb        # access log con $upstream_addr
docker logs app1      # peticiones de la replica 1
docker logs app2      # peticiones de la replica 2
docker inspect -f '{{.Config.User}}' opc-app-1   # opc (no root)
```

Endpoints: `curl -s http://localhost:8080/healthz` (Nginx propio) y
`curl -s http://localhost:8080/api/health` (API).

> `[HOST·Win]`: en PowerShell usa `curl.exe -si ...` (o `Invoke-WebRequest`).

### 12.2 Healthchecks

- Réplicas: Python dentro del contenedor → `GET /api/health` a `127.0.0.1:5000`.
  Nginx no arranca hasta que ambas pasan (`depends_on.condition: service_healthy`).
- Balanceador: `wget http://127.0.0.1:8080/healthz` (Nginx sano, sin backend).

```bash
docker compose ps
docker inspect --format '{{json .State.Health}}' opc-app-1
```

### 12.3 Failover

```bash
docker compose stop app1
for i in $(seq 1 8); do curl -si http://localhost:8080/api/health | grep -i x-replica; done
# 100% con la IP de la viva (a veces "ip1:5000, ip2:5000" = reintento de Nginx)

docker compose ps     # app1 "exited"; app2 y lb "healthy"
docker compose start app1 && sleep 20
for i in $(seq 1 8); do curl -si http://localhost:8080/api/health | grep -i x-replica; done
```

## 13. Persistencia con Docker volumes

### 13.1 Por qué existe

La aplicación **genera datos persistentes**: SQLite (`tickets.db`), adjuntos,
exportaciones y logs. Sin nada que los guarde, todo vive en el sistema de
archivos del contenedor y **desaparece** al recrearlo (`up -d` tras cambio de
imagen/`rm`). Con **Docker named volumes** los datos viven en un "disco" que
gestiona Docker y **sobrevive** al ciclo de vida del contenedor. Funcionan igual
en **Docker Desktop (Windows)** y **Docker Engine (Linux)**.

Implementación (sin tocar más que un detalle de la app):
- `config.py` respeta la variable opcional **`APP_DATA_DIR`** (raíz de datos).
- `compose.yaml` la fija a `/app/data` y monta un named volume ahí.
- El `Dockerfile` crea `/app/data` con dueño `opc` (para que el proceso no-root
  escriba en el volumen; Docker conserva dueño/permisos al inicializarlo).

### 13.2 Qué volúmenes existen

| Nombre | Dónde se declara | Se monta en | Lo monta |
|---|---|---|---|
| `app-data-1` | bloque `volumes:` de `compose.yaml` | `/app/data` | `opc-app-1` |
| `app-data-2` | ídem | `/app/data` | `opc-app-2` |

Son **named volumes** (raíz `volumes:` de Compose), no anónimos: tienen nombre
estable y se pueden ver con `docker volume ls`.

### 13.3 Qué datos almacena cada uno

El árbol `/app/data` completo de esa réplica:

```
/app/data/
├── tickets.db        # base SQLite (usuarios, tickets, comentarios, auditoria)
├── adjuntos/         # archivos subidos a los tickets
├── exportaciones/    # reportes exportados
└── logs/             # app.log de esa replica
```

**No** se monta el código de la aplicación: la app sigue en la imagen (recrear el
contenedor no re-descarga ni re-copia fuentes). Tampoco se usan bind mounts de
datos: los named volumes son portables (Windows/Linux) sin rutas de host.

### 13.4 ¿Por qué un volumen por réplica y no compartido?

**Porque la app usa SQLite.** Dos procesos escribiendo el mismo archivo SQLite
provocan bloqueos (`database is locked`) y corrupción. Por eso `app1` y `app2`
**no comparten** volumen: cada una persiste su propia base.

> **Limitación (documentada):** con esto, un ticket creado vía `app1` no se ve
> vía `app2` (bases independientes). Para el ejercicio de balanceo/HA es
> correcto (réplicas autocontenidas, como sin volumen). **En producción** la
> aplicación debería usar una **base de datos externa compartida** (Postgres/MySQL)
> fuera de las réplicas. Eso queda **fuera del alcance** de la prueba (no se
> añaden Swarm/Kubernetes/cachés solo por persistir).

### 13.5 ¿Qué ocurre con cada operación?

| Operación | ¿Toca los named volumes? | Consecuencia |
|---|---|---|
| `docker compose down` | **No** | Para y elimina contenedores y la red. Los volúmenes `app-data-*` **quedan intactos**. |
| `docker compose up -d` | **No** | Reutiliza los mismos volúmenes: los datos vuelven a aparecer montados en `/app/data`. |
| Recreación de un contenedor (cambio de imagen/`up --build`) | **No** | Contenedor nuevo + **mismo** volumen: los datos sobreviven. |
| `docker compose down -v` | **SÍ (borra)** | `-v` elimina los volúmenes declarados en Compose → **datos perdidos definitivamente**. El siguiente `up` crea volúmenes vacíos y la app genera una DB limpia (con los datos de demo de `init_db`). |
| `docker rm` / `docker compose rm` | **No** | Borra el contenedor, no el volumen. |

> `-v` de `down` también borra volúmenes **anónimos**; los named se conservan si
> no se usa `-v`. En `down --volumes` no hay diferencia: es el mismo flag.

### 13.6 Cómo comprobar que los datos persisten

`[SSH · VM]` (Docker dentro de la VM):

```bash
# 1) los volúmenes existen
docker volume ls | grep app-data

# 2) el montaje está vivo dentro del contenedor
docker exec opc-app-1 ls -la /app/data      # tickets.db, adjuntos/, exportaciones/, logs/

# 3) prueba real: marca un ticket, apaga, enciende, verifica que sigue
docker exec opc-app-1 python -c \
  "import sqlite3;c=sqlite3.connect('/app/data/tickets.db');\
  c.execute(\"INSERT INTO tickets (codigo,solicitante,desarrollador,estado)\
  VALUES ('PERSIST-TEST','tester','qa','demo')\");c.commit();\
  print('tickets=',c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])"

docker compose down
docker compose up -d
docker exec opc-app-1 python -c \
  "import sqlite3;c=sqlite3.connect('/app/data/tickets.db');\
  print('tickets=',c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])"
# -> el contador debe ser EL MISMO (p. ej. 8) tras down/up

# 4) separación entre réplicas: app1 tiene su DB, app2 la suya
docker exec opc-app-1 python -c "import sqlite3;c=sqlite3.connect('/app/data/tickets.db');print(c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])"
docker exec opc-app-2 python -c "import sqlite3;c=sqlite3.connect('/app/data/tickets.db');print(c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])"
# -> normalmente difieren (p. ej. app1=8, app2=7)

# 5) solo down -v borra (¡destructivo!)
docker compose down -v    # volúmenes app-data-* eliminados
docker volume ls          # ya no aparecen
```

## 14. Didáctica · Puertos y direcciones

### 14.1 El formato `HOST:CONTENEDOR`

`ports` se escribe **`"host:container"`**. Ejemplo genérico:

```yaml
ports:
  - "8080:80"
```

- **8080** → puerto del HOST.
- **80** → puerto del CONTENEDOR.

Flujo:

```text
http://localhost:8080
       ↓  (llega al puerto 8080 del host)
    Host:8080
       ↓  (Docker lo redirige)
Container:80
       ↓
     Nginx
```

En este proyecto el valor real es `"8080:8080"` porque usamos la imagen
`nginxinc/nginx-unprivileged` (no-root), que **no puede abrir puertos < 1024**:
Nginx escucha en 8080 dentro del contenedor. (Con la imagen Nginx normal/root
sería `8080:80`.)

### 14.2 `localhost`, `0.0.0.0`, `127.0.0.1`

- **`localhost`** = "este equipo". En `http://localhost:8080` lo usas en el host
  (Docker publicó el puerto) o en la propia VM.
- **`0.0.0.0`** = "todas las interfaces". La API escucha en `0.0.0.0:5000`
  **dentro del contenedor** para ser alcanzable en la red interna (no solo
  desde sí misma).
- **`127.0.0.1`** = loopback del **propio contenedor**: los healthchecks llaman a
  `127.0.0.1:5000` dentro de cada réplica y a `127.0.0.1:8080` dentro de Nginx.

```text
localhost:8080  →  publica  →  0.0.0.0:8080 (host)  →  172.x.0.x:8080 (lb)
127.0.0.1:5000  →  dentro de app1/app2 (healthcheck)
```

## 15. Didáctica · `compose.yaml` explicado bloque a bloque

```yaml
name: opc-tickets
```
- Nombre del proyecto Compose: prefija la red (`opc-tickets_default`) y cualquier
  recurso sin nombre explícito; identidad estable.

```yaml
x-app-base: &app-base
  image: opc-backend:local
  build:
    context: ..
    dockerfile: infraestructura/docker/backend/Dockerfile
  env_file: [ .env ]
  environment:
    FLASK_DEBUG: "0"
    APP_DATA_DIR: /app/data
  restart: unless-stopped
  cap_drop: [ ALL ]
  security_opt: [ no-new-privileges:true ]
  deploy:
    resources: { limits: { cpus: "0.50", memory: 256M } }
```
- Anclas YAML (`&app-base` / `<<:`) para no duplicar la base de las 2 réplicas.
- `build.context: ..` → el contexto es la **raíz del repo** (Docker exige el
  Dockerfile dentro del contexto); el Dockerfile copia solo `app-vulnerable/backend`.
- `APP_DATA_DIR=/app/data` → apunta a la raíz de datos sobre la que se monta el
  volumen (§13).
- `restart`/`cap_drop`/`no-new-privileges`/límites: ver §17.

```yaml
services:
  app1:
    <<: *app-base
    container_name: opc-app-1
    volumes:
      - app-data-1:/app/data      # named volume PRIVADO de app1
    healthcheck:
      test: [CMD, python, -c, >-
             import urllib.request,sys;
             sys.exit(0 if
             urllib.request.urlopen('http://127.0.0.1:5000/api/health',
             timeout=5).getcode()==200 else 1)]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
```
- `volumes: - app-data-1:/app/data` → monta el named volume **de esta réplica**
  (§13.2). `app2` usa `app-data-2`.
- Healthcheck: Python del contenedor hace `GET /api/health` a `127.0.0.1:5000`.
  `start_period: 20s` da margen al arranque de Flask.

```yaml
  lb:
    image: nginxinc/nginx-unprivileged:1.27-alpine
    container_name: opc-lb
    ports: ["8080:8080"]
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf:ro,z
    depends_on:
      app1: { condition: service_healthy }
      app2: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
    deploy:
      resources: { limits: { cpus: "0.10", memory: 64M } }

volumes:
  app-data-1: { name: app-data-1 }
  app-data-2: { name: app-data-2 }
```
- `ports` solo en `lb` (las réplicas no publican nada).
- Bind mount `:ro,z` = configuración del balanceador (no es un volumen de datos;
  ver §17 `volumes`).
- `depends_on` + `service_healthy`: Nginx espera a que **respondan** las réplicas.
- Bloque `volumes:` (raíz): declara y **da nombre** a los volúmenes persistentes.

## 16. Didáctica · `nginx.conf` explicado bloque a bloque

```nginx
worker_processes 1;
```
- Un único worker → round-robin **estricto** y predecible (con `auto`, cada worker
  lleva su contador y las ráfagas cortas se sesgan).

```nginx
error_log  /var/log/nginx/error.log notice;
pid        /tmp/nginx.pid;
```
- No-root: solo puede escribir en `/tmp`. Los logs van luego a `stdout`/`stderr`.

```nginx
events { worker_connections 1024; }
```

```nginx
http {
  proxy_temp_path /tmp/...; ...         # temporales en /tmp (no-root)
  include /etc/nginx/mime.types;
  default_type application/octet-stream;

  log_format opc_format '$remote_addr - $upstream_addr "$request" $status '
                        'upstream_time=$upstream_response_time';
  access_log /dev/stdout opc_format;
  error_log  /dev/stderr notice;
```
- `$upstream_addr` en el log = IP de la réplica que respondió: evidencia del
  balanceo. `stdout`/`stderr` para `docker compose logs lb`.

```nginx
  upstream opc_backend {
      server app1:5000;
      server app2:5000;
  }
```
- Grupo **upstream**; `app1`/`app2` son los DNS de Compose; `5000` el puerto Flask.
- Sin `weight`/`least_conn` → **round-robin** (el que demostramos).

```nginx
  server {
      listen 8080;
      server_name _;

      location = /healthz { access_log off; return 200 "ok\n"; }

      location / {
          proxy_pass http://opc_backend;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
          proxy_connect_timeout 5s;
          proxy_read_timeout 30s;
          add_header X-Replica $upstream_addr always;
      }
  }
```
- `listen 8080` (>= 1024, no-root); `_` acepta cualquier Host.
- `/healthz` = salud del **propio** balanceador (healthcheck de `lb`).
- `proxy_pass http://opc_backend` → reenvía al upstream (round-robin).
- Cabeceras `Host`/`X-Forwarded-*` para que el backend vea al cliente real.
- **`add_header X-Replica $upstream_addr always`** → cabecera de respuesta con la
  réplica: prueba de balanceo **sin tocar la app**.

## 17. Didáctica · Glosario de conceptos

> Formato: **Qué es → para qué sirve → por qué lo usamos → qué pasa si lo
> quitamos.**

### `ports`
Qué es: mapeo `host:container` que publica un puerto. Para qué: acceder al
servicio desde fuera del contenedor. Por qué: solo en `lb` (`8080:8080`). Si lo
quitamos: el balanceador queda inaccesible desde el host.

### `expose` / ausencia de `ports`
Qué es: declaración documental de un puerto interno **sin publicarlo**. Para qué:
señalar "aquí escucha esto" en la red interna. Por qué: las réplicas solo deben
ser alcanzables por Nginx (vía DNS interno). Si lo quitamos/no existe: las
réplicas ya no publican nada; el cambio es informativo.

### `depends_on`
Qué es: orden de arranque. Para qué: levantar en orden de dependencia. Por qué:
Nginx sin réplicas no tiene sentido. Si lo quitamos: arranque en paralelo y
posibles 502s transitorios.

### `depends_on` + `condition: service_healthy`
Qué es: esperar a que la dependencia esté **sana** (healthcheck OK), no solo a que
arranque. Para qué: eliminar la ventana en que lb existe pero backend aún no
responde. Por qué: es la *readiness* que ofrece Compose v2. Si lo quitamos:
`depends_on` clásico = solo espera al arranque del proceso.

### `healthcheck`
Qué es: comando periódico dentro del contenedor que marca `healthy`/`unhealthy`.
Para qué: conocer el estado real (servicio responde), no solo del proceso. Por
qué: réplicas (`GET /api/health`) y Nginx (`wget /healthz`). Si lo quitamos: no
habría `service_healthy` y el estado real se pierde.

### `restart: unless-stopped`
Qué es: política de reinicio del daemon. Para qué: levantar el contenedor si cae
o al reiniciar el host. Por qué: HA básica sin orquestador. Si lo quitamos: un
contenedor caído se queda parado hasta que lo subas.

### `env_file`
Qué es: archivo de variables inyectadas como entorno. Para qué: config/secretos
fuera del manifiesto y del código. Por qué: `.env` (gitignorado) aporta
`APP_SECRET_KEY` y `FLASK_DEBUG`. Si lo quitamos: faltan variables (secreto
vacío → la app usa el fallback de `config.py`).

### `volumes` (named volume)
Qué es: montaje gestionado por Docker (raíz `volumes:` de Compose) en una ruta del
contenedor; los datos viven fuera de la imagen y del contenedor. Para qué:
**persistencia** (§13). Por qué: `app-data-1`/`app-data-2` en `/app/data`.
Si lo quitamos: cada recreación de la réplica **borra los datos** (SQLite,
adjuntos, exportaciones, logs) → contenedores 100 % efímeros.

### `volumes` (bind mount `:ro,z`)
Qué es: monta un archivo del host (config). Para qué: dar configuración sin
rebuild. Por qué: `./deploy/nginx.conf → /etc/nginx/nginx.conf:ro,z`. `ro` =
solo lectura (los contenedores no lo modifican); `z` = etiquetado SELinux (en
Rocky; en Debian/Docker Desktop se ignora). Si lo quitamos: Nginx usa su
configuración por defecto (sin `X-Replica`, sin `upstream`, sin `/healthz`).

### `cap_drop`
Qué es: elimina *capabilities* de Linux. Para qué: mínimo privilegio. Por qué:
`cap_drop: [ALL]` en los 3. Si lo quitamos: el proceso conserva capabilities de
la imagen (superficie de ataque mayor).

### `no-new-privileges` (`security_opt`)
Qué es: impide elevar privilegios vía setuid/setgid. Para qué: complementa
`cap_drop`. Por qué: `no-new-privileges:true`. Si lo quitamos: binarios con
setuid podrían escalar.

### `user` (Dockerfile)
Qué es: usuario del proceso (directiva `USER`). Para qué: no correr como root.
Por qué: `USER opc` (backend) e imagen nginx no-root (uid 101). Si lo quitamos:
el contenedor corre como root (mayor impacto de una explotación).

### `cpus` y `mem_limit` (`deploy.resources.limits`)
Qué es: límites de CPU/memoria. Para qué: acotar consumo. Por qué: réplicas
0.50/256M; lb 0.10/64M (cabida en la VM 1 vCPU/1 GiB). Si lo quitamos: un pico de
memoria puede tumbar la VM. *(En la sintaxis v2 clásica eran `cpus`/`mem_limit`
a nivel de servicio: mismo concepto.)*

### Redes Docker
Qué es: red `bridge` privada del proyecto con DNS por nombre de servicio. Para
qué: que `app1`/`app2`/`lb` se encuentren por nombre y nada externo llegue a las
réplicas. Por qué: todo el descubrimiento del deploy (upstream) se apoya en ella.
Si la quitamos: `app1:5000` no resuelve → 502.

### `upstream`
Qué es: bloque de Nginx que agrupa backends. Para qué: definir el conjunto al que
`proxy_pass` reparte. Por qué: `app1:5000` + `app2:5000`. Si lo quitamos: no hay
a quién repartir → sin balanceo.

### `proxy_pass`
Qué es: directiva que reenvía la petición a un upstream/URL. Para qué: proxy
inverso (el cliente habla con Nginx). Por qué: `proxy_pass http://opc_backend`.
Si lo quitamos: Nginx no reenvía (404/estáticos).

### `round-robin`
Qué es: algoritmo por defecto que reparte en orden cíclico. Para qué: carga
repartida y predecible. Por qué: permite la demo `app1, app2, app1…`. Si lo
cambiamos a `least_conn`/`ip_hash`: reparto no 1-a-1 (evidencia visual peor).

### `app1` / `app2`
Qué es: nombres de servicio de Compose (`opc-app-1`/`opc-app-2`). Para qué:
identificarlos y **resolverlos por DNS** en la red interna. Por qué: el upstream
se escribe con ellos, no con IPs. Si los renombramos: hay que tocar upstream y
logs (y el DNS derivado).

### `5000`
Puerto **interno** de Flask. Nunca se publica en el host (§14.1).

### `8080` / `80`
`8080` (host) → `8080` (contenedor, imagen no-root). `80` sería el típico si la
imagen corriera como root (§14.1).

### `localhost`
"Este equipo". Sirve para probar el balanceo publicado (§14.2).

### `0.0.0.0`
"Todas las interfaces". La API escucha ahí dentro del contenedor (§14.2).

### `127.0.0.1`
Loopback del propio contenedor; base de los healthchecks (§14.2).

### `:z`
Opción de montaje SELinux (ver "volumes (bind mount)"). También aquí: `:ro`
funciona en todos; `:z` solo afecta a SELinux (Rocky).

### `APP_DATA_DIR`
Variable de entorno que `config.py` respeta para ubicar los datos persistentes.
Compose la pone a `/app/data`, donde se monta el named volume (§13). Sin ella, la
app usa la carpeta del código (comportamiento original).

## 18. Diferencias Debian vs Rocky/RHEL

| Aspecto | Debian 11/12 | Rocky/AlmaLinux/RHEL |
|---|---|---|
| Gestor de paquetes | `apt` / `.deb` | `dnf` / `.rpm` |
| Firewall | `ufw` | `firewalld` |
| LSM | AppArmor (Docker lo gestiona) | SELinux Enforcing (`:z` en volúmenes) |
| Repo Docker | `linux/debian` (codename) | `linux/centos` (canal RHEL) |
| systemd | `systemctl enable --now docker` | idéntico |
| Detección en scripts | `ID` + `VERSION_CODENAME` | `ID` (rocky/almalinux/rhel) |

**No cambia entre distribuciones**: el Dockerfile, `compose.yaml` y `nginx.conf`
(incluidos volúmenes y `:z`). Solo cambia la preparación del SO (FASE 5).

## 19. Estructura final, archivo por archivo

| Archivo | Qué es | Quién lo usa | Qué pasa si lo borras |
|---|---|---|---|
| `infraestructura/compose.yaml` | Manifiesto (réplicas + lb + **volúmenes**) | `docker compose up` | No hay despliegue ni persistencia |
| `infraestructura/.env.example` | Plantilla de variables | Humano (`cp`) | No sabes qué configurar |
| `infraestructura/.env` | Variables reales (gitignorado) | `env_file:` | App sin secretos reales |
| `infraestructura/.gitignore` | Ignora `.env` e `*.iso` | Git | Subirías secretos/binarios pesados |
| `infraestructura/deploy/nginx.conf` | Config completa del balanceador | `opc-lb` (`:ro,z`) | Nginx por defecto: sin `X-Replica` ni `upstream` |
| `infraestructura/docker/backend/Dockerfile` | Imagen no-root multi-stage (+ crea `/app/data`) | Build de Compose | No se construye la imagen |
| `infraestructura/scripts/setup_debian.sh` | Prepara la VM (Docker + UFW) | Dentro de la VM Debian | Preparar el SO a mano |
| `infraestructura/scripts/setup_rocky.sh` | Prepara la VM (Docker + firewalld) | Dentro de la VM Rocky | Preparar el SO a mano |
| `infraestructura/iso/README.md` | Guía de ISOs | Humano | Pierdes la guía |
| `infraestructura/README.md` | Este documento | Humano | Sin documentación |
| `app-vulnerable/backend/config.py` | Única modificación a la app: `DATA_DIR` opcional | App (leída en runtime) | Sin ella, la app usa `/app` (datos fuera del volumen) |

**Relación con la prueba técnica**: 3.1 (balanceo: réplicas + Nginx round-robin
+ healthchecks + failover) y 3.2 (multi-distribución sobre VMs creadas a mano), a
lo que se añade **persistencia** (§13). Las VMs las creas tú; los scripts y Docker
hacen el resto.