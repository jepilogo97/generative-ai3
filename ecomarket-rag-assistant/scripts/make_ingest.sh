#!/bin/bash
# Script para ejecutar la ingesta de datos y generar el índice FAISS

set -e

echo "🧮 Ejecutando ingesta de datos..."

# Verificar que estamos en el directorio correcto
if [ ! -f "src/ingest_data.py" ]; then
    echo "❌ Error: No se encuentra src/ingest_data.py"
    echo "   Asegúrate de ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

# Crear directorio de artifacts si no existe
mkdir -p artifacts/faiss_index

# Ejecutar la ingesta
echo "📦 Procesando datos y generando embeddings..."
python src/ingest_data.py

echo "✅ Ingesta completada exitosamente"
echo "📁 Índice FAISS guardado en: artifacts/faiss_index/"
echo "📄 Metadatos guardados en: artifacts/meta.jsonl"
