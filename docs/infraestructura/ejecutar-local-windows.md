# Ejecutar el stack de infraestructura en el host Windows (guía local)

Guía para **verificar que el despliegue corre en tu máquina principal (Windows)** con
**Docker Desktop (backend WSL2)**, sin necesidad de VMs. Complementa a
`../../infraestructura/README.md` (que documenta el despliegue didáctico sobre VMs
Debian 12 / Rocky 9); aquí trabajamos **directamente en Windows** con los mismos
`compose.yaml` y named volumes.

> Registro de modificaciones y avisos (app-vulnerable y `tsconfig.json`) al final,
> secciones **8** y **9**.

---

## Pregunta rápida: ¿qué va en `APP_SECRET_KEY`?

Cualquier **cadena aleatoria larga** (recomendado: 64 caracteres hexadecimales).

En `infraestructura/.env.example` el valor es un marcador:

```dotenv
# Secretos del backend. Generar una clave aleatoria, por ejemplo:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
APP_SECRET_KEY=cambia-esta-clave-por-una-aleatoria----
```

Genera la clave **antes** de copiar a `.env` (PowerShell), cualquiera de estas opciones:

```powershell
# Opcion A - si tienes Python instalado en Windows
python -c "import secrets; print(secrets.token_hex(32))"

# Opcion B - PowerShell nativo (hex aleatorio de 32 bytes)
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })

# Opcion C - sin instalar nada: un contenedor Python desechable (ya usas Docker)
docker run --rm python:3.9-slim python -c "import secrets; print(secrets.token_hex(32))"
```

Copia la salida (64 hex) como valor de `APP_SECRET_KEY` en tu `.env`.

- Si **no** defines la variable, la app no falla: `config.py:13` cae al fallback
  `"opc_super_secret_2024"`. Para validar el arranque local vale igual, pero ese fallback
  es uno de los hallazgos de la sección `seguridad/`. **En cualquier entorno real, clave
  aleatoria por entorno y nunca el fallback.**
- El `.env` real está gitignorado (`infraestructura/.gitignore`): tu clave no se sube.

---

## 1. Qué valida esta guía

Levantar **solo el backend** (API Flask) detrás de Nginx: 2 réplicas balanceadas, con
persistencia en named volumes. El frontend Angular **no se sirve** desde este stack
(no tiene Dockerfile; se documenta como mejora opcional). Si solo necesitas comprobar el
backend en tu Windows, esto alcanza.

Cambios **ninguno** al repositorio: solo se genera este documento.

## 2. Requisitos en Windows

| Requisito | Por qué | Cómo comprobar |
|---|---|---|
| **Docker Desktop** (WSL2 backend) | Ejecutar los contenedores | `docker --version` y `docker compose version` |
| Motor de **Linux containers** | Las imágenes son Linux | Docker Desktop → Settings → General → *Use the WSL 2 based engine* |
| **WSL2** con una distro activa | Backend de Docker Desktop | `wsl --status` |
| Git | Clonar el repositorio | `git --version` |
| `curl.exe` | Pruebas HTTP (en PowerShell `curl` es alias de `Invoke-WebRequest`, usa `curl.exe`) | `curl.exe --version` |
| Puerto TCP **8080 libre** | Lo publica el balanceador | `Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue` (sin salida = libre) |

> Line endings: `compose.yaml`, `nginx.conf`, `Dockerfile` y los `.sh` ya están
> fijados a **LF** por `.gitattributes`; en Windows con un clone normal no tendrás
> problemas con Compose.

## 3. Resumen (pasos rápidos)

```powershell
# 1) clonar y entrar
git clone <URL-del-repo> && cd <repo>
# 2) entorno (ajusta la clave, seccion "Pregunta rapida")
cd infraestructura
Copy-Item .env.example .env
notepad .env
# 3) construir y levantar (Linux containers)
docker compose up -d --build
# 4) comprobar salud
docker compose ps
curl.exe -s http://localhost:8080/api/health
```

## 4. Paso a paso

### 4.1 Conseguir el código

```powershell
cd C:\ruta\donde\quieres
git clone <URL-del-repo>
cd <repo>
```

### 4.2 Crear `.env` y fijar la clave

```powershell
cd infraestructura
Copy-Item .env.example .env
notepad .env
```

