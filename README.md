# Security-Lab · Despliegue OPC Tickets (Docker Compose)

Despliegue con **alta disponibilidad** de la API `opc-tickets` (backend Flask
de `app-vulnerable/backend`) mediante **Docker Compose**: **2 réplicas** +
**balanceador Nginx**, con persistencia y compatibilidad Windows/Linux, y guías
reproducibles para **Debian 12** y **Rocky Linux 9**.

| Directorio | Contenido |
|---|---|
| `app-vulnerable/` | Aplicación de ejemplo (backend Flask + frontend Angular 15) consumida por el despliegue. Su `README.md` explica cómo ejecutarla. |
| `infraestructura/` | Despliegue con **Docker Compose** (2 réplicas + Nginx) y scripts de preparación de SO para las VMs. Guía completa y reproducible (las capturas de pruebas las deja el responsable). |
| `docs/infraestructura/resumen_para_claude.md` | Contexto autosuficiente para validar diagramas de infraestructura con una herramienta IA. |
| `docs/infraestructura/redes.md` | Redes de punta a punta: asignación de IPs, tipos de conexión (NAT/Host-Only/bridge Docker), DHCP, DNS y flujo de paquetes. |
| `docs/infraestructura/pruebas-estres.md` | Plan de pruebas de carga, estrés y "fuerza bruta" sobre el balanceador, con umbrales editables para tu informe. |

## Punto de partida recomendado

1. **Infraestructura**: `infraestructura/README.md` (incluye la regla de
   creación manual de VMs en VirtualBox y el despliegue con `docker compose`).
2. **Redes**: `docs/infraestructura/redes.md`.
3. **Pruebas del balanceador**: `docs/infraestructura/pruebas-estres.md`.

> Regla de alcance: no se automatiza la creación de VMs ni la instalación de los
> sistemas operativos; el proyecto explica cómo hacerlo a mano y automatiza la
> preparación del SO y el despliegue con Docker.