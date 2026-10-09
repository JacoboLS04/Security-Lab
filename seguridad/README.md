# Sección de seguridad – Prueba técnica OptiPlant

Análisis SAST reproducible sobre `app-vulnerable/` (backend Flask + frontend Angular) y
revisión manual del código, **sin inventar datos**: los CWE/OWASP que muestran los
reportes provienen de los metadatos de las reglas de Semgrep; si no existen figura
"No disponible". No se asignan CVSS ni CVE de terceros.

Este documento es la **guía de uso**: cómo reproducir el análisis, qué esperar en cada
paso, cómo leer los reportes y cómo resolver los problemas típicos.

---

## 1. Estructura de la sección

```
seguridad/
├── README.md                     <- este archivo (guía de uso y reproducción)
├── docs/
│   ├── metodologia.md            <- cómo se hizo: entorno, comandos y limitaciones
│   ├── revision_manual.md        <- revisión punto a punto por archivo/endpoint
│   ├── triage.md                 <- cómo se triagearon los 79 hallazgos
│   ├── plan_remediacion.md       <- correcciones priorizadas por severidad
│   └── informe_final.md          <- resumen ejecutivo y 28 vulnerabilidades consolidadas
├── semgrep/
│   ├── reglas/
│   │   ├── backend-seguridad-opc.yaml     <- 13 reglas Python
│   │   └── frontend-seguridad-opc.yaml    <- 4 reglas TypeScript/Angular
│   ├── resultados/
│   │   ├── resultados_sast.json           <- scan estándar (27 hallazgos, evidencia cruda)
│   │   ├── resultados_reglas_custom.json  <- scan con reglas propias (52 hallazgos)
│   │   └── triage.json                    <- 79 decisiones de triage manual
│   └── scripts/
│       ├── reproducir_analisis.sh         <- todo en un comando (guía rápida)
│       ├── procesar_sast.py               <- JSON -> reporte TXT + CSV
│       └── generar_triage.py              <- genera triage.json desde el mapa de decisiones
├── evidencias/
│   └── reglas-pruebas/
│       ├── vulnerable/          <- fixtures vulnerables (26 hallazgos esperados)
│       └── corregido/           <- fixtures corregidos (0 hallazgos)
└── reportes/
    ├── reporte_sast.txt / .csv            <- escaneo estándar con triage
    └── reporte_reglas_custom.txt / .csv   <- reglas propias con triage
```

## 2. Resultado en una línea

| Escaneo | Hallazgos | Notas |
|---|---|---|
| Packs estándar (OWASP Top 10 + Python + JS + TS) | 27 | 12 ERROR, 15 WARNING |
| Reglas propias (17) | 52 | cubren lo que el estándar no ve |
| Triage manual | 79 decisiones | 64 TP, 14 FP, 1 en revisión |
| Vulnerabilidades consolidadas | **28** | 5 críticas, 8 altas, 12 medias, 3 bajas |

El estándar **no** detecta SQLi por f-string (`search_service.py`), path traversal,
pickle ni secretos hardcodeados; por eso existen las reglas propias.
Resumen ejecutivo en `docs/informe_final.md`.

## 3. Guía rápida (todo en un comando)

Requisitos: **Python 3**, **Semgrep** instalado y ejecutar desde la **raíz del repo**.

```bash
bash seguridad/semgrep/scripts/reproducir_analisis.sh todo
```

Ejecuta en orden: escaneo estándar → escaneo con reglas propias → validación de los
fixtures → triage → reportes. Solo necesitas el binario de semgrep en su ruta por defecto
(ver paso 1 de la sección 4) o `export SEMGREP_BIN=/ruta/a/semgrep`.

Variantes útiles:

```bash
bash seguridad/semgrep/scripts/reproducir_analisis.sh fixtures   # solo valida reglas
bash seguridad/semgrep/scripts/reproducir_analisis.sh reportes   # rehace triage/reportes
```

Salida esperada del modo `todo`:

```
==> [scan] estándar ...          ok: 27 hallazgos
==> [scan] reglas propias ...    ok: 52 hallazgos
==> [fixtures] vulnerable ...    hallazgos en vulnerable: 26 (referencia: 26)
==> [fixtures] corregido ...     hallazgos en corregido:  0 (referencia: 0)
==> [triage] genera triage.json  OK: ... con 79 decisiones.
==> [reportes] ...               OK: seguridad/reportes/reporte_*.txt|csv
```

