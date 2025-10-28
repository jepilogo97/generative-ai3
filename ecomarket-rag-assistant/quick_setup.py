#!/usr/bin/env python3
"""
Script de configuración rápida para EcoMarket RAG Assistant
Configura todo el entorno en un solo comando
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Ejecuta un comando y maneja errores."""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - OK")
            return True
        else:
            print(f"❌ {description} - ERROR: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPCIÓN: {e}")
        return False

def install_dependencies():
    """Instala las dependencias de Python."""
    print("📦 Instalando dependencias...")
    
    if run_command("pip install -r requirements.txt", "Instalando paquetes Python"):
        print("✅ Dependencias instaladas")
        return True
    else:
        print("❌ Error instalando dependencias")
        return False

def initialize_database():
    """Inicializa la base de datos."""
    print("🗄️ Inicializando base de datos...")
    
    if run_command("python init_db.py", "Creando base de datos SQLite"):
        print("✅ Base de datos inicializada")
        return True
    else:
        print("❌ Error inicializando base de datos")
        return False

def run_data_ingestion():
    """Ejecuta la ingesta de datos."""
    print("📊 Ejecutando ingesta de datos...")
    
    if run_command("python src/ingest_data.py", "Generando embeddings e índice FAISS"):
        print("✅ Ingesta completada")
        return True
    else:
        print("❌ Error en ingesta de datos")
        return False

def check_ollama():
    """Verifica si Ollama está instalado."""
    print("🤖 Verificando Ollama...")
    
    # Verificar si Ollama está instalado
    result = subprocess.run("ollama --version", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Ollama no está instalado")
        print("💡 Instala Ollama desde: https://ollama.ai/")
        print("   O ejecuta: curl -fsSL https://ollama.ai/install.sh | bash")
        return False
    
    print("✅ Ollama instalado")
    
    # Verificar si el modelo llama3 está disponible
    result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
    if "llama3" not in result.stdout:
        print("⚠️  Modelo llama3 no encontrado")
        print("🔄 Descargando modelo llama3...")
        print("⚠️  Esto puede tomar varios minutos...")
        
        if run_command("ollama pull llama3", "Descargando modelo llama3"):
            print("✅ Modelo llama3 descargado")
            return True
        else:
            print("❌ Error descargando modelo")
            return False
    else:
        print("✅ Modelo llama3 disponible")
        return True

def show_next_steps():
    """Muestra los próximos pasos."""
    print("""
🎉 ¡Configuración completada!
============================

Próximos pasos:

1. 🚀 Ejecutar la aplicación:
   python start.py

2. 🧪 Probar el sistema:
   python test_system.py

3. 🌐 Acceder a la aplicación:
   http://localhost:8501

4. 💬 Funcionalidades disponibles:
   ✅ Consultas sobre pedidos
   ✅ Información de devoluciones
   ✅ Historial de conversaciones
   ✅ Gestión de chats

5. 🛠️ Comandos útiles:
   - python start.py --local    # Ejecutar sin Docker
   - python start.py --rebuild  # Reconstruir imagen Docker
   - python start.py --help    # Ver ayuda completa

¡Disfruta tu sistema RAG! 🎊
""")

def main():
    """Función principal."""
    print("🚀 Configuración Rápida EcoMarket RAG Assistant")
    print("===============================================")
    print("")
    
    steps = [
        ("Instalando dependencias", install_dependencies),
        ("Inicializando base de datos", initialize_database),
        ("Ejecutando ingesta de datos", run_data_ingestion),
        ("Verificando Ollama", check_ollama)
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"\n❌ Error en: {step_name}")
            print("💡 Revisa los errores arriba y vuelve a intentar")
            return 1
    
    show_next_steps()
    return 0

if __name__ == "__main__":
    sys.exit(main())
