#!/usr/bin/env python3
"""Procesa el JSON de resultados de Semgrep (resultados_sast.json) y genera
un reporte legible en TXT (y CSV opcional) sin modificar el JSON original.

Uso (desde la raiz del repo o desde `seguridad/`):

    python3 seguridad/semgrep/scripts/procesar_sast.py
      --input   seguridad/semgrep/resultados/resultados_sast.json
      --output  seguridad/reportes/reporte_sast.txt
      [--csv    seguridad/reportes/reporte_sast.csv]
      [--min-severity ERROR|WARNING|INFO]
      [--triage  seguridad/semgrep/resultados/triage.json]

El archivo de triage (opcional) es un mapa manual clave -> json con:
    { "check_id|path:linea": {
         "estado": "True positive|False positive|Pendiente",
         "severidad_final": "Critica|Alta|Media|Baja",
         "cwe": "...", "owasp": "...", "nota": "..."
      } }

El script nunca inventa CVE/CVSS/CWE/OWASP: si el dato no existe en el JSON
de Semgrep se muestra como "No disponible".
"""

import argparse
import csv
import json
import os
import sys

SEVERIDADES = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def cargar_json(ruta):
    if not os.path.isfile(ruta):
        sys.exit(f"ERROR: no existe el archivo de entrada: {ruta}")
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: el archivo {ruta} no es JSON valido: {e}")


def extraer_cwes(nodo):
    """Devuelve lista CWE del nodo extra (metadata.cwe o extra.cwe)."""
    extra = nodo.get("extra", {}) or {}
    cwes = []
    for acceso in (extra.get("cwe", []),):
        cwes.extend(acceso)
    metadata = extra.get("metadata", {}) or {}
    meta_cwes = metadata.get("cwe", []) or []
    for c in meta_cwes:
        if isinstance(c, dict):
            cwes.append(c.get("id", ""))
        else:
            cwes.append(str(c))
    return [c for c in cwes if c]


def extraer_owasp(nodo):
    extra = nodo.get("extra", {}) or {}
    metadata = extra.get("metadata", {}) or {}
    owasp = metadata.get("owasp", []) or []
    return [str(o) for o in owasp]


def extraer_refs(nodo):
    extra = nodo.get("extra", {}) or {}
    refs = extra.get("metadata", {}).get("references", []) or []
    return [str(r) for r in refs]


def clave_triage(hallazgo):
    check = hallazgo["check_id"]
    if check.startswith("seguridad.semgrep.reglas."):
        check = check[len("seguridad.semgrep.reglas."):]
    return f"{check}|{hallazgo['path']}:{hallazgo['start']['line']}"


def filtrar(resultados, min_severidad):
    if not min_severidad:
        return resultados
    nivel = SEVERIDADES.get(min_severidad.upper(), 1)
    return [
        r
        for r in resultados
        if SEVERIDADES.get(r.get("extra", {}).get("severity", "WARNING"), 1) <= nivel
    ]


def resumen_por_severidad(resultados):
    conteo = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for r in resultados:
        sev = r.get("extra", {}).get("severity", "WARNING")
        conteo[sev] = conteo.get(sev, 0) + 1
    return conteo


def linea_hallazgo(r, triage):
    extra = r.get("extra", {}) or {}
    sev = extra.get("severity", "WARNING")
    check = r.get("check_id", "desconocida")
    path = r.get("path", "?")
    ini = r.get("start", {}).get("line")
    fin = r.get("end", {}).get("line")
    ubicacion = f"{path}:{ini}-{fin}" if ini else path
    mensaje = (extra.get("message", "") or "").replace("\n", " ").strip()
    cwes = extraer_cwes(r)
    owasp = extraer_owasp(r)
    refs = extraer_refs(r)

    t = triage.get(clave_triage(r))
    estado = t.get("estado", "Pendiente") if t else "Pendiente"
    sev_final = t.get("severidad_final", "-") if t else "-"

    lineas = [
        f"[{sev}] {check}",
        f"  Ubicacion : {ubicacion}",
        f"  Mensaje   : {mensaje[:240]}" if mensaje else "  Mensaje   : (sin mensaje)",
        f"  CWE       : {', '.join(sorted(set(cwes))) if cwes else 'No disponible'}",
        f"  OWASP     : {', '.join(sorted(set(owasp))) if owasp else 'No disponible'}",
        f"  Referencias: {', '.join(refs) if refs else 'No disponible'}",
        f"  Triage    : {estado} | Severidad final: {sev_final}",
    ]
    if t and t.get("nota"):
        lineas.append(f"  Nota      : {t['nota']}")
    return lineas


