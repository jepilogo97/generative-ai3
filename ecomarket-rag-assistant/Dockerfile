# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Copiamos requirements primero para cachear pip
COPY requirements.txt .

# 2) Instala TORCH primero (fuente oficial CPU) con más tolerancia de red
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 5 --default-timeout 600 --only-binary=:all: --progress-bar off \
        torch==2.2.2 --extra-index-url https://download.pytorch.org/whl/cpu

# 3) Instala el resto (usa solo wheels, sin compilar; mismo timeout/reintentos)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 5 --default-timeout 600 --only-binary=:all: --progress-bar off \
        -r requirements.txt

# 4) Ahora sí el código
COPY . .

CMD ["streamlit", "run", "src/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