## 4. Manual paso a paso

> Entorno probado: Debian 12, usuario sin root. Python del sistema 3.14 (sin `pip`),
> por eso Semgrep se instala con `uv` en un venv **fuera del repo** para no contaminar
> el proyecto.

### 4.1 Instalar Semgrep

```bash
# uv (gestor de Python) si no existe
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
# Python 3.12 aislado + Semgrep 1.180.0
uv venv /tmp/opencode/semgrep-venv --python 3.12
/tmp/opencode/semgrep-venv/bin/pip install semgrep==1.180.0
```

Comprueba: `/tmp/opencode/semgrep-venv/bin/semgrep --version` → `1.180.0`.

### 4.2 Variable `SEMGREP_CORES`

Este equipo dispara un fallo conocido de `semgrep-core` (`io_uring_queue_init` /
`Cannot allocate memory`). La mitigación es fijar el paralelismo del runner:

```bash
export SEMGREP_CORES=1
```

Todos los comandos siguientes y el script `reproducir_analisis.sh` la usan.

### 4.3 Escaneo estándar

```bash
SEMGREP_CORES=1 /tmp/opencode/semgrep-venv/bin/semgrep scan \
  --metrics=off --jobs 1 --output \
  seguridad/semgrep/resultados/resultados_sast.json --json \
  --config=p/owasp-top-ten --config=p/python \
  --config=p/javascript --config=p/typescript \
  app-vulnerable
```

> `--config=auto` exigiría activar métricas; se usa `--metrics=off` y packs explícitos
> para no enviar telemetría.

### 4.4 Escaneo con reglas propias

```bash
SEMGREP_CORES=1 /tmp/opencode/semgrep-venv/bin/semgrep scan \
  --metrics=off --jobs 1 --output \
  seguridad/semgrep/resultados/resultados_reglas_custom.json --json \
  --config seguridad/semgrep/reglas/backend-seguridad-opc.yaml \
  --config seguridad/semgrep/reglas/frontend-seguridad-opc.yaml \
  app-vulnerable
```

### 4.5 Validar las reglas con fixtures

Garantiza que cada regla mide "vulnerable vs. corregido", no solo ruido:

```bash
SEMGREP_CORES=1 /tmp/opencode/semgrep-venv/bin/semgrep scan --metrics=off --jobs 1 \
  --config seguridad/semgrep/reglas/backend-seguridad-opc.yaml \
  --config seguridad/semgrep/reglas/frontend-seguridad-opc.yaml \
  seguridad/evidencias/reglas-pruebas/vulnerable     # esperado: 26 hallazgos
SEMGREP_CORES=1 /tmp/opencode/semgrep-venv/bin/semgrep scan --metrics=off --jobs 1 \
  --config seguridad/semgrep/reglas/backend-seguridad-opc.yaml \
  --config seguridad/semgrep/reglas/frontend-seguridad-opc.yaml \
  seguridad/evidencias/reglas-pruebas/corregido      # esperado: 0 hallazgos
```

### 4.6 Triage y reportes

```bash
python3 seguridad/semgrep/scripts/generar_triage.py
python3 seguridad/semgrep/scripts/procesar_sast.py \
  --input seguridad/semgrep/resultados/resultados_sast.json \
  --output seguridad/reportes/reporte_sast.txt \
  --csv seguridad/reportes/reporte_sast.csv \
  --triage seguridad/semgrep/resultados/triage.json
python3 seguridad/semgrep/scripts/procesar_sast.py \
  --input seguridad/semgrep/resultados/resultados_reglas_custom.json \
  --output seguridad/reportes/reporte_reglas_custom.txt \
  --csv seguridad/reportes/reporte_reglas_custom.csv \
  --triage seguridad/semgrep/resultados/triage.json
```

> Los JSON crudos no se tocan: los reportes se generan desde ellos y aplicación del
> triage es solo de lectura.

## 5. Qué esperar (referencia de salidas)

