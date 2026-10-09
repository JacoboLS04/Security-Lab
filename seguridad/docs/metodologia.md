# Metodología del análisis de seguridad

## 1. Alcance

- **Objetivo:** identificación y clasificación de vulnerabilidades en
  `app-vulnerable/` (backend Flask + SQLite, frontend Angular), de acuerdo con el
  enunciado de la prueba técnica (§3.4 análisis de seguridad estático).
- **Superficie analizada:** `app-vulnerable/backend/` (57 archivos Python) y
  `app-vulnerable/frontend/` (componentes, servicios, pipes, entornos).
- **No está en alcance:** pruebas dinámicas de explotación sobre entornos desplegados,
  auditoría de dependencias (Software Composition Analysis), pentesting de infraestructura.

## 2. Herramienta

| Elemento | Valor |
|---|---|
| Herramienta principal | Semgrep (open source, análisis estático de patrones) |
| Versión | 1.180.0 |
| Motor | `semgrep-core` OSS |
| Python del runner | 3.12 (venv gestionado con `uv` en `/tmp/opencode/semgrep-venv`) |
| Packs estandar | `p/owasp-top-ten`, `p/python`, `p/javascript`, `p/typescript` |

El Python del sistema es 3.14.7 y no tiene `pip`; por eso Semgrep se instaló fuera del
repositorio (no contamina el entregable) con `uv venv --python 3.12`.

## 3. Limitacion ambiental conocida (documentada)

En esta máquina `semgrep-core` falla al arrancar el listener de `io_uring`:

```
Fatal error: [Could not allocate memory for io_uring queue (errno=12)]
```

Solución verificada: limitar el paralelismo del runner.

```bash
export SEMGREP_CORES=1
SEMGREP_CORES=1 /tmp/opencode/semgrep-venv/bin/semgrep scan --metrics=off --jobs 1 ...
```

Todas las ejecuciones usan este patrón.

## 4. Por qué no se usó `--config=auto`

`--config=auto` solicita activar la recopilación de métricas. Para no enviar telemetría
del código de la prueba, se desactivó (`--metrics=off`) y se usaron los packs estándar de
forma explícita:

```
p/owasp-top-ten  p/python  p/javascript  p/typescript
```

## 5. Reglas propias (17)

Las reglas estándar de Semgrep **no detectan** varios patrones del código objetivo
(SQLi por f-string en `search_service.py`, path traversal con `os.path.join`, pickle de
datos de usuario, secretos hardcodeados, etc.). Para cubrirlos se escribieron reglas
propias y se **validaron contra fixtures** antes de aplicarlas al código real.

| Archivo | Reglas |
|---|---|
| `semgrep/reglas/backend-seguridad-opc.yaml` | 13 reglas Python |
| `semgrep/reglas/frontend-seguridad-opc.yaml` | 4 reglas TypeScript/Angular |

Resultado de la validación (ver `evidencias/reglas-pruebas/`):

- Snippets `vulnerable/` (uno por regla, con la traza del patrón buscado): **26 hallazgos**.
- Snippets `corregido/` (mismo caso ya arreglado): **0 hallazgos**.

Esto reduce falsos positivos de las reglas propias y garantiza que miden "código
vulnerable vs. corregido", no solo ruido sintáctico.

### 5.1 Calibración real de las reglas (lecciones aplicadas)

Proceso iterativo, con pruebas en `/tmp` aisladas del repo:

1. **`metavariable-regex` como hermano de `pattern-either` se ignora.** Se evaluó
   `{pattern-either: [...], metavariable-regex: ...}` y Semgrep no aplicó la restricción.
   Solución: anidar `pattern-either` **dentro de `patterns:`** y colocar el
   `metavariable-regex` como hermano de ese patrón.
2. **`metavariable-regex` ancla al inicio del texto del metavariable** (incluidas las
   comillas). Un regex `^(select|insert|update|delete)` no casa con `"select ..."`.
   Solución: prefijo `.*` en el regex (`(?i).*(select|insert|update|delete)`).
3. **Los patrones secuenciales no atraviesan bloques `with`.** Una regla que buscaba
   `os.path.join` seguido de `open` no detectaba `with open(os.path.join(...))`. Solución:
   detectar el `os.path.join` sobre un directorio base y triagear esas aperturas, que es un
   patrón de "sink" estable para path traversal.
4. **YAML con `key: valor` tipo mapping** da `mapping values are not allowed here`; los
   patrones con comas/dos puntos deben ir entre comillas.
5. **Reglas estándar duplicadas por pack**: `tickets.py:187` lo marcan a la vez
   `python.django.security.injection.raw-html-format` y
   `python.flask.security.injection.raw-html-concat` (el pack Django también analiza
   Flask). El triage las fusiona como un solo hallazgo.
6. **Una llamada a método no casa con un patrón de llamada simple**: el patrón
   `bypassSecurityTrustHtml($ARG)` no detectaba `this.sanitizer.bypassSecurityTrustHtml(...)`;
   hay que usar `$OBJ.bypassSecurityTrustHtml($ARG)`. La regla quedó muerta hasta
   corregirlo y se detectó porque el fixture `safe-html.pipe.ts` no producía hallazgo
   (validación vulnerable 26 / corregido 0).

## 6. Procesamiento

- `semgrep/scripts/procesar_sast.py`: convierte el JSON de Semgrep en reportes TXT/CSV
  **sin modificar el JSON original** (evidencia cruda). Soporta `--min-severity` y
  `--triage`.
- `semgrep/scripts/generar_triage.py`: materializa un mapa de 79 decisiones
  (`check_id|ruta:línea` → estado/severidad/nota) en `triage.json`. Ver `docs/triage.md`.

## 7. Criterios de veredicto

- **True positive:** existe un flujo alcanzable desde entrada controlada (o configuración
  insegura) que materializa la debilidad, o es un patrón de configuración claramente
  incorrecto (secretos hardcodeados, `verify=False`, `DEBUG=True`).
- **False positive:** el patrón casa pero el contexto lo hace inocuo (constantes de
  config, claves de caché, nombres generados con `uuid`, `os.listdir` de un directorio
  propio).
- **Needs review:** hace falta información fuera del estático (ej. exposición latente de
  un blueprint condicionada a configuración).

## 8. Limitaciones declaradas

- Semgrep es **estático**: no demuestra explotabilidad; los hallazgos críticos que
  dependen de autenticación indican el rol requerido, pero no ejecutan el ataque.
- La severidad asignada se basa en: alcance de la entrada, requisito de autenticación
  y posible impacto (lectura/escritura de archivos, SQLi, RCE). **No se asignan CVSS,
  CVE ni OWASP/ASVS inventados**; los CWE/OWASP mostrados en los reportes provienen de los
  `metadata` que incorpora Semgrep, y si no existen se muestra "No disponible".
- La revisión manual cubre los endpoints y archivos de mayor exposición; no es una
  auditoría exhaustiva línea a línea de toda la base de código.