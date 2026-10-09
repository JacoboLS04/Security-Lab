# Triage de hallazgos

## 1. Qué es el triage en este análisis

Semgrep devuelve candidatos (patrones que casan), no vulnerabilidades confirmadas. El
triage decide, por cada hallazgo, si es:

- **True positive (TP)**: debilidad real y alcanzable.
- **False positive (FP)**: el patrón casa pero el contexto lo hace inocuo.
- **Needs review**: requiere información fuera del análisis estático.

La severidad asignada (`Critica / Alta / Media / Baja`) es **propia, basada en alcance de
la entrada, requisito de autenticación e impacto probable**. No se usan CVSS/CVE.

## 2. Cómo se materializa

`semgrep/scripts/generar_triage.py` contiene el mapa `DECISIONES` con las claves
`check_id|ruta:línea` de **todos** los hallazgos (estándar + reglas propias) y genera
`semgrep/resultados/triage.json` (79 decisiones). Los reportes finales
(`reportes/reporte_*.txt|csv`) cruzan cada hallazgo con ese JSON y nadie altera los JSON
de evidencia cruda.

## 3. Resumen de las 79 decisiones

| Estado | Count | Detalle |
|---|---|---|
| True positive | 64 | 40 de reglas propias + 24 de la estandar (muchos son el mismo fallo visto por dos reglas) |
| False positive | 14 | 11 de reglas propias + 3 de la estandar |
| Needs review | 1 | `internal.py:35` (endpoint `/internal/exec` latente) |

### 3.1 False positives documentados

| Hallazgo | Motivo |
|---|---|
| `config.py:39-42` (path base) | Constantes de configuración, no datos del usuario |
| `logging_conf.py:13` | Log fijo `app.log` |
| `backup_service.py:17` | Nombre de respaldo con `uuid4().hex` |
| `backup_service.py:33` | Nombre desde `os.listdir('/tmp')` filtrado a `opc-*.db.gz` |
| `config.py:17` (JWT_ALGORITHM) | Configuración de algoritmo, no secreto |
| `cache_service.py:18/50` (MD5) | Clave de caché / checksum de deduplicación, no criptografía |
| `export_service.py:63` | `rm -f <dir>/_*.bak` sin datos del usuario |
| `app.py:96` (bind 0.0.0.0) | Necesario en contenedor; el riesgo real está en el `DEBUG` (config.py:51) |

### 3.2 Pendiente de revisión

| Hallazgo | Nota |
|---|---|
| `internal.py:35` (`opc-python-inyeccion-comando`) | `/internal/exec` ejecuta `subprocess.getoutput(cmd)` del cuerpo de la petición. El blueprint **no se registra** salvo que `INTERNAL_API_ENABLED=True`, y en el paquete distribuible está desactivado. Se mantiene **Needs review**: si en algún despliegue se activa el flag con la clave estática expuesta en el frontend (`environment.prod.ts:5` => `config.py:31`), se convierte en RCE no autenticado. |

## 4. Duplicados entre reglas estándar y propias

Ambos escáneres apuntan a los mismos fallos con IDs distintos. En el informe consolidado
se fusionan; los reportes crudos los listan por separado con la nota "Mismo hallazgo ...".

Ejemplos:

- `admin.py:67` (ping con shell=True): lo marcan `opc-python-inyeccion-comando`
  (propia), `subprocess-injection`, `subprocess-shell-true` y
  `dangerous-subprocess-use` (estándar). **1 vulnerabilidad.**
- `security.py:22/27` (MD5): `opc-python-md5-crypto` + `md5-used-as-password` +
  `insecure-hash-algorithm-md5`. **1 vulnerabilidad.**
- `export_service.py:48`: `opc-python-inyeccion-comando` + `subprocess-shell-true`.
  **1 vulnerabilidad.**

## 5. Resultado por escaneo (con triage)

### Escaneo estándar (27 hallazgos)

| Estado | Severidad final de los TP |
|---|---|
| 24 TP | JWT sin firma (Crítica), SQLi `tickets.py:105` (Crítica), ping (Crítica), MD5 (2), log de contraseña, path/permissions, XSS HTML, `verify=False`, etc. |
| 3 FP | `insecure-file-permissions` repetidas / contextos de configuración |
| 0 Needs review | — |

### Reglas propias (52 hallazgos)

| Estado | Severidad final de los TP |
|---|---|
| 40 TP | 3 Crítica (SQLi `search_service.py`, ping, pickle), 12 Alta, 23 Media, 2 Baja |
| 11 FP | los de la tabla 3.1 |
| 1 Needs review | `internal.py:35` |

## 6. Consolidación final

Fusionando duplicados (mismo fallo visto por dos reglas/escáneres) quedan **28
vulnerabilidades**: 5 Críticas, 8 Altas, 12 Medias, 3 Bajas, más 1 exposición latente en
revisión. La lista completa con rutas y remedios está en `informe_final.md` y en el
`plan_remediacion.md`.