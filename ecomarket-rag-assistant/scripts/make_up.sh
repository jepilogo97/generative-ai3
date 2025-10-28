#!/bin/bash
# Script para construir y lanzar el contenedor Docker

set -e

echo "🚀 Construyendo y lanzando contenedor EcoMarket RAG..."

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker no está instalado o no está en el PATH"
    exit 1
fi

# Construir la imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t pedidos-app .

# Detener contenedor existente si está corriendo
echo "🛑 Deteniendo contenedor existente (si existe)..."
docker rm -f pedidos-app 2>/dev/null || true

# Lanzar el contenedor
echo "🚀 Lanzando contenedor..."
docker run -d \
    --name pedidos-app \
    -p 8501:8501 \
    -p 11434:11434 \
    pedidos-app

echo "✅ Contenedor lanzado exitosamente"
echo "🌐 Streamlit disponible en: http://localhost:8501"
echo "🤖 Ollama disponible en: http://localhost:11434"
echo ""
echo "📋 Para ver los logs: docker logs -f pedidos-app"
echo "🛑 Para detener: docker stop pedidos-app"
