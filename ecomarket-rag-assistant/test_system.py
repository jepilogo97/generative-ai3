#!/usr/bin/env python3
"""
Script de pruebas para verificar que el sistema EcoMarket RAG funciona correctamente
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

def test_database():
    """Prueba la base de datos SQLite."""
    print("🗄️ Probando base de datos...")
    
    db_path = "data/ecomarket_chat.db"
    if not os.path.exists(db_path):
        print("❌ Base de datos no encontrada")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['chat', 'messages', 'sources']
        for table in expected_tables:
            if table not in tables:
                print(f"❌ Tabla '{table}' no encontrada")
                return False
        
        print("✅ Base de datos OK")
        return True
        
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_faiss_index():
    """Prueba el índice FAISS."""
    print("🔍 Probando índice FAISS...")
    
    index_path = "artifacts/faiss_index"
    if not os.path.exists(index_path):
        print("❌ Índice FAISS no encontrado")
        return False
    
    required_files = ['index.faiss', 'index.pkl']
    for file in required_files:
        if not os.path.exists(f"{index_path}/{file}"):
            print(f"❌ Archivo {file} no encontrado")
            return False
    
    print("✅ Índice FAISS OK")
    return True

def test_data_files():
    """Prueba los archivos de datos."""
    print("📊 Probando archivos de datos...")
    
    # Verificar pedidos.json
    pedidos_path = "data/pedidos.json"
    if not os.path.exists(pedidos_path):
        print("❌ Archivo pedidos.json no encontrado")
        return False
    
    try:
        with open(pedidos_path, 'r', encoding='utf-8') as f:
            pedidos = json.load(f)
        
        if not isinstance(pedidos, list) or len(pedidos) == 0:
            print("❌ Archivo pedidos.json vacío o inválido")
            return False
        
        print(f"✅ {len(pedidos)} pedidos encontrados")
        return True
        
    except Exception as e:
        print(f"❌ Error leyendo pedidos.json: {e}")
        return False

def test_imports():
    """Prueba las importaciones de Python."""
    print("🐍 Probando importaciones...")
    
    required_modules = [
        'streamlit',
        'langchain',
        'langchain_community',
        'faiss',
        'sentence_transformers',
        'ollama',
        'pandas'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Módulos faltantes: {', '.join(missing_modules)}")
        print("💡 Instala con: pip install -r requirements.txt")
        return False
    
    print("✅ Todas las importaciones OK")
    return True

def test_ollama_connection():
    """Prueba la conexión con Ollama."""
    print("🤖 Probando conexión con Ollama...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            llama_models = [m for m in models if 'llama' in m.get('name', '').lower()]
            if llama_models:
                print(f"✅ Ollama conectado, modelos Llama encontrados: {len(llama_models)}")
                return True
            else:
                print("⚠️  Ollama conectado pero no hay modelos Llama")
                print("💡 Descarga con: ollama pull llama3")
                return False
        else:
            print("❌ Ollama no responde correctamente")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama no está ejecutándose")
        print("💡 Inicia Ollama con: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error conectando con Ollama: {e}")
        return False

def run_rag_test():
    """Ejecuta una prueba básica del sistema RAG."""
    print("🧪 Ejecutando prueba RAG...")
    
    try:
        # Importar módulos necesarios
        from langchain_community.embeddings import SentenceTransformerEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_community.chat_models import ChatOllama
        
        # Cargar embeddings
        emb = SentenceTransformerEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        
        # Cargar índice FAISS
        db = FAISS.load_local("artifacts/faiss_index", emb, allow_dangerous_deserialization=True)
        
        # Probar búsqueda
        docs = db.similarity_search("pedido 20001", k=2)
        if len(docs) > 0:
            print("✅ Búsqueda semántica OK")
            return True
        else:
            print("❌ No se encontraron documentos relevantes")
            return False
            
    except Exception as e:
        print(f"❌ Error en prueba RAG: {e}")
        return False

def main():
    """Función principal de pruebas."""
    print("🧪 Sistema de Pruebas EcoMarket RAG")
    print("===================================")
    print("")
    
    tests = [
        ("Archivos de datos", test_data_files),
        ("Base de datos", test_database),
        ("Índice FAISS", test_faiss_index),
        ("Importaciones Python", test_imports),
        ("Conexión Ollama", test_ollama_connection),
        ("Sistema RAG", run_rag_test)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"❌ Prueba '{test_name}' falló")
    
    print(f"\n📊 Resultados: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
        print("🚀 Ejecuta: python start.py")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
