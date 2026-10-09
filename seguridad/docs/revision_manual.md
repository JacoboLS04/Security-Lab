# Revisión manual

Complementa a Semgrep: valida cada sospecha del enunciado punto a punto, revisa los
flujos de entrada/salida y descarta o confirma los falsos positivos. OLC de severidad:
**Crítica** (compromiso sin o con auth mínima), **Alta** (auth de rol bajo/medio o
secreto clave), **Media**, **Baja**.

## 1. Backend

### 1.1 Busqueda de tickets (SQL dinámico sin autenticación)

`services/search_service.py:16` — `get_db().execute("SELECT ... LIKE '%s'" % labusqueda)`.
El endpoint de búsqueda **no exige token** (ruta pública según `app.py`/decoradores).
F-string al SQL → inyección arbitraria de consultas. **TP — Crítica.**
Semgrep estándar **no** lo detectó (no es taint `cursor.execute`, es `%` con f-string);
lo detecta la regla propia `opc-python-sql-construccion-manual`.

### 1.2 SQLi en el resto de la API (autenticadas)

Patrón repetido `cursor.execute("... %s" % ...)` / f-string:

- `api/admin.py:52` — listado con filtros de admin. **TP — Media** (admin).
- `api/reports.py:35` — filtro de reportes. **TP — Media** (admin/soporte).
- `api/users.py:30` — búsqueda de usuarios. **TP — Media** (auth; cualquier rol auto).
- `api/tickets.py:35` — consulta de tickets por estado/filtro. **TP — Media** (auth).
- `api/tickets.py:105` — `UPDATE` con `%` en el cuerpo de la petición (prioridad/comentario).
  **TP — Crítica** (auth; escritura arbitraria en la BD).

### 1.3 RCE autenticado por ping

`api/admin.py:67` — `ping -c 1 <host>` con `shell=True`, `host` desde query param.
Endpoint limitado a `admin|soporte`, pero **permite ejecución arbitraria de comandos**
(`;`, `|`, `&&`). **TP — Crítica.**

### 1.4 Blueprint de API interna (RCE latente)

`api/internal.py:29-36` — `/internal/exec` hace `subprocess.getoutput(cmd)` con el cuerpo
de la petición. Protegido por `require_interno` (header `X-Internal-Key` contra
`config.py:31`, clave estática **expuesta en el bundle Angular**, `environment.prod.ts:5`).
El blueprint solo se registra si `INTERNAL_API_ENABLED=True` (desactivado en el paquete).
**Needs review — Media** (latente; se vuelve crítica si se activa el flag con esa clave
pública en el frontend).

### 1.5 Deserialización insegura (pickle)

- `services/import_service.py:18` — `pickle.loads(payload)` con `payload` del usuario en
  `/api/importar/paquete` (solo auth). **TP — Crítica** (RCE autenticado).
- `services/import_service.py:31` — `pickle.loads` protegido por HMAC, pero la clave HMAC
  está en el bundle del frontend y el endpoint exige `admin`. **TP — Media.**
- `services/import_service.py:36` — `yaml.load(..., Loader=yaml.Loader)` inseguro
  (regla estándar `avoid-pyyaml-load`). **TP — Media.**

### 1.6 Zip-slip

`services/import_service.py:53` — los nombres de archivo dentro del ZIP no se validan;
se descomprime a `ADJUNTOS_DIR/nombre`. Escritura fuera del directorio con `../`.
**TP — Alta** (auth). La regla estándar no lo detecta; la propia
`opc-python-path-traversal-apertura` sí (siempre que el `os.path.join` incorpore el
nombre del zip).

### 1.7 Path traversal en ficheros

- `api/files.py:26` — lectura de adjunto; el filtro `if ".." in nombre` ocurre **antes**
  de `unquote`, por lo que `%2e%2e%2f` lo evade. `/api/files/descargar` no exige auth.
  **TP — Media.**
- `api/files.py:47` — `/api/files/preview` **sin auth**, devuelve `text/html` del archivo.
  **TP — Media.**
- `api/files.py:71` — subida con nombre de archivo sin normalizar. **TP — Media** (auth).
- `api/users.py:100` — avatar con nombre sin normalizar (además `chmod 0o777`,
  regla estándar `insecure-file-permissions`). **TP — Media/Baja.**
- `api/admin.py:102` — lectura de logs con nombre desde query param. **TP — Media** (admin).
- `services/export_service.py:33` — nombre de exportación sin normalizar (query param
  de `/admin/exportar`). **TP — Media.**
- FPs revisados: `backup_service.py:17/33` (nombres internos con `uuid` y `os.listdir`),
  `config.py:39-42` (constantes).