| Paso | Artifacto | Esperado |
|---|---|---|
| 4.3 | `resultados_sast.json` | `"errors": []`, 27 resultados, Semgrep 1.180.0 |
| 4.4 | `resultados_reglas_custom.json` | `"errors": []`, 52 resultados |
| 4.5 | salida de consola | vulnerable 26 / corregido 0 |
| 4.6 | `triage.json` | 79 claves: 64 TP, 14 FP, 1 Needs review |
| 4.6 | `reporte_sast.csv` | 27 filas: 24 TP + 3 FP |
| 4.6 | `reporte_reglas_custom.csv` | 52 filas: 40 TP + 11 FP + 1 pendiente |

Semgrep es determinista para el mismo árbol, versión y reglas. Si un número cambia al
re-scanear, revisa antes de asumir: qué versión de semgrep se usó, si el código o las
reglas se modificaron, o si se varió el conjunto de packs/`--config`.

## 6. Cómo leer los reportes

### Formato TXT

Cada hallazgo es un bloque con la localización, mensaje, CWE/OWASP (si los declara la
regla) y el resultado del triage:

```
[ERROR] opc-python-sql-construccion-manual
  Ubicacion : app-vulnerable/backend/services/search_service.py:16-16
  Mensaje   : Consulta SQL construida con datos del usuario (% / f-string)...
  CWE       : CWE-89  | OWASP : A03:2021 - Injection
  Triage    : True positive | Severidad final: Critica
  Nota      : f-string sobre parametro de busqueda; endpoint sin auth.
```

### Columnas del CSV

`severidad_regla` (ERROR/WARNING que definió la regla), `check_id`, `archivo`,
`linea_inicial`, `linea_final`, `mensaje`, `cwe`, `owasp`, **`estado_triage`** y
**`severidad_final`** (esta última es la decisión manual, no la de la regla).

### Estados de triage

| Estado | Qué significa |
|---|---|
| `True positive` | Debilidad real y alcanzable; cuenta para la consolidación. |
| `False positive` | El patrón casa pero el contexto lo hace inocuo; se justifica en `docs/triage.md`. |
| `Needs review` | Necesita información fuera del estático (ej. `internal.py:35`, latente). |

## 7. Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| `Fatal error: ... io_uring_queue_init` o `Cannot allocate memory` | Falta `SEMGREP_CORES=1 --jobs 1`. Exporta la variable y repite. |
| `semgrep: command not found` | No está en el `PATH`. Usa la ruta del venv (`/tmp/opencode/semgrep-venv/bin/...`) o `export SEMGREP_BIN=...` en el script. |
| `uv: command not found` | Instala uv (paso 4.1) o usa un Python 3.12 propio. |
| `pip` da `externally-managed-environment` | Usa el venv de uv; no instales en el Python del sistema. |
| `--config=auto` pide aceptar métricas | Por diseño: `--metrics=off` + packs explícitos (sección 4.3). |
| `mapping values are not allowed here` al usar las reglas | La regla YAML quedó mal formada; los patrones con `:` deben ir entre comillas. |
| `Too many findings?` en consola | Aviso informativo de Semgrep Pro; **no** es un error. |
| El CSV sale todo `Pendiente` | `triage.json` está desactualizado o el `check_id` no casa (p.ej. prefijo `seguridad.semgrep.reglas.`); regenera con `generar_triage.py`. |
| Un hallazgo roza dos reglas (duplicado) | Es esperado (packs solapados, ver `docs/triage.md`); la consolidación los fusiona. |

## 8. Documentos de referencia

| Documento | Para qué |
|---|---|
| `docs/metodologia.md` | Entorno, comandos, calibración de reglas y limitaciones. |
| `docs/triage.md` | Criterios y las 79 decisiones (TP/FP/pendiente) con justificación. |
| `docs/revision_manual.md` | Revisión punto a punto de endpoint y archivo. |
| `docs/plan_remediacion.md` | Correcciones priorizadas (nada aplicado todavía). |
| `docs/informe_final.md` | Informe ejecutivo, 28 vulnerabilidades consolidadas y transparencia de IA. |

La reproducibilidad se validó ejecutando `reproducir_analisis.sh todo` de principio a
fin (27/52/26/0/79).