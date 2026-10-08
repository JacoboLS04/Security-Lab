# Sintaxis 1 es estable y disponible en Docker Community (sin BuildKit obsoleto).
# syntax=docker/dockerfile:1

# =============================================================================
# Imagen para el backend del Mini Gestor de Tickets (OPC).
#
# El Dockerfile vive en infraestructura/ (no en la aplicacion). El contexto
# de build es la raiz del repositorio y aqui se copia SOLO lo que la API
# necesita, sin tocar el codigo original en app-vulnerable/.
#
# Por que multi-stage:
#   requirements.txt fija PyYAML 5.3.1, que no publica wheels: hay que
#   compilarlo. La etapa "builder" instala un compilador C y deja las
#   dependencias ya resueltas en /wheels. La etapa final solo copia esos
#   wheels, de modo que la imagen de runtime no lleva compiladores ni
#   headers -> mas pequena y con menos superficie de ataque.
# =============================================================================

FROM python:3.9-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /src

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY app-vulnerable/backend/requirements.txt ./
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir /wheels -r requirements.txt

# -----------------------------------------------------------------------------
FROM python:3.9-slim-bookworm

RUN useradd --create-home --home-dir /app --shell /usr/sbin/nologin opc

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY app-vulnerable/backend/requirements.txt /app/requirements.txt

# Instalacion offline desde los wheels ya resueltos (sin compiladores).
RUN pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt \
    && rm -rf /wheels

# El proceso corre como usuario sin privilegios. La aplicacion escribe su
# base (SQLite), adjuntos, exportaciones y logs.
COPY --chown=opc:opc app-vulnerable/backend /app

# /app/data: raiz de datos persistentes (config.py -> APP_DATA_DIR=/app/data).
# Se crea con el dueno correcto: cuando Docker initializa un named volume en
# una ruta existente, copia el contenido del directorio y conserva su
# propiedades, de modo que la app (usuario no-root) puede escribir en el
# volumen sin problemas de permisos.
RUN mkdir -p /app/data && chown opc:opc /app/data

USER opc

EXPOSE 5000

# python app.py inicializa la base y levanta la API en 0.0.0.0:5000.
CMD ["python", "app.py"]