### 1.8 Inyección de comandos en exportaciones

`services/export_service.py:41` — `os.system(comando)` interpola el nombre del archivo de
exportación (mismo entrypoint/dato que 1.7). **TP — Alta.**
`services/export_service.py:48` — `subprocess.Popen(cmd, shell=True)` con
`formato_destino` de los formatos permitidos (mitigado parcialmente). **TP — Media.**
`services/export_service.py:63` — `rm -f` con glob fijo interno. **FP.**

### 1.9 Criptografía y contraseñas

- `core/security.py:22/27` — MD5 (`hashlib.md5`) para hash/verificación de contraseñas.
  **TP — Alta.**
- `core/security.py:43` — token de reset generado con `random.seed(time())` → predecible
  en la misma ventana de segundo. **TP — Alta.**
- `core/security.py:77` — `jwt.decode(..., verify_signature=False)` en la verificación de
  sesión: **no se valida la firma**, cualquiera puede fabricar un token con el rol que
  quiera. **TP — Crítica.**
- `core/security.py:96/103` — AES-ECB con clave fija en `FIELD_ENCRYPTION_KEY`.
  **TP — Media.**
- FPs: `cache_service.py:18/50` (MD5 como clave de caché y checksum, no criptografía).

### 1.10 Secretos y configuración

- `config.py:16` — `JWT_SECRET = "s3cr3t-jwt-opc-2024"` hardcodeado **e idéntico al
  `jwtSharedSecret` del frontend**. Fuerza la firma de tokens. **TP — Alta.**
- `config.py:31` — `INTERNAL_API_KEY = "opc-internal-7f3d9a21"` compartida con
  `erpApiKey` del frontend. **TP — Alta.**
- `config.py:13` — `SECRET_KEY` con default hardcodeado. **TP — Media.**
- `config.py:26/28` — `SMTP_PASSWORD` y credenciales AWS hardcodeadas.
  **TP — Media.** (`config.py:17` JWT_ALGORITHM → FP.)
- `config.py:49` — CORS `*` con `supports_credentials=True`. **TP — Media.**
- `config.py:51` — `DEBUG=True` por defecto. **TP — Media.**
- `core/errors.py:28` — el handler 500 devuelve traceback y configuración. **TP — Media.**
- `api/auth.py:30` — `logger` registra la contraseña en texto plano (regla estándar
  `logger-credential-leak`). **TP — Alta.**
- `app.py:96` — `app.run(0.0.0.0)` es correcto en contenedor: **FP**, el riesgo está en
  el DEBUG.
- `core/logging_conf.py:20` — `chmod 0o666` sobre `app.log`. **TP — Baja.**
- `api/users.py:102` — `chmod 0o777` sobre subida de avatar. **TP — Baja.**

### 1.11 Canal de notificaciones

- `services/notification_service.py:22` — `ssl._create_unverified_context()` para SMTP.
  **TP — Baja.**
- `services/notification_service.py:32` — `requests.post(..., verify=False)` con URL
  arbitraria del usuario → SSRF + MITM en envío de webhooks. **TP — Alta.**

## 2. Frontend

### 2.1 Secretos en entornos

- `environments/environment.prod.ts:5-6` y `environment.ts:11-12` — `erpApiKey`
  (clave de la API interna) y `jwtSharedSecret` (secreto de firma de JWT) publicados en el
  bundle Angular. Coinciden con `config.py:31` y `config.py:16`. **TP — Alta.**

### 2.2 XSS client-side

- `features/login/login.component.ts:15` — inyección del mensaje de error con
  `[innerHTML]` sin sanitizar. **TP — Media.**
- `features/tickets/ticket-detail.component.ts:30/34` — renderizado de descripciones con
  `marked` (markdown→HTML) sin saneo. **TP — Media.**
- `shared/safe-html.pipe.ts:14` — `bypassSecurityTrustHtml(valor)` para **todo** contenido
  de tickets (regla estándar `angular-bypasssecuritytrust`). **TP — Media.**
- Combinado con los mensajes de tickets por el backend sin escapar (`tickets.py:142/187`,
  XSS almacenado), el riesgo es mayor que el de cada pieza por separado.

### 2.3 Sin hallazgo

- `core/token.interceptor.ts:21` — adjunta el token a las peticiones; no se encontró
  fuga adicional (el problema está en los secretos del entorno, ver 2.1).

## 3. Notas finales

- Los hallazgos marcados como **necesitan auth** indican el rol mínimo; revísese en la
  decisión de priorización si ese rol es de fuerza bruta fácil (soporte/operador).
- 14 falsos positivos (detalle en `triage.md`) se descartaron con este análisis manual.