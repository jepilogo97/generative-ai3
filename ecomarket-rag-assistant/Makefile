# =========================
# EcoMarket RAG – Makefile
# =========================

# ---- Config ----
APP_NAME       ?= pedidos-app
SERVICE        ?= pedidos-app
OLLAMA_NAME    ?= ollama
STREAMLIT_PORT ?= 8501
OLLAMA_PORT    ?= 11434
MODEL_NAME     ?= llama3
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
	@echo "  make setup-ollama - Configura Ollama completamente (espera + descarga + verifica)"
	@echo "  make check-ollama - Lista modelos instalados"
	@echo "  make pull-model   - Descarga el modelo LLM (usa MODEL_NAME)"
	@echo "  make verify-model - Verifica que el modelo exista"
	@echo "  make wait-ollama  - Espera a que Ollama esté listo"
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
	@echo "  make test-agent   - Ejecuta pruebas del agente"
	@echo ""
	@echo "💡 Ejemplos:"
	@echo "  make first-run                      - Instalación completa con modelo por defecto"
	@echo "  make first-run MODEL_NAME=llama3.1  - Instalación con modelo específico"
	@echo "  make pull-model MODEL_NAME=mistral  - Descargar modelo alternativo"
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
	@echo "💡 Usa 'make check-ollama' para verificar modelos"

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

# ---- Ollama (versión corregida y robusta) ----
.PHONY: wait-ollama
wait-ollama:
	@echo "⏳ Esperando a que Ollama esté listo..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12; do \
		if docker exec $(OLLAMA_NAME) curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then \
			echo "✅ Ollama está listo (intento $$i/12)"; \
			exit 0; \
		fi; \
		echo "   ⏳ Intento $$i/12... esperando 5 segundos"; \
		sleep 5; \
	done; \
	echo "❌ ERROR: Ollama no respondió después de 60 segundos"; \
	echo "💡 Verifica logs con: make logs-ollama"; \
	exit 1

.PHONY: pull-model
pull-model:
	@echo "📥 Descargando modelo $(MODEL_NAME)..."
	@echo "⏳ Esto puede tardar varios minutos dependiendo del tamaño y tu conexión..."
	@echo ""
	docker exec $(OLLAMA_NAME) ollama pull $(MODEL_NAME) || \
		(echo ""; \
		 echo "❌ ERROR: No se pudo descargar el modelo $(MODEL_NAME)"; \
		 echo ""; \
		 echo "💡 Posibles soluciones:"; \
		 echo "   1. Verifica que el nombre del modelo sea correcto"; \
		 echo "   2. Modelos disponibles comunes:"; \
		 echo "      - llama3 (recomendado)"; \
		 echo "      - llama3.1"; \
		 echo "      - llama3.2"; \
		 echo "      - llama2"; \
		 echo "      - mistral"; \
		 echo "      - phi3"; \
		 echo "   3. Prueba con otro modelo:"; \
		 echo "      make pull-model MODEL_NAME=llama3"; \
		 echo "   4. Busca más modelos en: https://ollama.ai/library"; \
		 echo ""; \
		 exit 1)
	@echo ""
	@echo "✅ Modelo $(MODEL_NAME) descargado exitosamente"

.PHONY: verify-model
verify-model:
	@echo "🔍 Verificando modelo $(MODEL_NAME)..."
	@if docker exec $(OLLAMA_NAME) ollama list 2>/dev/null | grep -q "$(MODEL_NAME)"; then \
		echo "✅ Modelo $(MODEL_NAME) confirmado y listo para usar"; \
	else \
		echo "❌ ERROR: Modelo $(MODEL_NAME) no encontrado después de la descarga"; \
		echo "💡 Verifica modelos instalados con: make check-ollama"; \
		exit 1; \
	fi

.PHONY: setup-ollama
setup-ollama: wait-ollama pull-model verify-model
	@echo ""
	@echo "✅ Ollama configurado completamente"
	@echo ""
	@$(MAKE) check-ollama

.PHONY: check-ollama
check-ollama:
	@echo "🔍 Modelos instalados en Ollama:"
	@docker exec $(OLLAMA_NAME) ollama list 2>/dev/null || \
		(echo "❌ Ollama no está corriendo"; \
		 echo "💡 Ejecuta: make up"; \
		 exit 1)

.PHONY: ollama-shell
ollama-shell:
	@echo "🐚 Abriendo shell en contenedor Ollama..."
	@docker exec -it $(OLLAMA_NAME) /bin/bash

