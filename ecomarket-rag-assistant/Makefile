# =========================
# EcoMarket RAG – Makefile
# =========================

# ---- Config ----
APP_NAME       ?= pedidos-app
SERVICE        ?= pedidos-app
OLLAMA_NAME    ?= ollama
STREAMLIT_PORT ?= 8501
OLLAMA_PORT    ?= 11434
MODEL_NAME     ?= llama3.2:3b
PY             ?= python
COMPOSE        := docker compose

# ---- Ayuda ----
.PHONY: help
help:
	@echo ""
	@echo "Comandos disponibles:"
	@echo ""
	@echo "🚀 Inicio rápido:"
	@echo "  make first-run    - Primera instalación completa (build + up + modelo + ingest)"
	@echo ""
	@echo "📦 Operaciones básicas:"
	@echo "  make build        - Construye las imágenes Docker"
	@echo "  make up           - Levanta todos los contenedores en segundo plano"
	@echo "  make down         - Detiene y elimina los contenedores"
	@echo "  make restart      - Reinicia los contenedores"
	@echo "  make status       - Muestra estado de los contenedores"
	@echo ""
	@echo "📊 Logs:"
	@echo "  make logs         - Logs de todos los servicios"
	@echo "  make logs-app     - Logs solo de la app"
	@echo "  make logs-ollama  - Logs solo de Ollama"
	@echo ""
	@echo "🤖 Ollama:"
	@echo "  make setup-ollama - Descarga el modelo LLM en Ollama"
	@echo "  make check-ollama - Lista modelos instalados"
	@echo "  make ollama-shell - Shell dentro del contenedor Ollama"
	@echo ""
	@echo "📊 Data & RAG:"
	@echo "  make ingest       - Ejecuta ingesta de datos (crea índice FAISS)"
	@echo "  make clean        - Limpia artifacts locales"
	@echo "  make clean-all    - Limpieza profunda (incluye volúmenes)"
	@echo ""
	@echo "🔧 Utilidades:"
	@echo "  make check        - Verifica Docker/Compose"
	@echo "  make shell        - Shell dentro del contenedor de la app"
	@echo ""

# ---- Checks ----
.PHONY: check
check:
	@docker --version >/dev/null 2>&1 || (echo "❌ Docker no disponible"; exit 1)
	@$(COMPOSE) version >/dev/null 2>&1 || (echo "❌ Docker Compose no disponible"; exit 1)
	@$(PY) --version
	@echo "✅ Entorno OK"

# ---- Build/Run ----
.PHONY: build
build:
	@echo "🔨 Construyendo imágenes..."
	$(COMPOSE) build --no-cache
	@echo "✅ Build completado"

.PHONY: up
up:
	@echo "🚀 Levantando servicios..."
	$(COMPOSE) up -d
	@echo ""
	@echo "✅ Servicios iniciados:"
	@echo "   • Streamlit:  http://localhost:$(STREAMLIT_PORT)"
	@echo "   • Ollama:     http://localhost:$(OLLAMA_PORT)"
	@echo ""
	@echo "💡 Usa 'make logs' para ver logs en vivo"
	@echo "💡 Usa 'make check-ollama' para verificar el modelo"

.PHONY: down
down:
	@echo "🛑 Deteniendo servicios..."
	$(COMPOSE) down
	@echo "✅ Servicios detenidos"

.PHONY: restart
restart: down up

.PHONY: status
status:
	@echo "📊 Estado de los contenedores:"
	@$(COMPOSE) ps

# ---- Logs ----
.PHONY: logs
logs:
	$(COMPOSE) logs -f

.PHONY: logs-app
logs-app:
	$(COMPOSE) logs -f $(SERVICE)

.PHONY: logs-ollama
logs-ollama:
	$(COMPOSE) logs -f $(OLLAMA_NAME)

# ---- Ollama ----
.PHONY: setup-ollama
setup-ollama:
	@echo "📦 Descargando modelo $(MODEL_NAME) en Ollama..."
	-@docker exec $(OLLAMA_NAME) ollama pull $(MODEL_NAME)
	@echo "✅ Modelo $(MODEL_NAME) preparado"
	@$(MAKE) check-ollama

.PHONY: check-ollama
check-ollama:
	@echo "🔍 Modelos instalados en Ollama:"
	-@docker exec $(OLLAMA_NAME) ollama list || echo "❌ Ollama no está corriendo"

.PHONY: ollama-shell
ollama-shell:
	@echo "🐚 Shell en contenedor Ollama..."
	@docker exec -it $(OLLAMA_NAME) /bin/bash

# ---- Espera Ollama (versión portable)
.PHONY: wait-ollama
wait-ollama:
	@echo "⏳ Verificando si Ollama responde..."
	-@docker exec $(OLLAMA_NAME) curl -s http://localhost:11434/api/tags > NUL 2>&1 || echo "⚠️ Ollama puede no estar listo todavía"
	@echo "✅ Continuando..."

# ---- Data / RAG ----
.PHONY: ingest
ingest:
	@echo "📦 Ejecutando ingesta de datos (FAISS)..."
	$(COMPOSE) exec $(SERVICE) python src/ingest_data.py
	@echo "✅ Índice FAISS actualizado"

# ---- Shell ----
.PHONY: shell
shell:
	@echo "🐚 Shell en contenedor de la app..."
	$(COMPOSE) exec $(SERVICE) bash

# ---- Limpieza ----
.PHONY: clean
clean:
	@echo "🧹 Limpiando artifacts/..."
	@rm -rf artifacts/faiss_index/* artifacts/meta.jsonl 2>/dev/null || true
	@echo "✅ Limpieza completada"

.PHONY: clean-all
clean-all: down clean
	@echo "🧹 Limpieza profunda (incluye volúmenes de Ollama)..."
	$(COMPOSE) down -v
	@echo "⚠️  Se eliminaron modelos descargados"
	@echo "✅ Limpieza profunda completada"

# ---- Primera ejecución completa ----
.PHONY: first-run
first-run: check build up wait-ollama setup-ollama ingest
	@echo ""
	@echo "🎉 ¡Configuración inicial completa!"
	@echo "   • Streamlit:  http://localhost:$(STREAMLIT_PORT)"
	@echo "   • Ollama:     http://localhost:$(OLLAMA_PORT)"
	@echo "🚀 Tu aplicación está lista"

# ---- Pruebas del Agente ----
.PHONY: test-agent
test-agent:
	@echo "🧪 Ejecutando pruebas del agente en contenedor..."
	$(COMPOSE) exec $(SERVICE) python test_agent.py

.PHONY: test-agent-local
test-agent-local:
	@echo "🧪 Ejecutando pruebas del agente localmente..."
	$(PY) test_agent.py
