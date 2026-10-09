# Informe final — Análisis de seguridad de `app-vulnerable`

## 1. Resumen ejecutivo

Se analizó la aplicación objetivo (backend Flask + SQLite, frontend Angular) con un
proceso reproducible de análisis estático (Semgrep 1.180.0, packs estándar OWASP/Top-10
Python/JS/TS + 17 reglas propias validadas contra fixtures vulnerables/corregidos) y
revisión manual de los flujos de entrada/salida.

| Métrica | Valor |
|---|---|
| Archivos Python analizados | 57 (backend completo) |
| Escaneo estándar (packs OWASP/Python/JS/TS) | 27 hallazgos (12 ERROR, 15 WARNING) |
| Escaneo con reglas propias | 52 hallazgos |
| Decisiones de triage | 79 (64 TP, 14 FP, 1 Needs review) |
| Errores de ejecución de Semgrep | 0 |
| **Vulnerabilidades consolidadas** | **28** (5 críticas, 8 altas, 12 medias, 3 bajas) + 1 exposición latente en revisión |

**Conclusión:** la aplicación presenta vulnerabilidades **críticas explotables incluso
sin autenticación** (SQLi en la búsqueda, lectura de ficheros por path traversal) y
**RCE autenticado** (ping con shell, pickle). La raíz común son tres patrones:
(1) construcción de SQL/comandos por concatenación de entrada del usuario,
(2) secretos de producción (JWT_SECRET, INTERNAL_API_KEY, credenciales SMTP/AWS)
integrados en el código y en el bundle del frontend, y
(3) tratamiento de datos no confiables como código (pickle, `yaml.load`, `os.system`,
`bypassSecurityTrustHtml`).

No se declara aplicada ninguna corrección: las evidencias corresponden al árbol
original `app-vulnerable/` y el plan de remediación está en `plan_remediacion.md`.

## 2. Metodología (resumen)

Detalle completo en `metodologia.md`. Lo esencial:

1. Semgrep instalado fuera del repo (Python 3.12, `uv venv`), `SEMGREP_CORES=1 --jobs 1`
   por el fallo de `io_uring` del runner (documentado).
2. Escaneo estándar → `semgrep/resultados/resultados_sast.json` (intacto).
3. 17 reglas propias calibradas con fixtures (`vulnerable/`: 26 hallazgos, `corregido/`:
   0 hallazgos) → `semgrep/resultados/resultados_reglas_custom.json` (intacto).
4. Triage manual de las 79 coincidencias → `semgrep/resultados/triage.json`.
5. Reportes finales con triage en `reportes/` (TXT y CSV por escaneo).

Por transparencia: **no se asignaron CVSS/CVE/CWE/OWASP inventados**. Los CWE/OWASP que
muestran los reportes provienen de los metadatos de las reglas de Semgrep; cuando no
existen figura "No disponible". La severidad es propia y se apoya en alcance de la
entrada, autenticación requerida e impacto probable.

## 3. Resultados consolidados (28 vulnerabilidades)

### Críticas (5)

| # | Vulnerabilidad | Ubicación | Notas |
|---|---|---|---|
| 1 | **SQLi sin autenticación** (búsqueda de tickets) | `backend/services/search_service.py:16` | Endpoint público; f-string en consulta. |
| 2 | **SQLi con auth** (UPDATE de tickets) | `backend/api/tickets.py:105` | Escritura arbitraria en BD. |
| 3 | **RCE autenticado** (ping con shell) | `backend/api/admin.py:67` | `host` del usuario; roles admin/soporte. |
| 4 | **RCE autenticado** (pickle) | `backend/services/import_service.py:18` | `pickle.loads` del cuerpo de la petición. |
| 5 | **JWT sin verificación de firma** | `backend/core/security.py:77` | `verify_signature=False`; se puede forjar rol/uid. |

### Altas (8)

| # | Vulnerabilidad | Ubicación |
|---|---|---|
| 6 | **MD5 como hash de contraseñas** | `backend/core/security.py:22/27` |
| 7 | **Token de reset predecible** (`random.seed(time())`) | `backend/core/security.py:43` |
| 8 | **`JWT_SECRET` hardcodeado y expuesto en el frontend** | `backend/config.py:16` + `frontend/src/environments/{environment,environment.prod}.ts` (igual valor) |
| 9 | **Clave de API interna compartida con el bundle** | `backend/config.py:31` + `environments/environment*.ts` |
| 10 | **Inyección de comandos** (exportación de archivos) | `backend/services/export_service.py:41/48` |
| 11 | **Zip-slip** | `backend/services/import_service.py:53` |
| 12 | **Webhook con `verify=False`** (MITM/SSRF) | `backend/services/notification_service.py:32` |
| 13 | **Contraseña en logs** | `backend/api/auth.py:30` |

### Medias (12)

