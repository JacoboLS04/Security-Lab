# Informe de seguridad — App vulnerable OPC Tickets (§3.4)

- **Alcance**: `app-vulnerable/backend` (Python/Flask) y `app-vulnerable/frontend` (Angular 15).
- **Tipo**: análisis estático (SAST) + revisión manual + PoC (solo lectura).
- **Estado de la app**: **NO corregida** de forma intencional (la corrección de las vulnerabilidades más críticas es un **bono opcional** de la prueba; no se modifica la aplicación sin justificación).
- **Fecha de ejecución**: 2026-10-09.
- **Evidencias**: `docs/seguridad/sast/bandit-backend.txt` (salida cruda), `docs/seguridad/sast/poc-criticos.txt` (PoC).

---

## 1. Resumen ejecutivo

El backend Flask de la app vulnerable contiene **vulnerabilidades explotables
reales y críticas**, no solo "malas prácticas". Se confirmaron con PoC:

1. **Autenticación eludible** (JWT sin verificar firma) → acceso **admin** sin credenciales.
2. **Ejecución de comandos** (RCE como usuario `opc`) vía `/api/admin/diagnostico/ping`.
3. **Inyección SQL booleana** confirmada en la búsqueda de tickets (y múltiples
   puntos por construcción).
4. **XSS reflejado** en endpoints que devuelven HTML sin escapar.
5. **Deserialización insegura (pickle)** alcanzable por cualquier usuario
   autenticado en `/api/importar/paquete` (RCE).
6. Múltiples secretos **hardcodeados** (JWT, cifrado simétrico, SMTP, AWS).

Bandit (`bandit -r backend`) reportó **52** hallazgos: 14 High / 14 Medium /
24 Low. De ellos, ~9 son **falsos positivos o descartes justificados** que se
documentan en §5. La corrección de las 2 vulnerabilidades más críticas es el
bono de la prueba (no aplicado).

> Ningún endpoint requiere acceso de red externo para explotarse: la app corre
> localmente en un laboratorio. **No desplegar en producción.**

---

## 2. Herramienta SAST ejecutada

```bash
bandit -r app-vulnerable/backend -f txt   # bandit 1.9.4 (venv aislado)
```
- Salida completa: `docs/seguridad/sast/bandit-backend.txt`.
- Métricas de la corrida (561 líneas): **52 resultados** — Severity
  High=14 · Medium=14 · Low=24; Confianza High=38 · Medium=5 · Low=9.
- CWE presentes (top): CWE-78 (15), CWE-89 (9), CWE-703 (6), CWE-327 (5),
  CWE-259 (4), CWE-330 (3), CWE-502 (3), CWE-732 (2), CWE-295 (2), otras (4).

**SAST del frontend (ejecutado)**: `npx eslint "src/**/*.ts"` (Node v26.10.0,
eslint 8.33.0, `@typescript-eslint` 5.48.0, `eslint-plugin-security` 1.7.1;
dependencias instaladas en `app-vulnerable/frontend/node_modules`).

```bash
npm install --no-audit --no-fund --ignore-scripts
npx eslint "src/**/*.ts" -f json
```
- Resultado: 18 archivos revisados, **15 mensajes** (13 `no-explicit-any`, 2 de
  reglas `security/*`). Salida: `docs/seguridad/sast/eslint-frontend.txt` + `.json`.