Edita `APP_SECRET_KEY` con el valor generado. Deja `FLASK_DEBUG=0` (Compose además lo
fuerza a `0` y fija `APP_DATA_DIR=/app/data`).

### 4.3 Construir y levantar

```powershell
docker compose up -d --build
```

- Compose construye la imagen `opc-backend:local` (Dockerfile de `infraestructura/`,
  contexto = raíz del repo) y descarga `nginxinc/nginx-unprivileged:1.27-alpine`.
- Crea la red interna y los named volumes `app-data-1` / `app-data-2`.
- `docker compose up` (o `docker compose up -d`) sin `--build` reutiliza la imagen.

### 4.4 Estado

```powershell
docker compose ps
# NAME      IMAGE                 STATUS
# opc-app-1 opc-backend:local     Up (healthy)
# opc-app-2 opc-backend:local     Up (healthy)
# opc-lb    nginx-unprivileged... Up (healthy)
```

Si `lb` está `(unhealthy)` o `(starting)`: mira el apartado 6. Da ~20 s (`start_period`).

## 5. Pruebas de validación (PowerShell)

### 5.1 La API responde (a través del balanceador)

```powershell
curl.exe -s http://localhost:8080/api/health
# {"status":"ok","servicio":"opc-tickets","version":"2.4.1"}

curl.exe -s http://localhost:8080/healthz
# ok
```

### 5.2 Balanceo round-robin (cabecera `X-Replica`)

```powershell
# ver las cabeceras de una peticion
curl.exe -si http://localhost:8080/api/health

# alternancia: X-Replica debe alternar app1/app2 (172.19.0.2 / .3:5000)
for ($i=1; $i -le 10; $i++) { curl.exe -si http://localhost:8080/api/health | findstr /i "x-replica" }
```

Corrobora la ruta real en los logs:

```powershell
docker compose logs lb          # access log con $upstream_addr
docker compose logs app1
docker compose logs app2
```

### 5.3 Contenedores como usuario no-root (endurecimiento)

```powershell
docker inspect -f '{{.Config.User}}' opc-app-1    # debe decir: opc
docker inspect -f '{{.HostConfig.CapDrop}}' opc-app-1  # [ALL]
docker exec opc-app-1 whoami
```

### 5.4 Failover (caída/recuperación de una réplica)

```powershell
docker compose stop app1
for ($i=1; $i -le 8; $i++) { curl.exe -si http://localhost:8080/api/health | findstr /i "x-replica" }
# 8/8 a la replica viva (solo la IP de app2); a veces "ip2:5000" con reintento de Nginx
docker compose ps               # app1 exited; app2 y lb healthy

docker compose start app1
Start-Sleep -Seconds 20
for ($i=1; $i -le 8; $i++) { curl.exe -si http://localhost:8080/api/health | findstr /i "x-replica" }
# vuelve la alternancia
```

### 5.5 Persistencia (named volumes)

```powershell
docker volume ls | findstr app-data        # app-data-1 y app-data-2

docker exec opc-app-1 ls /app/data         # tickets.db, adjuntos/, exportaciones/, logs/

# contador de tickets de cada replica (bases independientes)
docker exec opc-app-1 python -c 'import sqlite3;c=sqlite3.connect("/app/data/tickets.db");print("app1=",c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])'
docker exec opc-app-2 python -c 'import sqlite3;c=sqlite3.connect("/app/data/tickets.db");print("app2=",c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])'
```

Insertar un ticket y comprobar que sobrevive a `down`/`up` (PowerShell: comillas simples
fuera, comillas dobles dentro del Python):

```powershell
docker exec opc-app-1 python -c 'import sqlite3;c=sqlite3.connect("/app/data/tickets.db");c.execute("INSERT INTO tickets (codigo,solicitante,desarrollador,estado) VALUES (%s,%s,%s,%s)",("PERSIST-TEST","tester","qa","demo"));c.commit();print("tickets=",c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])'

docker compose down        # conserva los volumes (datos intactos)
docker compose up -d       # reutiliza los mismos volumes
docker exec opc-app-1 python -c 'import sqlite3;c=sqlite3.connect("/app/data/tickets.db");print("tickets=",c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])'
# el contador debe ser EL MISMO tras down/up
```

> `docker compose down -v` **borra** `app-data-1`/`app-data-2` (¡destructivo!).

