# Plan de remediación

Orden de prioridad por severidad e impacto real. Cada remedio es una acción concreta y
verificable. Los números entre paréntesis remiten a los reportes
(`seguridad/reportes/reporte_*.csv`) y al detalle de `revision_manual.md`.

> Estado actual: **ninguna de estas correcciones está aplicada** en `app-vulnerable/`.
> Este plan es la guía de remediación; su aplicación (total o parcial) se hará en una fase
> posterior y quedará documentada y re-escaneada.

## Fase 0 – Eliminar la superficie de riesgo inmediata (minutos)

1. **`config.py:51`** — `DEBUG=False` como **default**, no como opt-in. En el contenedor
   de producción debe forzarse por variable de entorno y fallar al arrancar si está en
   True.
2. **`app.py`** — servir con un servidor WSGI (gunicorn/waitress) con interfaz de escucha
   concreta, en lugar de `app.run()`.

## Fase 1 – Siniestralidad crítica (5 vulnerabilidades)

| # | Hallazgo | Acción |
|---|---|---|
| 1 | SQLi sin auth — `search_service.py:16` | Jugar **solo** con API parametrizada (SQLite `?`) o ORM; el parámetro nunca forma parte de la cadena SQL. Eliminar el `%`/f-string en consultas. |
| 2 | SQLi `tickets.py:105` (UPDATE) | Igual que 1: `execute("UPDATE ... SET ... WHERE id = ?", (v, id))`. |
| 3 | RCE `admin.py:67` (ping) | No construir comandos con `shell=True`. Usar `subprocess.run(["ping","-c","1",host])`, validar el host contra `ipaddress.ip_address`/hostname permitido en Allowlist; o mover la comprobación a un servicio interno de red con timeout y sin shell. |
| 4 | Pickle `import_service.py:18/31` | Sustituir pickle por un formato seguro (JSON) **con esquema validado**; eliminar `pickle.loads` de entrada. Si es innegociable, firmar en backend con clave no distribuida (jamás en el frontend) y fallback a JSON. |
| 5 | JWT `security.py:77` | `jwt.decode(token, secret, algorithms=[Config.JWT_ALGORITHM])` **con verificación obligatoria** (`verify_signature=True` y `verify` Semantic: usar `decode(..., leeway=0)`). Tests que rechacen tokens sin firma. |

## Fase 2 – Altas (8)

| # | Hallazgo | Acción |
|---|---|---|
| 6 | MD5 contraseñas — `security.py:22/27` | Migrar a `argon2` (o `bcrypt`); rehash en login para cuentas antiguas. |
| 7 | Entropía token reset — `security.py:43` | `secrets.token_urlsafe(32)`; nunca `random` con `seed(time())`. |
| 8 | `JWT_SECRET` hardcodeado — `config.py:16` | Variable de entorno obligatoria sin default; rotación de secreto antes de exponer. |
| 9 | `INTERNAL_API_KEY` compartida con frontend — `config.py:31` | Clave independiente del bundle; autenticación mútua (mTLS o firma HMAC por petición) y revocar la expuesta. |
| 10 | Inyección comandos export — `export_service.py:41/48` | API de conversión como servicio interno con interfaz acotada (sin shell); si se conserva `subprocess`, siempre por lista de args (`Popen([...])`) y jamás `shell=True` ni interpolación. |
| 11 | Zip-slip — `import_service.py:53` | Validar cada nombre del ZIP: rechazar `..`, rutas absolutas y `\`, y resolver con `os.path.realpath` comprobando que quede bajo `ADJUNTOS_DIR`. |
| 12 | Webhook `verify=False` — `notification_service.py:32` | `verify=True` con CA de confianza; validar el esquema y dominio de `url` (anti-SSRF), usar timeout. |
| 13 | Log de contraseña — `auth.py:30` | No loguear credenciales; loguear solo `usuario` e IP. |

## Fase 3 – Medias (12)

| # | Hallazgo | Acción |
|---|---|---|
| 14 | SQLi admin/reports/users — `admin.py:52, reports.py:35, users.py:30` | Parametrización (mismo criterio que Fase 1). |
| 15 | Path traversal ficheros — `files.py:26/47/71, users.py:100, admin.py:102, export_service.py:33` | Normalizar `unquote` **antes** del chequeo, `realpath` bajo directorio permitido; `send_from_directory`. |
| 16 | Pickle post-HMAC con clave expuesta — `import_service.py:31` | Migrar a JSON firmado con clave de backend no distribuida. |
| 17 | `yaml.load` inseguro — `import_service.py:36` | `yaml.safe_load`. |
| 18 | XSS backend `tickets.py:142/187` | Escapar/neutralizar el HTML de salida; nunca confiar en contenido de tickets. |
| 19 | XSS frontend `login.ts:15, ticket-detail.ts:30/34, safe-html.pipe.ts:14` | Eliminar `bypassSecurityTrustHtml`/`[innerHTML]`; renderizar con Angular (`{{ }}`) y para markdown usar una librería que sanea (DOMPurify antes de `marked`). |
| 20 | AES-ECB — `security.py:96/103` | Modo autenticado (AES-GCM) con IV aleatorio por operación; clave via gestor de secretos + `FERNET`, no literal. |
| 21 | CORS `config.py:49` | Dominios permitidos explícitos, sin `*` con credenciales. |
| 22 | `DEBUG=True` por defecto — `config.py:51` | (ver Fase 0) |
| 23 | Traceback en 500 — `errors.py:28` | Log interno del traceback; respuesta genérica sin rastro de stack/config. |
| 24 | Secretos integraciones `config.py:26/28` | Mover a variables de entorno / gestor de secretos. |
| 25 | `SECRET_KEY` default — `config.py:13` | Idem: obligatoria por entorno. |

## Fase 4 – Bajas y endurcido

| # | Hallazgo | Acción |
|---|---|---|
| 26 | SMTP contexto no verificado — `notification_service.py:22` | `ssl.create_default_context()`; validar hostname. |
| 27 | Permisos avatar `users.py:102` (`0o777`) | `0o644`/`0o600`. |
| 28 | Permisos log `logging_conf.py:20` (`0o666`) | `0o640` restrictivo. |

## Pendiente de revisión (Needs review)

- **`internal.py:35`** — `/internal/exec`. Decisión pendiente de negocio sobre si el
  blueprint con `INTERNAL_API_ENABLED=True` existirá en algún despliegue. Si se mantiene:
  (a) dejar de exponer su clave en el frontend, (b) restringir por red/IP, (c) comando a
  allowlist y (d) exigir mTLS.

## Verificación post-remediación

Re-escanear con los mismos comandos del `README` (packs estándar + reglas propias) y
fijar los siguientes umbrales objetivos:

- 0 hallazgos **Críticos** en `reporte_sast` y `reporte_reglas_custom`.
- 0 hallazgos **Altos** en las reglas propias para `environment*.ts`, `config.py` y
  `security.py`.
- Reducción ≥ 90% del total de TP consolidado.
- Los fixtures `evidencias/reglas-pruebas/corregido/` deben seguir a 0 hallazgos y los
  `vulnerable/` a 25.

Estos umbrales no son "falsos positivos": se miden contra el árbol corregido, no contra
el vulnerable original.

## Riesgos y dependencias

- La migración de MD5→argon2 exige coordinar con el esquema de la BD (rehash progresivo).
- Cambiar `verify_signature=False` a `True` invalidará tokens ya emitidos: planificar
  ventana de regeneración de sesiones.
- La rotación del `JWT_SECRET` debe hacerse con doble emisión temporal.