| # | Vulnerabilidad | Ubicación |
|---|---|---|
| 14 | SQLi en admin/reportes/usuarios | `admin.py:52`, `reports.py:35`, `users.py:30` |
| 15 | Path traversal en ficheros/avatars/logs | `files.py:26/47/71`, `users.py:100`, `admin.py:102`, `export_service.py:33` |
| 16 | Pickle con HMAC expuesto | `import_service.py:31` |
| 17 | `yaml.load` inseguro | `import_service.py:36` |
| 18 | XSS backend (HTML de tickets sin escapar) | `tickets.py:142/187` |
| 19 | XSS frontend (`[innerHTML]`, `marked`, `bypassSecurityTrustHtml`) | `login.component.ts:15`, `ticket-detail.component.ts:30/34`, `safe-html.pipe.ts:14` |
| 20 | AES-ECB con clave fija | `core/security.py:96/103` |
| 21 | CORS `*` con credenciales | `config.py:49` |
| 22 | `DEBUG=True` por defecto | `config.py:51` |
| 23 | Traceback/stack en errores 500 | `core/errors.py:28` |
| 24 | Credenciales de integración hardcodeadas (SMTP/AWS) | `config.py:26/28` |
| 25 | `SECRET_KEY` con default hardcodeado | `config.py:13` |

### Bajas (3) y observaciones

| # | Vulnerabilidad | Ubicación |
|---|---|---|
| 26 | SMTP con contexto TLS no verificado | `notification_service.py:22` |
| 27 | Permisos `0o777` en avatares | `users.py:102` |
| 28 | Permisos `0o666` en `app.log` | `logging_conf.py:20` |

Observación: `app.run` en `0.0.0.0` es esperable en contenedor y no se cuenta como
vulnerabilidad (el problema es el `DEBUG`, ya listado).

### Exposición latente (Needs review)

- `backend/api/internal.py:35` — `/internal/exec` ejecuta el comando del cuerpo de la
  petición. No registrado salvo `INTERNAL_API_ENABLED=True` y su clave está en el bundle
  Angular. **Critico si se activa**; decisión de negocio en `plan_remediacion.md`.

## 4. Cobertura de la herramienta

- Lo que detectan los packs estándar (y las reglas propias lo confirman): SQLi por
  `cursor.execute`, `subprocess` con shell, XSS HTML en salida, MD5, JWT sin firma,
  `verify=False`, permisos de archivo, credenciales en logs, `avoid-pyyaml-load`,
  `bypassSecurityTrustHtml`.
- Lo que **no** detectan los packs estándar y solo las reglas propias: SQLi por f-string
  en `search_service.py`, path traversal (con la regla de `os.path.join`, 6 TP),
  pickle, secretos hardcodeados en config y entornos del frontend, CORS/debug/traceback
  por configuración. Esto justifica su inclusión en la metodología y queda evidenciado
  en los dos reportes.
- Falsos positivos documentados (14): constantes de configuración, claves de caché,
  nombres generados con `uuid`, logs fijos, `os.listdir` de directorio propio.
  Detalle en `triage.md`.

## 5. Transparencia de IA

Este análisis se elaboró con asistencia de un modelo de lenguaje (Claude) integrado en el
flujo de OpenCode. Se documenta lo real:

- **Uso:** escritura/modificación de reglas YAML de Semgrep, del pipeline
  `procesar_sast.py` + `generar_triage.py`, y redacción de estos documentos. Todo comando
  de escaneo se ejecutó localmente; los resultados provienen de las ejecuciones.
- **Correcciones reales aplicadas durante la calibración** (basadas en observación de
  salidas de Semgrep, no en supuestos):
  1. `metavariable-regex` como hermano de `pattern-either` se ignoraba → reestructuración
     con `patterns:` + `pattern-either:` anidado.
  2. `metavariable-regex` anclaba al inicio del texto (con comillas) → `.*` al inicio.
  3. El patrón secuencial `os.path.join`→`open` no atravesaba bloques `with` → regla
     centrada en el `os.path.join` como sink.
  4. Error YAML `mapping values are not allowed here` → comillas en patrones.
  5. Duplicados entre packs (`tickets.py:187` en dos reglas) → fusión en triage.
  6. Desajuste de `check_id` con prefijo `seguridad.semgrep.reglas.` entre el JSON y el
     mapa de triage → normalización en ambos scripts (visible en `git diff`).
  7. La regla `bypassSecurityTrustHtml($ARG)` no detectaba llamadas de método
     (`this.sanitizer.…`) hasta usar `$OBJ.bypassSecurityTrustHtml($ARG)`; se localizó
     porque el fixture `safe-html.pipe.ts` no producía hallazgo (26/0).
- **Nada se inventó:** las severidades se basan en código; no hay CVSS/CVE de terceros.

## 6. Evidencias y reproducción

- Resultados crudos: `semgrep/resultados/resultados_sast.json` (27),
  `resultados_reglas_custom.json` (52), ambos con `errors: []`.
- Validación de reglas: `evidencias/reglas-pruebas/vulnerable/` (26) vs `corregido/` (0).
- Reportes con triage: `reportes/reporte_sast.{txt,csv}` y
  `reporte_reglas_custom.{txt,csv}`.
- Reproducción paso a paso (incluido el fix de `io_uring`): `seguridad/README.md`.

Cualquier lector puede re-validar este informe ejecutando los cinco bloques de comandos
del `seguridad/README.md` en un entorno base Debian/Ubuntu.