#!/usr/bin/env bash
set -e

echo "🗄️ Bootstrap: DB e índice"
# Asegura rutas
mkdir -p data artifacts/faiss_index

# Inicializa DB si no existe
if [ ! -f "data/ecomarket_chat.db" ]; then
  echo "➡️  Creando DB..."
  python init_db.py || { echo "❌ Falló init_db.py"; exit 1; }
else
  echo "✅ DB ya existe"
fi

# Genera índice FAISS si no existe
if [ ! -f "artifacts/faiss_index/index.faiss" ]; then
  echo "➡️  Ingesta de datos..."
  python src/ingest_data.py || { echo "❌ Falló ingest_data.py"; exit 1; }
else
  echo "✅ Índice FAISS ya existe"
fi

echo "🚀 Lanzando Streamlit"
exec streamlit run src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0