- Reglas de seguridad detectadas:
  - `security/detect-non-literal-regexp` (`src/app/shared/highlight.directive.ts:18`):
    el término de búsqueda del usuario se concatena a un `RegExp` → **ReDoS**
    potencial; además la directiva reescribe `innerHTML` (sin el pipe sanitizado).
    Severidad **Media** (hallazgo #22).
  - `security/detect-object-injection` (`src/app/core/api.service.ts:15`):
    `HttpParams.set(k,v)` sobre `Record<string,string>` controlado por los
    llamadores. **Baja / descarte justificado** (parámetros tipados; sin claves
    arbitrarias del usuario).

---

## 3. Revisión manual (hallazgos que SAST no detecta)

Los hallazgos más graves **no los detecta Bandit** porque son de lógica de
autorización y deslizamiento de datos:

- JWT decodificado **sin verificar firma** (`core/security.py:70-79`): cualquier
  token es válido si contiene un `sub`/`rol`; permite suplantar a `admin`.
- Publicación de endpoints sensibles **sin autenticación** (listado/búsqueda de
  tickets: `api/tickets.py:23-48`).
- Autorización horizontal interrumpida (`api/users.py:47-69`): cualquier usuario
  autenticado puede cambiar `rol`/`activo` de otros usuarios.
- XSS en HTML generado servidor-side y en el frontend (`bypassSecurityTrustHtml`).
- `render_template_string` con HTML sin escapar con datos del ticket.

---

## 4. Hallazgos clasificados

Legenda: **Evidencia** = archivo:línea y/o PoC. **Estado** = `Pendiente`
(no corregido) o `Verificado` (PoC). Severidad marcada por el analista.

| # | Vulnerabilidad | Ubicación | Evidencia | Severidad | CWE / OWASP | Impacto | Recomendación | Estado |
|---|---|---|---|---|---|---|---|---|
| 1 | **Omisión de verificación de firma JWT** (authZ/AuthN) | `core/security.py:70-79` (usado en `core/decorators.py:27-34, 77-84`) | PoC: `/api/admin/auditoria` con token forjado → **200** (`poc-criticos.txt`) | **Crítica** | CWE-345 / CWE-347 · OWASP A07 / A01 | Cualquier usuario logra rol `admin`/`soporte` sin conocer secretos | `validar_token()` (verificar firma y `alg`) en `require_auth`/`require_rol` | Verificado |
| 2 | **Deserialización insegura (pickle) → RCE** | `services/import_service.py:15-19` + `api/importar.py:12-27` | Route alcanzable con cualquier `@require_auth`; `pickle.loads` sobre payload b64 | **Crítica** | CWE-502 · OWASP A03 (Injection) / A08 | RCE arbitrario en el contenedor | Sustituir por JSON firmado; validar tipos; nunca `pickle.loads` de input | Pendiente |
| 3 | **Ejecución de comandos (RCE)** | `api/admin.py:60-72` (`subprocess.check_output(..., shell=True)`) | PoC: `host=127.0.0.1; id` → ejecuta `uid=1000(opc)` (`poc-criticos.txt`) | **Crítica** | CWE-78 · OWASP A03 | RCE como usuario `opc` del contenedor | `shlex.split`, `subprocess` sin shell, lista de hosts, o `ping` permitido por allowlist | Verificado |
| 4 | **Inyección SQL (múltiples puntos)** | `services/search_service.py:18-25`; `api/tickets.py:100-105`; `api/users.py:30-34`; `api/reports.py:35-37`; `api/admin.py:51-57`; `utils/auditoria.py:15-19` | PoC booleano en `/api/tickets/buscar`: 7→**8** filas con `x' OR '1'='1` (`poc-sqli-boolean.txt`) | **Alta** | CWE-89 · OWASP A03 | Lectura/escalada sobre toda la BD (incl. usuarios, notas internas) | Solo queries parametrizadas (`?`); validación estricta de columnas/orden | Verificado (buscar) · Pendiente (resto) |
| 5 | **Secretos hardcodeados** | `config.py:16-31`; `frontend/src/environments/environment.ts:9-15` y `environment.prod.ts` | Código (JWT secrets, `FIELD_ENCRYPTION_KEY`, SMTP, AWS, `INTERNAL_API_KEY` en frontend) | **Alta** | CWE-798 / CWE-259 · OWASP A07 / A08 | Robo de credenciales, firma, cifrado | Variables de entorno por servicio; rotar y revocar lo publicado en código | Pendiente |
| 7 | **Cifrado simétrico débil (AES-ECB, clave fija)** | `core/security.py:94-105` | Código | **Alta** | CWE-327 · OWASP A02 | Descifrado/patrones en campos cifrados (teléfonos) | AES-GCM con clave gestionada (secrets manager), IV/nonce único | Pendiente |
| 8 | **Hash MD5 de contraseñas** | `core/security.py:20-28`; seed demo `db.py:111-115` | Bandit B324 | **Alta** | CWE-327 · OWASP A02 | Crackeo trivial de hashes | `pbkdf2_hmac`/`bcrypt`/`argon2`; rehash sobre el esquema nuevo | Pendiente |
| 9 | **Token de reset predecible** | `core/security.py:41-44` (`random.seed(int(time.time()))`, 6 dígitos) | Bandit B311 (parcial) + revisión | **Alta** | CWE-330 · OWASP A01/A02 | Adivinación del código → account takeover | `secrets.token_urlsafe(...)` / `secrets.SystemRandom`; expiración y un solo uso | Pendiente |
| 10 | **Contraseñas en logs** | `api/auth.py:30-31` (login loguea `password`) | Código | **Media** | CWE-532 · OWASP A09 | Exfiltración de credenciales por logs | No loguear el password; redactar | Pendiente |
| 11 | **XSS (servidor y cliente)** | `api/tickets.py:134-150, 182-191`; `api/files.py:43-52`; frontend `safe-html.pipe.ts:14`, `login.component.ts:15`, `admin-console.component.html:21` | PoC etiqueta: `<script>` se devuelve sin escapar (`poc-criticos.txt`) | **Alta** | CWE-79 · OWASP A03 | Robo de sesión / ejecución en navegador | Escapar salida; no usar `bypassSecurityTrustHtml`; CSP | Verificado (reflejado) · Pendiente (stored/frontend) |
| 12 | **Subida de archivos sin saneo (path/ejecutables)** | `api/files.py:63-77`; `api/users.py:87-107` | `archivo.filename` usado tal cual en `os.path.join` | **Alta** | CWE-434 / CWE-22 · OWASP A03/A05 | Sobrescritura de rutas, potencial servido de contenido | `secure_filename` + extensión allowlist; servir desde carpeta con `X-Content-Type-Options: nosniff` | Pendiente |
| 13 | **Autorización (IDOR/rol) rota** | `api/users.py:47-69`; `core/decorators.py:86` (assert como control de acceso) | Revisión | **Alta** | CWE-862 / CWE-639 · OWASP A01 | Escalada de privilegios entre usuarios | Comprobar `g.usuario.id`/rol explícitamente; eliminar `assert` | Pendiente |
| 14 | **Exposición pública de datos sensibles** | `api/tickets.py:23-48` (`listar`/`buscar` sin auth; incluye `notas_internas`, p.ej. ticket con datos de contrato) | Revisión | **Alta** | CWE-200 · OWASP A01/A04 | Fuga de datos internos/credenciales | Exigir auth en listado/búsqueda; no devolver `notas_internas` | Pendiente |
| 15 | **Carga YAML insegura** | `services/import_service.py:34-36` + `api/importar.py:45-52` | Revisión (Bandit no lo marca) | **Alta** | CWE-502 · OWASP A08/A03 | Ejecución de código vía `yaml.load(..., Loader=yaml.Loader)` | Usar `yaml.safe_load` o SafeLoader | Pendiente |
| 16 | **Verificación TLS deshabilitada** | `services/notification_service.py:22,36` | Bandit (CWE-295) | **Media** | CWE-295 · OWASP A02 | MITM en smtp/webhooks/ERP | Verificar certificados (`verify=True`, contexto por defecto) | Pendiente |
| 17 | **User enumeration** | `api/auth.py:35,40-41,101-102` | Revisión | **Media** | CWE-204 · OWASP A01 | Discernir usuarios válidos | Mensajes genéricos | Pendiente |
| 18 | **Permisos de archivos peligrosos** | `api/users.py:102` (`os.chmod 0o777`); `core/logging_conf.py:20` (`0o666`) | Bandit B103 | **Baja/Media** | CWE-732 · OWASP A05 | Lectura/escritura por cualquier usuario del contenedor | Mínimos permisos (0o640/0o600) | Pendiente |
| 19 | **Cookie de sesión sin flags** | `api/auth.py:62` (`set_cookie("sesion", token)`) | Revisión | **Baja** | CWE-614/1004 · OWASP A05/A07 | Robo vía XSS | `HttpOnly`, `Secure`, `SameSite=Lax` | Pendiente |
| 20 | **Error verbose 500 (traceback + rutas)** | `core/errors.py` (respuesta de error devuelve traceback y rutas) | PoC: error de SQLi muestra `config.db` y traceback | **Media** | CWE-209 · OWASP A05 | Información interna | Log server-side; respuesta genérica | Pendiente |
| 21 | **Superficie de ataque del blueprint interno** (consola SQL, `subprocess.getoutput`) | `api/internal.py:19-36` + `core/decorators.py:107-118` (`require_interno` confía en `X-Forwarded-For`) | Revisión; **no** registrado por defecto (`INTERNAL_API_ENABLED=False`) | **Media (latente)** | CWE-78/CWE-89 · OWASP A03 | Si se activa el flag, equivale a RCE con control parcial | Mantener desactivado o migrar a red/gw real; no confiar en `X-Forwarded-For` | Pendiente |
| 22 | **ReDoS / manipulación de innerHTML con input de usuario** (frontend) | `src/app/shared/highlight.directive.ts:18` | ESLint `detect-non-literal-regexp` (`eslint-frontend.txt`) | **Media** | CWE-1333 / CWE-79 · OWASP A03 | El término de búsqueda se inyecta en `RegExp` y se reescribe el `innerHTML` del host | Escapar el término para el patrón; construir el `mark` sin `innerHTML` crudo | Pendiente |

> Faltaba aquí numeración #6 por legibilidad; el orden en la tabla es interno.

## 5. Falsos positivos / descartes de Bandit (documentados)

| Id | Código | Motivo del descarte |
|---|---|---|
| B104 (bind `0.0.0.0`) | `app.py:96` | Necesario para exponer la API en la red del contenedor; no es una debilidad en sí (la expone Nginx internamente). |
| B608 en `api/tickets.py:35-37` (`listar`) | columna whiteliscada + `int()` para límite/offset | Construcción controlada; **FP**. |
| B311 en `services/cache_service.py:21-23` | `random.randint` para TTL | Uso no criptográfico (solo dispersión de cache); **FP**. |
| B603/B607 en `api/internal.py` | solo alcanzable con `INTERNAL_API_ENABLED=True` (por defecto `False`) | Riesgo latente (hallazgo #21) pendiente de flag; no explotable por defecto. |
| B101 (assert) | varios | Mayormente robustez salvo `decorators.py:86` (ver hallazgo #13). |

## 6. Priorización y plan de remediación

Orden (impacto × facilidad de explotación × dependencia):

1. **#1 JWT no verificado** → corregir primero: un solo cambio (`leer_claims` →
   `validar_token`) elimina la vía de authN rota.
2. **#3 RCE (ping)** y **#2 pickle** → requieren auth, pero un admin comprometido
   o un token forjado (#1) los dispara; eliminar `shell=True` y `pickle.loads`.
3. **#4 SQLi** → parametrizar todos los `%`/[f-string] de SQL (un patrón único);
   tocar 6 archivos con la misma regla `?`.
4. **#5, #7, #8, #9** → secretos y criptografía: mover a variables de entorno,
   algoritmos seguros (argon2, AES-GCM, `secrets`).
5. **#11, #12, #13, #14** → validación de entrada, escape de salida y
   autorización explícita.
6. **Media/Baja** (#10, #16, #17, #18, #19, #20, #21) → saneamiento rápido
   (logs, TLS, mensajes, permisos, cookies, errores, superficie interna).

> La corrección de los dos más críticos (#1 y #2/#3) es el **bono opcional** de
> la prueba: se documenta el plan pero **no se implementa** en este repositorio.

## 7. Estado y pendientes

- [x] SAST backend con Bandit — hecho, salida en `docs/seguridad/sast/bandit-backend.txt`.
- [x] SAST frontend con ESLint + `eslint-plugin-security` — hecho, salida en `docs/seguridad/sast/eslint-frontend.txt`.
- [x] PoC (lectura) de #1, #3, #4 y #11 — `docs/seguridad/sast/poc-criticos.txt`, `poc-sqli-boolean.txt`.
- [x] Revisión manual consolidada (backend y frontend) — hallazgos #5–#22 en §4.
- [ ] (Opcional) corrección de las vulnerabilidades críticas de la app.