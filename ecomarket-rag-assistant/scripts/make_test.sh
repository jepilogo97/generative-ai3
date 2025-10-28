#!/bin/bash
# Script para ejecutar pruebas de consultas RAG

set -e

echo "🧪 Ejecutando pruebas de consultas RAG..."

# Verificar que el contenedor está corriendo
if ! docker ps --format '{{.Names}}' | grep -q '^pedidos-app$'; then
    echo "❌ Error: El contenedor 'pedidos-app' no está corriendo"
    echo "   Ejecuta primero: make up"
    exit 1
fi

# Verificar que el índice FAISS existe
if [ ! -d "artifacts/faiss_index" ] || [ ! -f "artifacts/faiss_index/index.faiss" ]; then
    echo "❌ Error: No se encuentra el índice FAISS"
    echo "   Ejecuta primero: make ingest"
    exit 1
fi

echo "🧪 Test 1: Consulta de seguimiento de pedido"
echo "Pregunta: ¿Dónde está mi pedido 20001?"
docker exec -it pedidos-app sh -c "printf '¿Dónde está mi pedido 20001?\n' | python rag_ejemplo.py"

echo ""
echo "🧪 Test 2: Consulta sobre devoluciones"
echo "Pregunta: ¿Puedo devolver el Yogur griego del pedido 20003?"
docker exec -it pedidos-app sh -c "printf '¿Puedo devolver el Yogur griego del pedido 20003?\n' | python rag_ejemplo.py"

echo ""
echo "🧪 Test 3: Consulta sobre políticas de devolución"
echo "Pregunta: ¿Qué productos no se pueden devolver?"
docker exec -it pedidos-app sh -c "printf '¿Qué productos no se pueden devolver?\n' | python rag_ejemplo.py"

echo ""
echo "✅ Pruebas completadas"
