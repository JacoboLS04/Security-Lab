# Mini Gestor de Tickets - OPC (app-vulnerable)

Aplicacion de ejemplo para la **Parte 3 – Análisis Estático de Seguridad** de la
prueba técnica. Se compone de:

- `backend/` — API REST en **Flask** (Python) que reemplaza al prototipo
  monolítico original (`app.py`).
- `frontend/` — SPA en **Angular 15** que consume la API.
- `docs/` — material de apoyo para la evaluación (ver más abajo).

> ⚠️ **Esta aplicación contiene vulnerabilidades intencionales.** Está pensada
> exclusivamente para practicar análisis estático (SonarQube, Semgrep, Bandit,
> ESLint-security) y revisión manual. **No la despliegues en un entorno real ni
> accesible desde Internet.**

## Objetivo de la evaluación (sección 3.4)

Quien realiza la prueba debe:

1. Ejecutar al menos una herramienta de análisis estático sobre `backend/` y `frontend/`.
2. Complementar con **revisión manual** (varios hallazgos no los detecta ninguna herramienta).
3. Clasificar cada hallazgo: **ubicación**, **severidad** (crítica/alta/media/baja)
   y **mapeo a CWE / OWASP Top 10** cuando aplique.
4. **Distinguir los hallazgos reales de los falsos positivos**: la app incluye
   varios patrones que *parecen* vulnerables pero, por la arquitectura o por
   controles equivalentes, **no** lo son. Justificar cada descarte.


## Puesta en marcha

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py           # API en http://localhost:5000/api
```

Credenciales de demo: `admin` / `Optiplant2024!`

### Frontend
```bash
cd frontend
npm install
npm start               # http://localhost:4200 (proxy hacia el backend)
```

## Cómo correr las herramientas (sugerido)

```bash
# Python
pip install bandit semgrep
bandit -r backend -f txt
semgrep --config p/python --config p/flask backend

# Angular / TypeScript
cd frontend && npm run lint
semgrep --config p/javascript --config p/typescript src
```

## Alcance

`backend/api/internal.py` es un blueprint que **no** se registra en el paquete
distribuible (`Config.INTERNAL_API_ENABLED = False`). Se incluye a propósito
como caso de análisis de superficie de ataque: es código presente en el
repositorio pero no alcanzable por defecto. Tenlo en cuenta al clasificar.