### 5.6 Red y DNS de Compose

```powershell
docker network inspect opc-tickets_default
docker exec opc-lb getent hosts app1 app2
```

## 6. Solución de problemas en Windows

| Síntoma | Causa y solución |
|---|---|
| `docker compose` no existe / versión vieja | Docker Desktop trae Compose v2; actualiza Docker Desktop. |
| `daemon not running` / `Error response from daemon` | Arranca Docker Desktop y espera a que el "whale" esté arriba. |
| CONTAINERS "linux" vs "windows" | Asegúrate de que Docker Desktop usa el motor **WSL2 / Linux containers** (no Windows containers). |
| `port is already allocated` / `8080` ocupado | Otro proceso usa 8080. Libéralo o cambia el mapeo en `compose.yaml` (`"8080:8080"` → otro puerto host). |
| `curl: (7) Failed to connect` | El stack no está `healthy` todavía o WSL2/NAT del puerto no maduró; `docker compose ps` y reintenta. |
| VSCode/PowerShell me cambia comillas en `docker exec ... python -c '...'` | PowerShell interpreta comillas: usa **comillas simples para toda la expresión** y **dobles dentro** del Python (como en 5.5); o copia el bloque a un `.ps1`. |
| WSL2 se queda sin memoria (compilación lenta) | Docker Desktop → Settings → **Resources** → sube memoria WSL (este stack usa poco; 2 GB bastan). |
| Build lento (compila PyYAML) | Es esperado: `requirements.txt` fija PyYAML 5.3.1 sin wheels y hay que compilarlo (por eso el Dockerfile es multi-stage). Solo la primera vez. |
| Aviso `:z` en volúmenes | Docker Desktop no tiene SELinux: la opción `z` se ignora. No es un error. |
| `text file busy` o errores de CRLF en scripts | No ocurre en el host (los `.sh` solo se ejecutan dentro de VMs Linux). En el host solo ejecutas Compose. |

## 7. Infraestructura: árbol de directorios e importancia de cada archivo

```
proyecto/
├── app-vulnerable/            # aplicacion original (ver modificacion en seccion 8)
├── .dockerignore              # contexto de build: excluye docs/iso/.env del build
├── .gitattributes             # fuerza LF (evita CRLF de Windows en .sh/.py/.yaml/.conf)
├── docs/
│   └── infraestructura/       # redes.md, pruebas-estres.md, resumen_para_claude.md
└── infraestructura/           # TODO lo del despliegue (3.1 / 3.2)
    ├── README.md              # guia didactica y de operacion completa (VMs + host)
    ├── compose.yaml           # manifiesto: 2 replicas + Nginx + named volumes
    ├── .env.example           # plantilla de variables (copiar a .env)
    ├── .env                   # variables reales (gitignorado: nunca se sube)
    ├── .gitignore             # oculta .env e *.iso
    ├── deploy/
    │   └── nginx.conf         # config completa del balanceador (no-root, X-Replica)
    ├── docker/
    │   └── backend/
    │       └── Dockerfile     # imagen no-root multi-stage (compila wheels; crea /app/data)
    ├── scripts/
    │   ├── setup_debian.sh    # prepara la VM: Docker + UFW (solo VMs)
    │   └── setup_rocky.sh     # prepara la VM: Docker + firewalld/SELinux (solo VMs)
    └── iso/
        └── README.md          # ISOs recomendadas y verificacion de integridad
```

### Importancia de cada archivo

