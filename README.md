# Security-Lab · Prueba técnica OptiPlant Consultores

Prueba técnica para el cargo de **Ingeniero de Ciberseguridad y Soporte TI
Interno**. El repositorio se organiza en dos frentes:

| Directorio | Contenido |
|---|---|
| `app-vulnerable/` | Aplicación de ejemplo (backend Flask + frontend Angular 15) con **vulnerabilidades intencionales** para análisis estático (§3.4). Su `README.md` explica cómo ejecutarla y las herramientas sugeridas. |
| `infraestructura/` | Despliegue con **Docker Compose** del backend (2 réplicas + Nginx) con persistencia y compatibilidad Windows/Linux (§3.1 y §3.2). Guía completa y reproducible. |
| `docs/infraestructura/resumen_para_claude.md` | Contexto autosuficiente para validar diagramas de infraestructura con una herramienta IA. |
| `docs/seguridad/` | Análisis estático (SAST), informe de hallazgos de seguridad y plan de remediación. |
| `docs/herramientas-ia.md` | Documentación y evaluación crítica de las herramientas de IA utilizadas en la evaluación. |

## Punto de partida recomendado

1. **Seguridad (parte 1 de la prueba)**: `app-vulnerable/README.md` y
   `docs/seguridad/informe-seguridad.md`.
2. **Infraestructura (parte 2 de la prueba)**: `infraestructura/README.md`
   (incluye la regla de creación manual de VMs en VirtualBox y el despliegue
   con `docker compose`).

> Regla de alcance: no se automatiza la creación de VMs ni la instalación de los
> sistemas operativos; el proyecto explica cómo hacerlo a mano y automatiza la
> preparación del SO y el despliegue con Docker.
