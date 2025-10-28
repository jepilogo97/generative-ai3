# =========================
# EcoMarket RAG – Makefile
# =========================

# ---- Config ----
APP_NAME      ?= pedidos-app
OLLAMA_NAME   ?= ollama
STREAMLIT_PORT?= 8501
OLLAMA_PORT   ?= 11434
MODEL_NAME    ?= llama3.2:3b
PY            ?= python
COMPOSE := docker compose
SERVICE := pedidos-app

# ---- Ayuda ----
.PHONY: help
help:
	@echo "Comandos disponibles:"
	@echo ""
	@echo "🚀 Inicio rápido:"
	@echo "  make first-run    - Primera instalación completa (build + up + modelo)"
	@echo ""
	@echo "📦 Operaciones básicas:"
	@echo "  make build        - Construye las imágenes Docker"
	@echo "  make up           - Levanta todos los contenedores"
	@echo "  make down         - Detiene y elimina los contenedores"
	@echo "  make restart      - Reinicia los contenedores"
	@echo "  make logs         - Muestra logs de todos los servicios"
	@echo "  make logs-app     - Muestra logs solo de la app"
	@echo "  make logs-ollama  - Muestra logs solo de Ollama"
	@echo ""
	@echo "🤖 Ollama:"
	@echo "  make setup-ollama - Descarga el modelo LLM en Ollama"
	@echo "  make check-ollama - Verifica modelos instalados"
	@echo "  make ollama-shell - Abre shell en contenedor Ollama"
	@echo ""
	@echo "📊 Data & RAG:"
	@echo "  make ingest       - Ejecuta ingesta de datos (crea índice FAISS)"
	@echo "  make clean        - Limpia artefactos locales"
	@echo ""
	@echo "🔧 Utilidades:"
	@echo "  make check        - Verifica Docker y entorno"
	@echo "  make status       - Muestra estado de contenedores"
	@echo "  make shell        - Abre shell en contenedor de app"

# ---- Checks ----
.PHONY: check
check:
	@docker --version >/dev/null 2>&1 || (echo "❌ Docker no disponible"; exit 1)
	@docker-compose --version >/dev/null 2>&1 || (echo "❌ Docker Compose no disponible"; exit 1)
	@$(PY) --version
	@echo "✅ Entorno OK"

# ---- Build/Run ----
.PHONY: build
build:
	@echo "🔨 Construyendo imágenes..."
	docker-compose build --no-cache
	@echo "✅ Build completado"

.PHONY: up
up:
	@echo "🚀 Levantando servicios..."
	docker-compose up -d
	@echo ""
	@echo "✅ Servicios iniciados:"
	@echo "   • Streamlit:  http://localhost:$(STREAMLIT_PORT)"
	@echo "   • Ollama:     http://localhost:$(OLLAMA_PORT)"
	@echo ""
	@echo "💡 Usa 'make logs' para ver los logs"
	@echo "💡 Usa 'make check-ollama' para verificar el modelo"

.PHONY: down
down:
	@echo "🛑 Deteniendo servicios..."
	docker-compose down
	@echo "✅ Servicios detenidos"

.PHONY: restart
restart: down up

.PHONY: status
status:
	@echo "📊 Estado de los contenedores:"
	@docker-compose ps

# ---- Logs ----
.PHONY: logs
logs:
	docker-compose logs -f

.PHONY: logs-app
logs-app:
	docker-compose logs -f app

.PHONY: logs-ollama
logs-ollama:
	docker-compose logs -f ollama

# ---- Ollama ----
.PHONY: setup-ollama
setup-ollama:
	@echo "📦 Descargando modelo $(MODEL_NAME) en Ollama..."
	@echo "⏳ Esto puede tardar varios minutos dependiendo del tamaño del modelo..."
	docker exec $(OLLAMA_NAME) ollama pull $(MODEL_NAME)
	@echo "✅ Modelo $(MODEL_NAME) descargado"
	@make check-ollama

.PHONY: check-ollama
check-ollama:
	@echo "🔍 Modelos instalados en Ollama:"
	@docker exec $(OLLAMA_NAME) ollama list || echo "❌ Ollama no está corriendo"

.PHONY: ollama-shell
ollama-shell:
	@echo "🐚 Abriendo shell en contenedor Ollama..."
	docker exec -it $(OLLAMA_NAME) /bin/bash

# ---- Primera ejecución ----
.PHONY: first-run
first-run: check build up wait-ollama setup-ollama ingest
	@echo ""
	@echo "🎉 ¡Configuración inicial completa!"
	@echo ""
	@echo "✅ Servicios disponibles:"
	@echo "   • Streamlit:  http://localhost:$(STREAMLIT_PORT)"
	@echo "   • Ollama:     http://localhost:$(OLLAMA_PORT)"
	@echo ""
	@echo "🚀 Tu aplicación está lista para usar"
	@echo "💡 Usa 'make logs' para ver los logs en tiempo real"

.PHONY: wait-ollama
wait-ollama:
	@echo "⏳ Esperando que Ollama esté listo..."
	@timeout=60; \
	while ! docker exec $(OLLAMA_NAME) curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do \
		timeout=$$((timeout - 1)); \
		if [ $$timeout -le 0 ]; then \
			echo "❌ Timeout esperando Ollama"; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	@echo "✅ Ollama está listo"

.PHONY: warmup
warmup:
	@echo "🔥 Descargando el modelo en Ollama..."
	@if docker compose ps --services 2>/dev/null | grep -q '^ollama$$'; then \
	  docker compose exec ollama ollama pull llama3; \
	else \
	  echo "No se detectó compose con servicio 'ollama'. Usando contenedor suelto..."; \
	  docker exec -it ollama ollama pull llama3; \
	fi

# ---- Data / RAG ----
.PHONY: ingest
ingest:
	@echo "📦 Ejecutando ingesta de datos..."
	docker-compose exec app python src/ingest_data.py
	@echo "✅ Índice FAISS actualizado"

# ---- Shell ----
.PHONY: shell
shell:
	@echo "🐚 Abriendo shell en contenedor de app..."
	docker-compose exec app bash

# ---- Limpieza ----
.PHONY: clean
clean:
	@echo "🧹 Limpiando artifacts/"
	@rm -rf artifacts/faiss_index/* artifacts/meta.jsonl 2>/dev/null || true
	@echo "✅ Limpieza completada"

.PHONY: clean-all
clean-all: down clean
	@echo "🧹 Limpieza profunda (incluye volúmenes de Ollama)..."
	docker-compose down -v
	@echo "⚠️  Se eliminaron los modelos descargados de Ollama"
	@echo "✅ Limpieza profunda completada"

.PHONY: up ingest logs ps

up:
	$(COMPOSE) up -d $(SERVICE)

ingest: up
	@echo "📦 Ejecutando ingesta de datos..."
	$(COMPOSE) exec $(SERVICE) python src/ingest_data.py

logs:
	$(COMPOSE) logs -f $(SERVICE)

ps:
	$(COMPOSE) ps

# ---- Rebuild ----
.PHONY: rebuild
rebuild: down build up