#!/usr/bin/env python3
"""Genera el JSON de triage (seguridad/semgrep/resultados/triage.json)
a partir de los dos JSON de hallazgos (estandar y reglas custom) y de un
mapa de decisiones manuales.

La clave de cada hallazgo es "check_id|ruta:linea". El proceso de triage:
  1. Vista previa: como los resultados de Semgrep pueden repetir la misma
     clave (misma regla y linea), el mapa de decisiones agrupa por clave.
  2. Deduplicacion: las reglas custom numeradas xN al final agrupa por
     clave sin repeticion (ver apply_dedup).
  3. El archivo generado es EVOLUTIVO: se puede regenerar ante cambios del
     codigo sin perder las decisiones ya tomadas.

Uso: python3 seguridad/semgrep/scripts/generar_triage.py
"""

from __future__ import annotations

import json
import os

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RESULTADOS = os.path.join(RAIZ, "semgrep", "resultados")
TRIAJE_SALIDA = os.path.join(RESULTADOS, "triage.json")

# Estado posible: "True positive" | "False positive" | "Needs review"
# Severidad final posible: Critica | Alta | Media | Baja | No aplica

DECISIONES = {
    # ------------------------------------------------------------------
    # Backend – SQL injection y construccion manual de SQL (reglas custom y estandar)
    # ------------------------------------------------------------------
    "opc-python-sql-construccion-manual|app-vulnerable/backend/api/admin.py:52": (
        "True positive", "Media",
        "Dimension llega por query param sin validacion y se interpola con %s. Confirmado: /api/admin/estadisticas (requiere auth)."),
    "opc-python-sql-construccion-manual|app-vulnerable/backend/api/reports.py:35": (
        "True positive", "Media",
        "Orden llega por query param y se concatena en ORDER BY (requiere auth). Permite inyeccion aunque limitada por GROUP BY."),
    "opc-python-sql-construccion-manual|app-vulnerable/backend/api/users.py:30": (
        "True positive", "Media",
        "campo y filtro concatenados en LIKE; /api/users/buscar requiere auth y devuelve datos de usuarios."),
    "opc-python-sql-construccion-manual|app-vulnerable/backend/services/search_service.py:16": (
        "True positive", "Critica",
        "SQL por concatenacion con q/estado del usuario. /api/tickets/buscar NO requiere auth (lista y buscar son publicos). Exfiltracion total de la BD sin autenticacion."),

    # Estandar (python.flask.security.injection.tainted-sql-string y db-cursor)
    "python.flask.security.injection.tainted-sql-string.tainted-sql-string|app-vulnerable/backend/api/admin.py:52": (
        "True positive", "Media", "Mismo hallazgo que la regla custom admin.py:52."),
    "python.flask.security.injection.tainted-sql-string.tainted-sql-string|app-vulnerable/backend/api/reports.py:35": (
        "True positive", "Media", "Mismo hallazgo que la regla custom reports.py:35."),
    "python.flask.security.injection.tainted-sql-string.tainted-sql-string|app-vulnerable/backend/api/users.py:30": (
        "True positive", "Media", "Mismo hallazgo que la regla custom users.py:30."),
    "python.flask.security.injection.tainted-sql-string.tainted-sql-string|app-vulnerable/backend/api/tickets.py:35": (
        "True positive", "Media",
        "limite/offset convertidos a int (menor riesgo) pero columna/direccion provienen de seleccion acotada. El casi-real es tickets.py:105."),
    "python.flask.security.injection.tainted-sql-string.tainted-sql-string|app-vulnerable/backend/api/tickets.py:105": (
        "True positive", "Critica",
        "UPDATE tickets con campos del usuario concatenados por .format; permite alterar filas ajenas (IDOR+escritura). Requiere auth."),
    "python.django.security.injection.sql.sql-injection-using-db-cursor-execute.sql-injection-db-cursor-execute|app-vulnerable/backend/api/admin.py:51": (
        "True positive", "Media", "Mismo hallazgo que admin.py:52."),

    # ------------------------------------------------------------------
    # Backend – Inyeccion de comandos
    # ------------------------------------------------------------------
    "opc-python-inyeccion-comando|app-vulnerable/backend/api/admin.py:67": (
        "True positive", "Critica",
        "ping -c 1 <host> con shell=True; host del usuario. /api/admin/diagnostico/ping exige admin o soporte, pero permite ejecucion arbitraria de comandos (RCE autenticado)."),
    "opc-python-inyeccion-comando|app-vulnerable/backend/api/internal.py:35": (
        "Needs review", "Media",
        "Los endpoints /internal requieren require_interno; el propio blueprint NO se registra salvo que INTERNAL_API_ENABLED=True. En el paquete distribuible esta desactivado, por lo que es una exposicion latente."),
    "opc-python-inyeccion-comando|app-vulnerable/backend/services/export_service.py:41": (
        "True positive", "Alta",
        "os.system(comando) donde comando interpola el nombre del archivo de exportacion (mismo entrypoint y dato del usuario que export_service.py:33): inyeccion de comandos via nombre/param con formato."),
    "opc-python-inyeccion-comando|app-vulnerable/backend/services/export_service.py:48": (
        "True positive", "Media",
        "subprocess.Popen(cmd, shell=True) con formato_destino provisto al conversor (los formatos se validan en export_service.FORMATOS, lo que reduce el riesgo)."),
    "opc-python-inyeccion-comando|app-vulnerable/backend/services/export_service.py:63": (
        "False positive", "No aplica",
        "os.system('rm -f <EXPORT_DIR>/*.bak'); no datos del usuario."),

    # Estandar (subprocess/shell)
    "python.flask.security.injection.subprocess-injection.subprocess-injection|app-vulnerable/backend/api/admin.py:67": (
        "True positive", "Critica", "Mismo hallazgo custom admin.py:67."),
    "python.lang.security.dangerous-subprocess-use.dangerous-subprocess-use|app-vulnerable/backend/api/admin.py:68": (
        "True positive", "Critica", "Mismo hallazgo custom admin.py:67."),
    "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true|app-vulnerable/backend/api/admin.py:68": (
        "True positive", "Critica", "Mismo hallazgo custom admin.py:67."),
    "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true|app-vulnerable/backend/services/export_service.py:48": (
        "True positive", "Media", "Mismo hallazgo custom export_service.py:48."),
    "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true|app-vulnerable/backend/api/internal.py:35": (
        "Needs review", "Media", "Latente salvo que se habilite INTERNAL_API_ENABLED."),

    # ------------------------------------------------------------------
    # Backend – Path traversal
    # ------------------------------------------------------------------
    "opc-python-path-traversal-apertura|app-vulnerable/backend/api/files.py:26": (
        "True positive", "Media",
        "El control 'if \"..\" in nombre' ocurre ANTES de unquote; ..%2f lo evade y hay lectura de archivos fuera de ADJUNTOS_DIR. Requiere auth para la variante /descargar-seguro; /descargar NO exige auth."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/api/files.py:47": (
        "True positive", "Media",
        "open(os.path.join(ADJUNTOS_DIR, nombre)) con lectura y respuesta text/html. /api/files/preview NO exige auth: lectura de cualquier archivo legible."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/api/files.py:71": (
        "True positive", "Media", "Escritura en disco con nombre del archivo sin normalizar (subir adjuntos). Exige auth."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/api/users.py:100": (
        "True positive", "Media", "Subida de avatar con nombre sin normalizar (users.py:100). Exige auth."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/api/admin.py:102": (
        "True positive", "Media",
        "Os.path.join(LOG_DIR, archivo) con lectura de logs; archivo desde query param permite salirse del directorio. Solo admin."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/services/backup_service.py:17": (
        "False positive", "Media", "destino con tempfile y uuid; sin dato del usuario."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/services/backup_service.py:33": (
        "False positive", "Baja",
        "El nombre proviene de os.listdir('/tmp') filtrado a opc-*.db.gz (archivos que crea el propio servicio); no hay entrada directa del usuario. Impacto limite a borrado de respaldos antiguos."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/services/export_service.py:33": (
        "True positive", "Media",
        "Nombre del archivo de exportacion sin normalizar (nombre desde query param en /admin/exportar)."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/services/import_service.py:53": (
        "True positive", "Alta",
        "Escritura de archivos dentro de un zip sin validar los nombres: zip-slip real (importar-zip). Exige auth. CWE-22/CWE-434."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/config.py:39": (
        "False positive", "No aplica", "Bibliotecas/constantes config, no datos del usuario."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/config.py:40": (
        "False positive", "No aplica", "Constante de config."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/config.py:41": (
        "False positive", "No aplica", "Constante de config."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/config.py:42": (
        "False positive", "No aplica", "Constante de config."),
    "opc-python-path-traversal-apertura|app-vulnerable/backend/core/logging_conf.py:13": (
        "False positive", "No aplica", "Log fijo app.log."),

    # ------------------------------------------------------------------
    # Backend – Criptografia y gestión de secretos
    # ------------------------------------------------------------------
    "opc-python-md5-crypto|app-vulnerable/backend/core/security.py:22": (
        "True positive", "Alta", "MD5 como hash de contraseña (hash_password)."),
    "opc-python-md5-crypto|app-vulnerable/backend/core/security.py:27": (
        "True positive", "Alta", "MD5 para verificar contraseña (verificar_password)."),
    "opc-python-md5-crypto|app-vulnerable/backend/services/cache_service.py:18": (
        "False positive", "No aplica", "Clave de cache, no criptografico."),
    "opc-python-md5-crypto|app-vulnerable/backend/services/cache_service.py:50": (
        "False positive", "No aplica", "Checksum de deduplicacion, no criptografico."),
    "python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5|app-vulnerable/backend/core/security.py:22": (
        "True positive", "Alta", "Mismo hallazgo custom security.py:22."),
    "python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5|app-vulnerable/backend/core/security.py:27": (
        "True positive", "Alta", "Mismo hallazgo custom security.py:27."),
    "python.lang.security.audit.md5-used-as-password.md5-used-as-password|app-vulnerable/backend/core/security.py:22": (
        "True positive", "Alta", "Mismo hallazgo custom security.py:22."),
    "python.lang.security.audit.md5-used-as-password.md5-used-as-password|app-vulnerable/backend/core/security.py:27": (
        "True positive", "Alta", "Mismo hallazgo custom security.py:27."),
    "python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5|app-vulnerable/backend/services/cache_service.py:18": (
        "False positive", "No aplica", "Clave de cache, no criptografico."),
    "python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5|app-vulnerable/backend/services/cache_service.py:50": (
        "False positive", "No aplica", "Checksum de deduplicacion."),
    "opc-python-aes-ecb|app-vulnerable/backend/core/security.py:96": (
        "True positive", "Media", "Cifrado AES-ECB con clave fija (128 bits) en FIELD_ENCRYPTION_KEY."),
    "opc-python-aes-ecb|app-vulnerable/backend/core/security.py:103": (
        "True positive", "Media", "Mismo modo ECB en descifrado."),
    "opc-python-entropia-debil-token|app-vulnerable/backend/core/security.py:43": (
        "True positive", "Alta", "random.seed(time()) permite predecir el codigo de reset en la misma ventana de segundo."),
    "opc-python-secreto-por-defecto|app-vulnerable/backend/config.py:13": (
        "True positive", "Media", "SECRET_KEY con default hardcodeado y JWT_SECRET fijo falla el requisito de cambio de secreto."),
    "opc-python-secretos-hardcodeados|app-vulnerable/backend/config.py:16": (
        "True positive", "Alta", "JWT_SECRET fijo en codigo: permite forjar tokens de cualquier rol."),
    "opc-python-secretos-hardcodeados|app-vulnerable/backend/config.py:17": (
        "False positive", "No aplica", "JWT_ALGORITHM es config de algoritmo, no secreto."),
    "opc-python-secretos-hardcodeados|app-vulnerable/backend/config.py:26": (
        "True positive", "Media", "SMTP_PASSWORD hardcodeado."),
    "opc-python-secretos-hardcodeados|app-vulnerable/backend/config.py:28": (
        "True positive", "Media", "AWS credentials hardcodeadas (values de ejemplo publicos, pero el patron es incorrecto)."),
    "opc-python-secretos-hardcodeados|app-vulnerable/backend/config.py:31": (
        "True positive", "Alta", "INTERNAL_API_KEY fija y compartida con el bundle del frontend (rompe la confianza del canal interno)."),
    "opc-python-tls-sin-verificar|app-vulnerable/backend/services/notification_service.py:22": (
        "True positive", "Baja", "ssl._create_unverified_context() para SMTP."),
    "opc-python-tls-sin-verificar|app-vulnerable/backend/services/notification_service.py:32": (
        "True positive", "Alta",
        "requests verify=False en enviar_webhook; combinado con URL arbitraria del usuario configura SSRF + man-in-the-middle."),
    "python.lang.security.unverified-ssl-context.unverified-ssl-context|app-vulnerable/backend/services/notification_service.py:22": (
        "True positive", "Baja", "Mismo hallazgo custom notification_service.py:22."),

    # ------------------------------------------------------------------
    # Backend – Deserializacion y libreria
    # ------------------------------------------------------------------
    "opc-python-pickle-inseguro|app-vulnerable/backend/services/import_service.py:18": (
        "True positive", "Critica",
        "pickle.loads sobre payload del usuario; /api/importar/paquete solo exige auth. Permite RCE autenticado."),
    "opc-python-pickle-inseguro|app-vulnerable/backend/services/import_service.py:31": (
        "True positive", "Media",
        "pickle.loads tras HMAC; el endpoint exige rol admin. La clave HMAC esta expuesta en el frontend, reduce la proteccion."),
    "python.lang.security.deserialization.avoid-pyyaml-load.avoid-pyyaml-load|app-vulnerable/backend/services/import_service.py:36": (
        "True positive", "Media", "yaml.load con Loader=yaml.Loader inseguro (puede construir objetos arbitrarios)."),

    # ------------------------------------------------------------------
    # Backend – Exposicion de informacion / config
    # ------------------------------------------------------------------
    "opc-python-exposicion-traceback|app-vulnerable/backend/core/errors.py:28": (
        "True positive", "Media", "El handler 500 devuelve traceback, tipo y config (DB path y DEBUG)."),
    "opc-python-debug-produccion|app-vulnerable/backend/app.py:96": (
        "True positive", "Baja", "app.run 0.0.0.0 es correcto en contenedor; el problema real es DEBUG por defecto en config."),
    "opc-python-debug-produccion|app-vulnerable/backend/config.py:51": (
        "True positive", "Media", "DEBUG=True por defecto; en produccion no debe activarse."),
    "opc-python-cors-permisivo|app-vulnerable/backend/config.py:49": (
        "True positive", "Media", "CORS_ORIGINS='*' con supports_credentials=True amplifica riesgos de robo de sesion por CSRF/CORS."),
    "python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host|app-vulnerable/backend/app.py:96": (
        "False positive", "No aplica", "El bind 0.0.0.0 es necesario dentro del contenedor; el riesgo real es DEBUG por defecto, cubierto por opc-python-debug-produccion (config.py:51)."),
    "python.lang.security.audit.insecure-file-permissions.insecure-file-permissions|app-vulnerable/backend/api/users.py:102": (
        "True positive", "Baja", "chmod 0o777 sobre archivo subido (avatar)."),
    "python.lang.security.audit.insecure-file-permissions.insecure-file-permissions|app-vulnerable/backend/core/logging_conf.py:20": (
        "True positive", "Baja", "chmod 0o666 sobre app.log."),

    # ------------------------------------------------------------------
    # Backend – Log de credenciales
    # ------------------------------------------------------------------
    "python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure|app-vulnerable/backend/api/auth.py:30": (
        "True positive", "Alta", "login() registra la password en texto plano en los logs."),

    # ------------------------------------------------------------------
    # Backend – JWT sin verificacion de firma
    # ------------------------------------------------------------------
    "python.jwt.security.unverified-jwt-decode.unverified-jwt-decode|app-vulnerable/backend/core/security.py:77": (
        "True positive", "Critica",
        "leer_claims con verify_signature=False usado por require_auth y require_rol; el token no se verifica. Cualquiera puede presentar claims propios (cambiar rol/uid). "),

    # ------------------------------------------------------------------
    # Backend – HTML generado por concatenacion (XSS lazy)
    # ------------------------------------------------------------------
    "python.flask.security.injection.raw-html-concat.raw-html-format|app-vulnerable/backend/api/tickets.py:142": (
        "True positive", "Media", "vista_html une campos del ticket en HTML; contenido inyectable llega al navegador con mimetype text/html."),
    "python.flask.security.injection.raw-html-concat.raw-html-format|app-vulnerable/backend/api/tickets.py:187": (
        "True positive", "Media", "etiqueta construye HTML por concatenacion con texto/color del usuario (reflejado)."),
    "python.django.security.injection.raw-html-format.raw-html-format|app-vulnerable/backend/api/tickets.py:187": (
        "True positive", "Media", "Mismo hallazgo tickets.py:187."),

    # ------------------------------------------------------------------
    # Frontend – XSS
    # ------------------------------------------------------------------
    "opc-ts-innerhtml-inseguro|app-vulnerable/frontend/src/app/features/login/login.component.ts:15": (
        "True positive", "Media", "[innerHTML] con el error del backend; el mensaje de /api/auth/login incluye texto controlado (username), permite XSS reflejado."),
    "opc-ts-marked-inseguro|app-vulnerable/frontend/src/app/features/tickets/ticket-detail.component.ts:30": (
        "True positive", "Media", "marked.parse sobre la descripcion del ticket y luego [innerHTML] en la vista (XSS almacenado)."),
    "opc-ts-marked-inseguro|app-vulnerable/frontend/src/app/features/tickets/ticket-detail.component.ts:34": (
        "True positive", "Media", "marked.parse sobre comentarios (XSS almacenado)."),
    "opc-ts-bypass-security-trust|app-vulnerable/frontend/src/app/shared/safe-html.pipe.ts:14": (
        "True positive", "Media", "bypassSecurityTrustHtml anula la sanitizacion; base de la cadena XSS (misma debilidad que la regla estandar angular-bypasssecuritytrust)."),
    "typescript.angular.security.audit.angular-domsanitizer.angular-bypasssecuritytrust|app-vulnerable/frontend/src/app/shared/safe-html.pipe.ts:14": (
        "True positive", "Media", "bypassSecurityTrustHtml anula la sanitizacion; base de la cadena XSS."),

    # ------------------------------------------------------------------
    # Frontend – Secretos en bundle
    # ------------------------------------------------------------------
    "opc-ts-secretos-hardcodeados|app-vulnerable/frontend/src/environments/environment.prod.ts:5": (
        "True positive", "Alta", "erpApiKey en bundle; el frontend inyecta X-Api-Key a /admin/ y /erp/."),
    "opc-ts-secretos-hardcodeados|app-vulnerable/frontend/src/environments/environment.prod.ts:6": (
        "True positive", "Alta", "jwtSharedSecret en bundle: permite forjar tokens (con backend que no verifica la firma, es una backdoor)."),
    "opc-ts-secretos-hardcodeados|app-vulnerable/frontend/src/environments/environment.ts:11": (
        "True positive", "Alta", "Mismo hallazgo en dev."),
    "opc-ts-secretos-hardcodeados|app-vulnerable/frontend/src/environments/environment.ts:12": (
        "True positive", "Alta", "Mismo hallazgo en dev."),
    "opc-ts-secretos-hardcodeados|app-vulnerable/frontend/src/environments/environment.prod.ts:13": (
        "False positive", "No aplica", "featureFlags (objeto de config, no secreto)."),
}