# ---- Data / RAG ----
.PHONY: ingest
ingest:
	@echo "📦 Ejecutando ingesta de datos (generando índice FAISS)..."
	@echo "⏳ Esto puede tardar 1-2 minutos..."
	$(COMPOSE) exec $(SERVICE) python src/ingest_data.py
	@echo "✅ Índice FAISS actualizado correctamente"

# ---- Shell ----
.PHONY: shell
shell:
	@echo "🐚 Abriendo shell en contenedor de la app..."
	$(COMPOSE) exec $(SERVICE) bash

# ---- Limpieza ----
.PHONY: clean
clean:
	@echo "🧹 Limpiando artifacts locales..."
	@rm -rf artifacts/faiss_index/* artifacts/meta.jsonl 2>/dev/null || true
	@echo "✅ Limpieza completada"

.PHONY: clean-all
clean-all: down clean
	@echo "🧹 Limpieza profunda (incluye volúmenes de Docker)..."
	$(COMPOSE) down -v
	@echo "⚠️  Se eliminaron:"
	@echo "   - Contenedores"
	@echo "   - Volúmenes (modelos de Ollama descargados)"
	@echo "   - Artifacts locales"
	@echo ""
	@echo "✅ Limpieza profunda completada"
	@echo "💡 Para volver a empezar: make first-run"

# ---- Primera ejecución completa ----
.PHONY: first-run
first-run: check build up setup-ollama ingest
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "🎉 ¡Configuración inicial completada exitosamente!"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "📊 Recursos disponibles:"
	@echo "   • Streamlit:  http://localhost:$(STREAMLIT_PORT)"
	@echo "   • Ollama:     http://localhost:$(OLLAMA_PORT)"
	@echo "   • Modelo:     $(MODEL_NAME)"
	@echo ""
	@echo "🚀 Próximos pasos:"
	@echo "   1. Abre tu navegador en: http://localhost:$(STREAMLIT_PORT)"
	@echo "   2. Prueba el agente con: make test-agent"
	@echo "   3. Ve logs en tiempo real: make logs"
	@echo ""
	@echo "💡 Comandos útiles:"
	@echo "   - make status        Ver estado de contenedores"
	@echo "   - make check-ollama  Verificar modelos instalados"
	@echo "   - make restart       Reiniciar servicios"
	@echo "   - make help          Ver todos los comandos"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"

# ---- Pruebas del Agente ----
.PHONY: test-agent
test-agent:
	@echo "🧪 Ejecutando suite de pruebas del agente..."
	@echo "⏳ Esto puede tardar 1-2 minutos..."
	@echo ""
	$(COMPOSE) exec $(SERVICE) python test_agent.py

.PHONY: test-agent-local
test-agent-local:
	@echo "🧪 Ejecutando pruebas del agente localmente..."
	$(PY) test_agent.py

# ---- Comandos de desarrollo ----
.PHONY: dev-restart
dev-restart:
	@echo "🔄 Reinicio rápido para desarrollo..."
	$(COMPOSE) restart $(SERVICE)
	@echo "✅ Aplicación reiniciada"

.PHONY: dev-logs
dev-logs:
	@echo "📋 Siguiendo logs de la aplicación..."
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

# ---- Diagnóstico ----
.PHONY: diagnose
diagnose:
	@echo "🔍 Diagnóstico del sistema:"
	@echo ""
	@echo "=== Docker ==="
	@docker --version || echo "❌ Docker no disponible"
	@echo ""
	@echo "=== Docker Compose ==="
	@$(COMPOSE) version || echo "❌ Docker Compose no disponible"
	@echo ""
	@echo "=== Contenedores ==="
	@docker ps --filter name=$(OLLAMA_NAME) --filter name=$(SERVICE)
	@echo ""
	@echo "=== Modelos Ollama ==="
	@docker exec $(OLLAMA_NAME) ollama list 2>/dev/null || echo "❌ Ollama no está corriendo"
	@echo ""
	@echo "=== Índice FAISS ==="
	@if [ -f "artifacts/faiss_index/index.faiss" ]; then \
		echo "✅ Índice FAISS existe"; \
	else \
		echo "❌ Índice FAISS no encontrado"; \
	fi
	@echo ""
	@echo "=== Base de datos ==="
	@if [ -f "data/ecomarket_chat.db" ]; then \
		echo "✅ Base de datos existe"; \
	else \
		echo "❌ Base de datos no encontrada"; \
	fi