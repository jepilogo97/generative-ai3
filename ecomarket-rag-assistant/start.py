#!/usr/bin/env python3
"""
Script de inicio universal para EcoMarket RAG Assistant
Funciona en Windows, Linux, Mac y WSL
Incluye inicialización de BD, ingesta de datos y gestión completa
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(cmd, description="", capture_output=True, show_output=False):
    """Ejecuta un comando y maneja errores."""
    print(f"🔄 {description}")
    try:
        common = dict(shell=True, text=True, encoding="utf-8", errors="replace")

        if show_output:
            # Muestra salida en vivo (útil para builds largos)
            result = subprocess.run(cmd, **common)
            return result.returncode == 0

        if capture_output:
            result = subprocess.run(cmd, capture_output=True, **common)
            if result.returncode == 0:
                print(f"✅ {description} - OK")
                return True
            else:
                # Si stderr viene vacío, intenta stdout (algunos comandos imprimen todo en stdout)
                err = (result.stderr or "").strip()
                if not err:
                    err = (result.stdout or "").strip()
                print(f"❌ {description} - ERROR: {err}")
                return False

        # Modo sin captura pero sin volcar en consola (raro usarlo)
        result = subprocess.run(cmd, **common)
        return result.returncode == 0

    except Exception as e:
        print(f"❌ {description} - EXCEPCIÓN: {e}")
        return False


def check_docker():
    """Verifica que Docker esté instalado y ejecutándose."""
    print("🐳 Verificando Docker...")
    
    # Verificar que Docker esté instalado
    if not run_command("docker --version", "Verificando instalación de Docker"):
        print("❌ Docker no está instalado")
        print("💡 Descarga Docker Desktop desde: https://www.docker.com/")
        return False
    
    # Verificar que Docker esté ejecutándose
    if not run_command("docker info", "Verificando que Docker esté ejecutándose"):
        print("❌ Docker no está ejecutándose")
        print("💡 Inicia Docker Desktop")
        return False
    
    print("✅ Docker verificado")
    return True

def check_python_dependencies():
    """Verifica que las dependencias de Python estén instaladas."""
    print("🐍 Verificando dependencias de Python...")
    
    required_packages = [
        "streamlit", "langchain", "faiss-cpu", "sentence-transformers", 
        "ollama", "pandas", "requests"
    ]
    
    missing_packages = []
    for package in required_packages:
        if not run_command(f"python -c \"import {package.replace('-', '_')}\"", 
                         f"Verificando {package}", show_output=False):
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Faltan dependencias: {', '.join(missing_packages)}")
        print("💡 Instala con: pip install -r requirements.txt")
        return False
    
    print("✅ Dependencias verificadas")
    return True

def initialize_database():
    """Inicializa la base de datos SQLite."""
    print("🗄️ Inicializando base de datos...")
    
    if not os.path.exists("data/ecomarket_chat.db"):
        if run_command("python init_db.py", "Creando base de datos SQLite"):
            print("✅ Base de datos inicializada")
            return True
        else:
            print("❌ Error inicializando base de datos")
            return False
    else:
        print("✅ Base de datos ya existe")
        return True

def run_data_ingestion():
    """Ejecuta la ingesta de datos para crear el índice FAISS."""
    print("📊 Ejecutando ingesta de datos...")
    
    # Verificar si el índice ya existe
    if os.path.exists("artifacts/faiss_index/index.faiss"):
        print("✅ Índice FAISS ya existe")
        return True
    
    if run_command("python src/ingest_data.py", "Generando embeddings e índice FAISS"):
        print("✅ Ingesta de datos completada")
        return True
    else:
        print("❌ Error en la ingesta de datos")
        return False

def build_image(force_rebuild=False):
    """Construye la imagen Docker si no existe."""
    print("🔍 Verificando imagen Docker...")

    # Verificar si la imagen existe
    result = subprocess.run(
        "docker image inspect ecomarket-rag",
        shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )

    if result.returncode == 0 and not force_rebuild:
        print("✅ Imagen ya existe")
        return True

    if force_rebuild:
        print("🔨 Reconstruyendo imagen Docker (sin caché)...")
        cmd = "docker build --no-cache --progress=plain -t ecomarket-rag ."
    else:
        print("🔨 Construyendo imagen Docker...")
        cmd = "docker build --progress=plain -t ecomarket-rag ."

    if run_command(cmd, "Construyendo imagen", show_output=True):
        print("✅ Imagen construida exitosamente")
        return True
    else:
        print("❌ Error construyendo imagen")
        return False


def run_container():
    """Ejecuta el contenedor Docker."""
    print("🚀 Iniciando contenedor EcoMarket RAG...")
    print("📱 La aplicación estará disponible en: http://localhost:8501")
    print("🤖 Ollama estará disponible en: http://localhost:11434")
    print("⏳ Esperando a que Ollama descargue el modelo (puede tomar varios minutos)...")
    print("")
    
    # Verificar si hay contenedores ejecutándose
    result = subprocess.run("docker ps --filter name=ecomarket-rag", 
                           shell=True, capture_output=True, text=True)
    
    if "ecomarket-rag" in result.stdout:
        print("⚠️  Ya hay un contenedor ejecutándose")
        print("💡 Detén el contenedor anterior con: docker stop ecomarket-rag")
        return False
    
    # Ejecutar contenedor
    try:
        subprocess.run("docker run --name ecomarket-rag -p 8501:8501 -p 11434:11434 ecomarket-rag", 
                      shell=True, check=True)
    except subprocess.CalledProcessError as e:
        error_msg = str(e)
        if "port is already allocated" in error_msg:
            print("❌ Puerto 8501 ya está en uso")
            print("💡 Detén otros contenedores o cambia el puerto:")
            print("   docker run --name ecomarket-rag -p 8502:8501 -p 11435:11434 ecomarket-rag")
        elif "numpy.core.multiarray" in error_msg:
            print("❌ Error con NumPy en el contenedor")
            print("💡 Reconstruye la imagen con:")
            print("   docker build --no-cache -t ecomarket-rag .")
        else:
            print(f"❌ Error ejecutando contenedor: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Contenedor detenido por el usuario")
        return True
    
    return True

def run_tests(use_docker: bool = False) -> bool:
    """Ejecuta test_system.py en local o dentro de Docker.

    Cuando use_docker=True, corre las pruebas en un contenedor efímero
    basado en la imagen construida para validar el entorno de ejecución.
    """
    if use_docker:
        return run_command(
            "docker run --rm ecomarket-rag python test_system.py",
            "Ejecutando pruebas dentro de Docker"
        )
    return run_command(
        "python test_system.py",
        "Ejecutando pruebas locales"
    )
def run_local():
    """Ejecuta la aplicación localmente sin Docker."""
    print("🏠 Ejecutando aplicación localmente...")
    print("📱 La aplicación estará disponible en: http://localhost:8501")
    print("⚠️  Asegúrate de tener Ollama ejecutándose en http://localhost:11434")
    print("")
    
    try:
        subprocess.run("streamlit run src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0", 
                      shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando aplicación local: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Aplicación detenida por el usuario")
        return True
    
    return True

def show_help():
    """Muestra la ayuda del script."""
    print("""
