#!/usr/bin/env python3
"""
Script para inicializar la base de datos SQLite del sistema EcoMarket RAG
Ejecutar una sola vez al configurar el proyecto
"""

import sqlite3
import os
from pathlib import Path

def init_database():
    """Inicializa la base de datos SQLite con las tablas necesarias"""
    
    # Asegurar que el directorio existe
    os.makedirs("data", exist_ok=True)
    
    # Conectar a la base de datos
    db_path = "data/ecomarket_chat.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🗄️ Inicializando base de datos EcoMarket...")
    
    # Crear tabla 'chat'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Crear tabla 'sources' (para fuentes de información)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source_text TEXT,
            type TEXT DEFAULT "document",
            chat_id INTEGER,
            FOREIGN KEY (chat_id) REFERENCES chat(id)
        )
    """)
    
    # Crear tabla 'messages' (para mensajes del chat)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES chat(id)
        )
    """)
    
    # Crear índices para mejorar el rendimiento
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_chat_id ON sources(chat_id)")
    
    # Commit y cerrar
    conn.commit()
    conn.close()
    
    print(f"✅ Base de datos inicializada: {db_path}")
    print("📊 Tablas creadas: chat, sources, messages")
    print("🔍 Índices creados para optimizar consultas")

if __name__ == "__main__":
    init_database()