def _check_id_corto(check_id):
    """Las reglas locales de la config salen como
    seguridad.semgrep.reglas.<id>; las comparamos por su id basico."""
    if check_id.startswith("seguridad.semgrep.reglas."):
        return check_id[len("seguridad.semgrep.reglas."):]
    return check_id


def aplicar(lista_resultados):
    """Convierte cada finding a un dict triageado usando el mapa de decisiones."""
    triage = {}
    for r in lista_resultados:
        check = _check_id_corto(r["check_id"])
        clave = f"{check}|{r['path']}:{r['start']['line']}"
        decision = DECISIONES.get(clave)
        if decision is None:
            triage[clave] = {
                "estado": "Needs review",
                "severidad_final": "Pendiente",
                "nota": "Hallazgo sin decision manual en el mapa de triage.",
            }
        else:
            estado, sev_final, nota = decision
            triage[clave] = {
                "estado": estado,
                "severidad_final": sev_final,
                "nota": nota,
            }
    return triage


def cargar_resultados(ruta):
    with open(ruta, "r", encoding="utf-8") as fh:
        return json.load(fh).get("results", [])


def deduplicar(triage):
    """Si una misma regla+linea aparece mas de una vez (sub)fusionamos notas."""
    unicos = {}
    for clave, valor in triage.items():
        if clave not in unicos:
            unicos[clave] = dict(valor)
        else:
            unicos[clave]["nota"] += " (duplicado)"
    return unicos


def main():
    resultados_estandar = cargar_resultados(
        os.path.join(RESULTADOS, "resultados_sast.json"))
    resultados_custom = cargar_resultados(
        os.path.join(RESULTADOS, "resultados_reglas_custom.json"))
    triage = aplicar(resultados_estandar + resultados_custom)
    triage = deduplicar(triage)
    with open(TRIAJE_SALIDA, "w", encoding="utf-8") as fh:
        json.dump(triage, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"OK: {TRIAJE_SALIDA} con {len(triage)} decisiones.")


if __name__ == "__main__":
    main()