# Herramientas de IA usadas en la contextualización (§3.6)

Propósito: documentar qué herramientas de IA se emplearon para agilizar la
lectura/contextualización del código y la infraestructura, cómo se ejecutaron,
su valor real y sus limitaciones.

## 1. Herramientas utilizadas

| Herramienta | Uso | Resultado |
|---|---|---|
| **Claude Code / opencode** (agente CLI) | Lectura y auditoría asistida del repositorio, redacción de `resumen_para_claude.md` y evidencias | Consolidación rápida de un repo de ~3.000 LOC; detección de patrones de riesgo guiada por prompts |
| **via CLI** (`opencode`, agente auxiliar `explore`) | Búsquedas de patrones (SQL por concatenación, `pickle`, `shell=True`, secretos) | Localización de hallazgos en minutos en vez de horas |
| **Bandit 1.9.4** (SAST, no-IA) | Escaneo estático del backend | 52 hallazgos (14 High / 14 Medium / 24 Low); salida en `docs/seguridad/sast/bandit-backend.txt` |
| **ESLint + eslint-plugin-security** | SAST del frontend Angular | **Ejecutado**: 18 archivos, 15 mensajes (2 de `security/*`); salida en `docs/seguridad/sast/eslint-frontend.txt` |

## 2. Comando curl usado para contextualizar un archivo ante la IA

Para dar contexto reproducible a un modelo sin cargar el repo completo, se
resume un archivo directamente por tubería:

```bash
# Resumir el contenido de la API vulnerable para la IA
curl -sL -X POST "https://api.anthropic.com/v1/messages" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "messages": [{
      "role": "user",
      "content": "Resume en bullets los riesgos de seguridad de este archivo: '"$(cat app-vulnerable/backend/api/admin.py)"'"
    }]
  }'
```

> En esta auditoría el contexto se aportó vía el agente CLI (que ya tiene
> acceso de lectura al workspace), por lo que **no fue necesario** ejecutar
> este curl de resumen por archivo.

## 3. Evaluación crítica

**Valor aportado**
- Reducción drástica del tiempo de lectura: el agente localizó en una pasada
  los ~20 puntos de riesgo que se validaron luego manualmente.
- Reproducibilidad: los prompts/archivos quedaron en `docs/` y `evidencias/`.
- Separación de responsabilidades: la IA propone, **el humano valida** los
  PoC y decide (p. ej. no corregir la app por política del ejercicio).

**Limitaciones detectadas**
- **Confusión de contexto por ambigüedad**: un primer sesgo asumió un valor
  como resultado cuando en realidad dependía del round-robin del balanceador
  (app1=8 filas vs app2=7). Fue necesario rediseñar la PoC por-replica.
- **Falsos positivos heredados de Bandit** (~9): no se pueden descartar sin
  leer el código; la IA ayudó a clasificarlos pero la revisión final es
  humana.
- **Asunciones de versionado**: el agente sugirió dependencias/detalles de
  entorno que luego se verificaron contra el stack real del host (Docker 29.8,
  Compose v5.4).

**Recomendación**
- Usar IA como **colega de revisión**, nunca como única fuente: todo hallazgo
  tiene que terminar con un PoC o una línea exacta del código.
- Incluir siempre el contexto real del entorno (donde se ejecuta, versions,
  salida de `docker ps`) en el prompt.
- Registrar prompts y evidencias para que el proceso sea auditable.

## 4. Pendiente relacionado
- Ninguno de SAST: tanto Bandit (backend) como ESLint (frontend) ya se
  ejecutaron y quedaron en `docs/seguridad/sast/`. Para reproducirlo con
  otros equipos: `npm install --no-audit --no-fund --ignore-scripts` y
  `npx eslint "src/**/*.ts" -f json` (frontend); `bandit -r backend`
  (backend, venv).