| Archivo | Qué es | Qué pasa si falta/respuesta errónea |
|---|---|---|
| `compose.yaml` | Manifiesto (servicios, red, healthchecks, límites, **volúmenes**) | No hay despliegue ni persistencia |
| `.env.example` | Plantilla de configuración | No sabes qué variables definir |
| `.env` | Variables reales (`APP_SECRET_KEY`, `FLASK_DEBUG`) | La app arranca con el fallback del `config.py` (secreto por defecto) |
| `.gitignore` | Ignora `.env` e ISOs | Subirías secretos y archivos de varios GB |
| `deploy/nginx.conf` | Configuración completa del balanceador (upstream, `X-Replica`, `/healthz`, no-root) | Nginx usa su config de serie: sin balanceo a las réplicas ni `X-Replica` |
| `docker/backend/Dockerfile` | Imagen no-root multi-stage; compila wheels y crea `/app/data` con dueño `opc` | No se construye la imagen |
| `.dockerignore` (raíz) | Reduce el contexto de build (excluye `docs/`, `.env`, ISOs) | Builds lentos y `.env` dentro del contexto |
| `.gitattributes` | Fuerza LF en texto ejecutado en Linux | Scripts con CRLF que rompen en las VMs |
| `scripts/setup_debian.sh` | Prep. de SO Debian (Docker + UFW) | Fuera del host Windows: son para las VMs |
| `scripts/setup_rocky.sh` | Prep. de SO Rocky (Docker + firewalld) | Ídem |
| `iso/README.md` | Guía de ISOs | Pierdes la guía (las VMs se crean a mano, no hay automatización) |
| `infraestructura/README.md` | Documentación completa (fases, didáctica, glosario, persistencia) | Sin referencia didáctica |
| `docs/infraestructura/*.md` | Redes y pruebas de estrés | Pierdes complementos de evidencias |

Para el arranque local en Windows **solo intervienen**: `compose.yaml`, `.env`,
`deploy/nginx.conf`, `docker/backend/Dockerfile`, `.dockerignore` y `app-vulnerable/backend`.

## 8. Qué se modificó de `app-vulnerable`

**Una única modificación, mínima y opt-in:**

- **`backend/config.py`** (líneas 34–42): se añadió la variable opcional **`APP_DATA_DIR`**
  que redirige los datos persistentes (SQLite `tickets.db`, `adjuntos/`, `exportaciones/`,
  `logs/`) a una carpeta fija. Compose la fija a `/app/data`, donde se monta el named
  volume. **Sin la variable el comportamiento original no cambia** (datos junto al código).

Nada más se tocó de la aplicación: ni `app.py`, ni endpoints, ni el balanceo (se demuestra
sin modificar código). El Dockerfile copia solo `app-vulnerable/backend` y crea `/app/data`
para que el proceso no-root pueda escribir en el volumen.

> Estado en git: `app-vulnerable/` está al día (sin cambios pendientes); el `config.py`
> modificado ya forma parte de los commits de despliegue.

## 9. Aviso sobre `app-vulnerable/frontend/tsconfig.json` (errores de VS Code)

VS Code marca **4 problemas de deprecación** en `tsconfig.json` (líneas 4, 5, 8 y 10) por
**TypeScript ≥ 6.0** que depreca/retira opciones:

| Línea | Opción | Mensaje marcado |
|---|---|---|
| 4 | `baseUrl` | Deprecada; deja de funcionar en TS 7.0 |
| 5 | `outDir` | Exige `rootDir` explícito en TS 6.0 (`./src`) |
| 8 | `downlevelIteration` | Deprecada (irrelevante con `target: ES2022`) |
| 10 | `moduleResolution: "node"` (`node10`) | Deprecada; migrar a `"bundler"` |

**Puntos a tener en cuenta (sin modificar nada):**

- Es un aviso **del editor/TypeScript 6**, no del proyecto. El stack de
  contenedores (sección 4) **no compila TypeScript**: sirve solo el backend Python.
  Por tanto **no impide** ejecutar ni validar esta guía.
- La aplicación frontend es Angular; la migración correcta (eliminar `baseUrl`/
  `downlevelIteration`, añadir `"rootDir": "./src"`, `"moduleResolution": "bundler"`)
  corresponde a otra sección del ejercicio (frontend) y **no se ha aplicado aquí**,
  porque esta guía no modifica código.
- Posibilidad "puente" para silenciar mientras tanto: `"ignoreDeprecations": "6.0"`
  dentro de `compilerOptions` — solo pospone el aviso hasta TS 7.0.

## 10. Referencias

- `../../infraestructura/README.md` — despliegue completo sobre VMs (Debian 12 / Rocky 9),
  arquitectura bloques, glosario y persistencia (§13).
- `../../infraestructura/` → `.env.example`, `compose.yaml`, `deploy/nginx.conf`.
- `redes.md` y `pruebas-estres.md` (mismo directorio).
- `seguridad/` → análisis SAST del backend/frontend (incluye hallazgos sobre
  `config.py`, secretos por defecto y la exposición del `tsconfig`/frontend).