🚀 EcoMarket RAG Assistant - Script de Inicio
==============================================

Uso: python start.py [opciones]

Opciones:
  (sin argumentos)  - Ejecuta con Docker (recomendado)
  --local          - Ejecuta localmente (requiere Ollama instalado)
  --rebuild        - Reconstruye la imagen Docker sin caché
  --test           - Ejecuta pruebas (test_system.py) antes de lanzar
  --help           - Muestra esta ayuda

Ejemplos:
  python start.py              # Ejecutar con Docker
  python start.py --local      # Ejecutar localmente
  python start.py --rebuild    # Reconstruir imagen Docker

Requisitos:
  - Docker Desktop (para modo Docker)
  - Python 3.11+ (para modo local)
  - Ollama instalado (para modo local)

La aplicación incluye:
  ✅ Sistema RAG con FAISS y Llama 3
  ✅ Persistencia de conversaciones con SQLite
  ✅ Interfaz web con Streamlit
  ✅ Gestión de historial de chats
""")

def main():
    """Función principal."""
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        show_help()
        return 0
    
    print("🚀 Iniciando EcoMarket RAG Assistant")
    print("=====================================")
    print("")
    
    # Verificar argumentos
    use_local = "--local" in args
    force_rebuild = "--rebuild" in args
    run_pre_tests = "--test" in args
    
    if use_local:
        print("🏠 Modo: Ejecución Local")
        print("⚠️  Requiere Ollama instalado y ejecutándose")
        print("")
        
        # Verificar dependencias
        if not check_python_dependencies():
            return 1
        
        # Inicializar base de datos
        if not initialize_database():
            return 1
        
        # Ejecutar ingesta
        if not run_data_ingestion():
            return 1
        
        # Ejecutar pruebas locales si se solicita
        if run_pre_tests:
            if not run_tests(use_docker=False):
                return 1

        # Ejecutar aplicación local
        return 0 if run_local() else 1
    
    else:
        print("🐳 Modo: Docker")
        print("")
        
        # Verificar Docker
        if not check_docker():
            return 1
        
        # Construir imagen
        if not build_image(force_rebuild):
            return 1
        
        # Ejecutar pruebas dentro de Docker si se solicita
        if run_pre_tests:
            if not run_tests(use_docker=True):
                return 1

        # Ejecutar contenedor
        return 0 if run_container() else 1

if __name__ == "__main__":
    sys.exit(main())