"""
Módulo de gestión de chat para EcoMarket RAG Assistant
Proporciona funcionalidades para manejar conversaciones persistentes
"""

import streamlit as st
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

class ChatManager:
    def __init__(self):
        self.current_chat_id = None
        
    def get_or_create_chat(self, title="Nueva consulta EcoMarket"):
        """Obtiene el chat actual o crea uno nuevo"""
        if 'current_chat_id' not in st.session_state:
            # Crear nuevo chat
            chat_id = db.create_chat(title)
            st.session_state.current_chat_id = chat_id
            st.session_state.chat_title = title
        return st.session_state.current_chat_id
    
    def save_message(self, sender, content):
        """Guarda un mensaje en la base de datos"""
        chat_id = self.get_or_create_chat()
        db.create_message(chat_id, sender, content)
    
    def get_chat_history(self):
        """Obtiene el historial de mensajes del chat actual"""
        if 'current_chat_id' in st.session_state:
            return db.get_messages(st.session_state.current_chat_id)
        return []
    
    def get_all_chats(self):
        """Obtiene todos los chats disponibles"""
        return db.list_chats()
    
    def switch_chat(self, chat_id):
        """Cambia al chat especificado"""
        st.session_state.current_chat_id = chat_id
        chat_info = db.read_chat(chat_id)
        if chat_info:
            st.session_state.chat_title = chat_info[1]  # title
    
    def create_new_chat(self, title=None):
        """Crea un nuevo chat"""
        if not title:
            title = f"Consulta {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        chat_id = db.create_chat(title)
        st.session_state.current_chat_id = chat_id
        st.session_state.chat_title = title
        return chat_id
    
    def delete_chat(self, chat_id):
        """Elimina un chat"""
        db.delete_chat(chat_id)
        if st.session_state.get('current_chat_id') == chat_id:
            # Si eliminamos el chat actual, crear uno nuevo
            self.create_new_chat()
    
    def update_chat_title(self, chat_id, new_title):
        """Actualiza el título de un chat"""
        db.update_chat(chat_id, new_title)
        if st.session_state.get('current_chat_id') == chat_id:
            st.session_state.chat_title = new_title

def render_chat_sidebar():
    """Renderiza la barra lateral con gestión de chats"""
    with st.sidebar:
        st.header("💬 Gestión de Conversaciones")
        
        # Crear nuevo chat
        if st.button("➕ Nueva Consulta", use_container_width=True):
            chat_manager = ChatManager()
            chat_manager.create_new_chat()
            st.rerun()
        
        st.divider()
        
        # Lista de chats existentes
        st.subheader("📋 Conversaciones Anteriores")
        chats = db.list_chats()
        
        if not chats:
            st.info("No hay conversaciones anteriores")
        else:
            for chat in chats:
                chat_id, title, created_at, updated_at = chat
                
                # Formatear fecha
                created_date = datetime.fromisoformat(created_at).strftime('%d/%m %H:%M')
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"💬 {title[:20]}...", key=f"chat_{chat_id}", use_container_width=True):
                        chat_manager = ChatManager()
                        chat_manager.switch_chat(chat_id)
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{chat_id}", help="Eliminar chat"):
                        chat_manager = ChatManager()
                        chat_manager.delete_chat(chat_id)
                        st.rerun()
                
                st.caption(f"Creado: {created_date}")

def render_chat_history():
    """Renderiza el historial de mensajes del chat actual"""
    chat_manager = ChatManager()
    messages = chat_manager.get_chat_history()
    
    if not messages:
        st.info("Inicia una conversación escribiendo tu consulta abajo")
        return
    
    # Mostrar historial de mensajes
    for sender, content in messages:
        if sender == "user":
            with st.chat_message("user"):
                st.write(content)
        else:
            with st.chat_message("assistant"):
                st.write(content)
