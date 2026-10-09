#!/usr/bin/env bash
# Reproduce el analisis de seguridad de la seccion `seguridad/` en un solo comando.
#
# Uso (desde la raiz del repositorio):
#   bash seguridad/semgrep/scripts/reproducir_analisis.sh [todo|fixtures|reportes]
#
#   todo      (por defecto) re-ejecuta ambos escaneos, valida las reglas con los
#             fixtures, genera el triage y reconstruye los reportes TXT/CSV.
#   fixtures  solo valida las reglas propias contra vulnerables/corregido.
#   reportes  solo regenera triage.json y los reportes a partir de los JSON ya
#             escaneados (util cuando solo cambian decisiones o documentos).
#
# Configuracion opcional por entorno:
#   SEMGREP_BIN  ruta del binario de semgrep (por defecto el venv de la instalacion).
#
# Salida: los JSON crudos en seguridad/semgrep/resultados/ y los reportes en
# seguridad/reportes/. Ningun JSON de evidencia queda alterado por los reportes.

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$RAIZ" || exit 1

SEMGREP_BIN="${SEMGREP_BIN:-/tmp/opencode/semgrep-venv/bin/semgrep}"
SCAN_STD="seguridad/semgrep/resultados/resultados_sast.json"
SCAN_CUSTOM="seguridad/semgrep/resultados/resultados_reglas_custom.json"
TRIAGE="seguridad/semgrep/resultados/triage.json"
REGLA_B="seguridad/semgrep/reglas/backend-seguridad-opc.yaml"
REGLA_F="seguridad/semgrep/reglas/frontend-seguridad-opc.yaml"
VULN="seguridad/evidencias/reglas-pruebas/vulnerable"
CORR="seguridad/evidencias/reglas-pruebas/corregido"
PY3="${PYTHON_BIN:-python3}"

salir() { echo -e "ERROR: $*" >&2; exit 1; }

comprobar_entorno() {
    [ -x "$SEMGREP_BIN" ] || salir "no se encuentra semgrep en '$SEMGREP_BIN'.
  Instalalo con:
    uv venv /tmp/opencode/semgrep-venv --python 3.12
    /tmp/opencode/semgrep-venv/bin/pip install semgrep==1.180.0
  O exporta SEMGREP_BIN con la ruta de tu propio binario de semgrep."
    command -v "$PY3" >/dev/null 2>&1 || salir "no se encuentra '$PY3' (Python 3)."
}

contar() { # $1 archivo JSON -> imprime numero de resultados (o "?" si falla)
    local n
    n="$("$PY3" -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["results"]))' "$1" 2>/dev/null)"
    echo "${n:-?}"
}

escaneo() { # $1 etiqueta  $2 salida  resto: configs
    local etiqueta="$1" salida="$2"; shift 2
    echo "==> [scan] $etiqueta -> $salida"
    SEMGREP_CORES=1 "$SEMGREP_BIN" scan --metrics=off --jobs 1 --quiet \
        --output "$salida" --json "$@" app-vulnerable \
        || salir "fallo el escaneo '$etiqueta'. Revisa el mensaje anterior (p.ej. redes,
  reglas YAML mal formadas o falta de la variable SEMGREP_CORES=1)."
    echo "    ok: $(contar "$salida") hallazgos en $salida"
}

scan_estandar() {
    escaneo "estandar (packs OWASP/Python/JS/TS)" "$SCAN_STD" \
        --config=p/owasp-top-ten --config=p/python \
        --config=p/javascript --config=p/typescript
}

scan_custom() {
    escaneo "reglas propias" "$SCAN_CUSTOM" \
        --config "$REGLA_B" --config "$REGLA_F"
}

fixtures() {
    local tmp
    tmp="$(mktemp)"
    echo "==> [fixtures] reglas propias contra snippets vulnerables (esperado >0)"
    SEMGREP_CORES=1 "$SEMGREP_BIN" scan --metrics=off --jobs 1 --json \
        --output "$tmp" --config "$REGLA_B" --config "$REGLA_F" "$VULN" 2>/dev/null \
        || true
    echo "    hallazgos en vulnerable: $(contar "$tmp" 2>/dev/null) (referencia: 26)"
    echo "==> [fixtures] reglas propias contra snippets corregidos (esperado 0)"
    SEMGREP_CORES=1 "$SEMGREP_BIN" scan --metrics=off --jobs 1 --json \
        --output "$tmp" --config "$REGLA_B" --config "$REGLA_F" "$CORR" 2>/dev/null \
        || true
    echo "    hallazgos en corregido:  $(contar "$tmp" 2>/dev/null) (referencia: 0)"
    rm -f "$tmp"
}

reporte() { # $1 salida-txt  $2 csv
    local txt="$1" csv="$2"
    "$PY3" seguridad/semgrep/scripts/procesar_sast.py \
        --input "${SCAN_ORIGEN}" --output "$txt" --csv "$csv" \
        --triage "$TRIAGE" || salir "fallo al generar $txt"
}

reportes() {
    [ -f "$SCAN_STD" ] && [ -f "$SCAN_CUSTOM" ] || salir "faltan los JSON de escaneo.
  Ejecuta primero el modo 'todo' (o re-escanea con semgrep)."
    echo "==> [triage] genera $TRIAGE"
    "$PY3" seguridad/semgrep/scripts/generar_triage.py \
        || salir "fallo al generar el triage (revisa DECISIONES en generar_triage.py)."
    SCAN_ORIGEN="$SCAN_STD"  reporte seguridad/reportes/reporte_sast.txt \
        seguridad/reportes/reporte_sast.csv
    SCAN_ORIGEN="$SCAN_CUSTOM" reporte seguridad/reportes/reporte_reglas_custom.txt \
        seguridad/reportes/reporte_reglas_custom.csv
    echo "==> reportes regenerados en seguridad/reportes/"
}

comprobar_entorno

modo="${1:-todo}"
case "$modo" in
    todo)
        scan_estandar
        scan_custom
        fixtures
        reportes
        ;;
    fixtures)
        fixtures
        ;;
    reportes)
        reportes
        ;;
    *)
        salir "modo desconocido: '$modo'. Uso: $0 [todo|fixtures|reportes]"
        ;;
esac

echo "==> Listo. Documento de referencia: seguridad/docs/informe_final.md"