def main():
    parser = argparse.ArgumentParser(description="Procesa resultados de Semgrep (JSON) a TXT/CSV.")
    parser.add_argument("--input", default="seguridad/semgrep/resultados/resultados_sast.json")
    parser.add_argument("--output", default="seguridad/reportes/reporte_sast.txt")
    parser.add_argument("--csv", help="Ruta opcional de salida CSV")
    parser.add_argument("--min-severity", choices=["ERROR", "WARNING", "INFO"],
                        help="Filtra por severidad minima de la regla")
    parser.add_argument("--triage", help="JSON opcional con estados de triage manual")
    args = parser.parse_args()

    datos = cargar_json(args.input)
    resultados = datos.get("results", [])
    version = datos.get("version", "No disponible")

    triage = {}
    if args.triage:
        triage = cargar_json(args.triage)

    filtrados = filtrar(resultados, args.min_severity)
    conteo = resumen_por_severidad(filtrados)
    total_aut = sum(conteo.values())

    if not filtrados:
        salida = (
            f"REPORTE SAST - Semgrep v{version}\n"
            f"Sin hallazgos para el filtro aplicado "
            f"(min-severity={args.min_severity or 'ninguno'}).\n"
            f"Total de resultados en el JSON: {len(resultados)}\n"
        )
    else:
        lineas = [f"REPORTE SAST - Semgrep v{version}", ""]
        lineas.append(f"Resultados totales en JSON: {len(resultados)}")
        lineas.append(
            f"Resultados mostrados: {total_aut} "
            f"(ERROR={conteo['ERROR']}, WARNING={conteo['WARNING']}, INFO={conteo['INFO']})"
        )
        lineas.append(f"Filtro min-severity: {args.min_severity or 'ninguno'}")
        lineas.append(f"Errores de ejecucion de Semgrep: {len(datos.get('errors', [])) or 0}")
        lineas.append("")
        lineas.append("=" * 78)
        for r in sorted(
            filtrados,
            key=lambda x: (SEVERIDADES.get(x["extra"].get("severity", "WARNING"), 1), x["path"], x["check_id"]),
        ):
            lineas.extend(linea_hallazgo(r, triage))
            lineas.append("-" * 78)
        salida = "\n".join(lineas) + "\n"

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(salida)
    total_triage = len(triage)
    print(f"OK: {args.output} generado ({total_aut} hallazgos).")
    print(f"Hallazgos en triage manual: {total_triage}")
    if total_triage:
        fp = sum(1 for t in triage.values() if t.get("estado") == "False positive")
        tp = sum(1 for t in triage.values() if t.get("estado") == "True positive")
        print(f"  - True positives: {tp}, False positives: {fp}, "
              f"Pendientes: {total_triage - tp - fp}")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8", newline="") as fh:
            escritor = csv.writer(fh)
            escritor.writerow([
                "severidad_regla", "check_id", "archivo", "linea_inicial",
                "linea_final", "mensaje", "cwe", "owasp", "estado_triage",
                "severidad_final",
            ])
            for r in filtrados:
                t = triage.get(clave_triage(r))
                escritor.writerow([
                    r.get("extra", {}).get("severity", ""),
                    r.get("check_id", ""),
                    r.get("path", ""),
                    r.get("start", {}).get("line", ""),
                    r.get("end", {}).get("line", ""),
                    (r.get("extra", {}).get("message", "") or "").replace("\n", " ")[:240],
                    ", ".join(extraer_cwes(r)),
                    ", ".join(extraer_owasp(r)),
                    t.get("estado", "Pendiente") if t else "Pendiente",
                    t.get("severidad_final", "") if t else "",
                ])
        print(f"OK: {args.csv} generado ({total_aut} filas).")


if __name__ == "__main__":
    main()