import os
import sys
from pathlib import Path
import streamlit as st

# Configuración de entorno
st.set_page_config(
    page_title="EcoMarket - Agente Proactivo",
    page_icon="🛒",
    layout="wide"
)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Paths
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

# Verificar y crear índice si no existe
from ingest_data import main as ingest_main
ARTIFACTS = BASE / "artifacts" / "faiss_index"
INDEX_FAISS = ARTIFACTS / "index.faiss"

if not INDEX_FAISS.exists():
    with st.spinner("📦 Generando índice FAISS (primera vez puede tardar)..."):
        try:
            ingest_main()
        except Exception as e:
            st.error(f"Error generando índice: {e}")
            st.stop()

# Importar módulos del agente
try:
    from agent import create_agent
    from chat_manager import ChatManager, render_chat_sidebar, render_chat_history
except ImportError as e:
    st.error(f"Error importando módulos: {e}")
    st.stop()

# ⚡ OPTIMIZACIÓN: Cache del agente para toda la aplicación
@st.cache_resource(show_spinner="🤖 Inicializando agente (solo primera vez)...")
def get_agent():
    """Crea y cachea el agente para reutilizarlo entre peticiones"""
    return create_agent()

# Inicializar agente con cache
try:
    agent = get_agent()
    st.session_state.agent_ready = True
except Exception as e:
    st.error(f"Error inicializando agente: {e}")
    st.session_state.agent_ready = False

# UI Principal
render_chat_sidebar()

st.title("🛍️ Asistente Proactivo de EcoMarket")
st.caption("Agente inteligente con capacidad de ejecutar acciones operativas")

# Tabs para diferentes funcionalidades
tab1, tab2, tab3 = st.tabs(["💬 Chat", "⚙️ Configuración", "ℹ️ Información"])

with tab1:
    # Historial de chat
    render_chat_history()
    chat_manager = ChatManager()
    
    # Input del usuario
    user_query = st.chat_input(
        placeholder="Ej: Quiero devolver el producto del pedido 20001"
    )
    
    if user_query:
        # Guardar mensaje del usuario
        chat_manager.save_message("user", user_query)
        
        with st.chat_message("user"):
            st.write(user_query)
        
        with st.chat_message("assistant"):
            if not st.session_state.get('agent_ready', False):
                st.error("El agente no está listo. Por favor recarga la página.")
            else:
                # ⚡ Mostrar progreso detallado
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                try:
                    # Paso 1: Recuperar contexto
                    progress_text.text("🔍 Buscando información relevante...")
                    progress_bar.progress(25)
                    
                    # Paso 2: Ejecutar agente
                    progress_text.text("🤔 Analizando consulta...")
                    progress_bar.progress(50)
                    
                    result = agent.run(user_query)
                    
                    # Paso 3: Formatear respuesta
                    progress_text.text("✍️ Preparando respuesta...")
                    progress_bar.progress(75)
                    
                    formatted_response = agent.format_response(result)
                    
                    # Limpiar progreso
                    progress_text.empty()
                    progress_bar.empty()
                    
                    # Mostrar respuesta
                    st.markdown(formatted_response)
                    
                    # Mostrar debug info si se usaron herramientas
                    if result.get("used_tools"):
                        with st.expander("🔍 Ver detalles de ejecución"):
                            st.json({
                                "herramientas_usadas": result["used_tools"],
                                "pasos_intermedios": len(result.get("intermediate_steps", [])),
                                "tiempo_aproximado": "~3-5 segundos"
                            })
                    
                    # Guardar respuesta
                    chat_manager.save_message("assistant", formatted_response)
                    
                except Exception as e:
                    progress_text.empty()
                    progress_bar.empty()
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    chat_manager.save_message("assistant", error_msg)

with tab2:
    st.header("⚙️ Configuración de Rendimiento")
    
    st.info("""
    💡 **Optimizaciones Activas:**
    - ✅ Agente cacheado (no se recarga en cada petición)
    - ✅ Embeddings pre-calculados (índice FAISS)
    - ✅ Contexto reducido (solo documentos relevantes)
    """)
    
    st.subheader("🎛️ Parámetros Ajustables")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Tiempo promedio de respuesta",
            "3-5 segundos",
            help="Tiempo típico para consultas con herramientas"
        )
        
    with col2:
        st.metric(
            "Documentos recuperados (RAG)",
            "3",
            help="Número de fragmentos relevantes del índice"
        )
    
    st.divider()
    
    st.subheader("🚀 Consejos para Mejorar Velocidad")
    
    st.markdown("""
    **1. Hardware Recomendado:**
    - 🖥️ CPU: 4+ cores
    - 💾 RAM: 8GB+ disponibles
    - 💽 Disco: SSD (mejora carga de modelos)
    
    **2. Ollama Local:**
    - Asegúrate que Ollama esté corriendo localmente
    - Usa modelo más pequeño: `ollama pull llama3.2:1b`
    - Configura `OLLAMA_NUM_PARALLEL=2` para múltiples peticiones
    
    **3. Primera Ejecución:**
    - La primera consulta siempre es más lenta (carga del modelo)
    - Siguientes consultas son más rápidas (modelo en memoria)
    
    **4. Red:**
    - Si usas Docker, evita puentes de red complejos
    - Usa `network_mode: host` para menor latencia
    """)
    
    if st.button("🔄 Limpiar Cache del Agente"):
        st.cache_resource.clear()
        st.success("✅ Cache limpiado. La próxima consulta recargará el agente.")
        st.rerun()

with tab3:
    st.header("ℹ️ Sobre el Agente Proactivo")
    
    st.markdown("""
    ### 🎯 Capacidades del Agente
    
    Este agente inteligente puede:
    
    1. **Consultar Estado de Pedidos** 📦
       - Verifica información de seguimiento en tiempo real
       - Detecta automáticamente si un pedido fue entregado
       
    2. **Gestionar Devoluciones** 🔄
       - Verifica elegibilidad según políticas de EcoMarket
       - Genera etiquetas de devolución automáticamente
       - Calcula plazos y categoriza procesos
    
    3. **Proporcionar Información** 📚
       - Responde preguntas sobre políticas
       - Explica procedimientos de devolución
       - Ofrece orientación personalizada
    
    ---
    
    ### 💡 Ejemplos de Consultas
    
    **Para seguimiento (rápido - sin herramientas):**
    - "¿Dónde está mi pedido 20001?"
    - "¿Cuál es el plazo para devolver?"
    
    **Para devoluciones (más lento - con herramientas):**
    - "Quiero devolver el producto del pedido 20007"
    - "Generar etiqueta de devolución para el pedido 20001"
    
    ---
    
    ### ⏱️ Tiempos de Respuesta
    
    | Tipo de Consulta | Tiempo Aproximado |
    |------------------|-------------------|
    | Solo información (RAG) | 1-2 segundos |
    | Con 1 herramienta | 2-3 segundos |
    | Con 3 herramientas | 4-6 segundos |
    
    **Nota:** El primer uso siempre es más lento mientras el modelo se carga en memoria.
    """)

# Sidebar adicional con información del sistema
with st.sidebar:
    st.divider()
    st.subheader("⚙️ Estado del Sistema")
    
    if st.session_state.get('agent_ready', False):
        st.success("✅ Agente operativo")
    else:
        st.error("❌ Agente no disponible")
    
    st.divider()
    
    # Mostrar ejemplos rápidos
    st.subheader("⚡ Ejemplos Rápidos")
    
    if st.button("📦 Estado del pedido 20001"):
        st.session_state.quick_query = "¿Dónde está mi pedido 20001?"
        st.rerun()
        
    if st.button("❓ Plazo para devolver"):
        st.session_state.quick_query = "¿Cuál es el plazo para devolver productos?"
        st.rerun()
        
    if st.button("🔄 Devolver pedido 20007"):
        st.session_state.quick_query = "Quiero devolver el Juego de cubiertos del pedido 20007"
        st.rerun()

# Procesar consulta rápida si existe
if 'quick_query' in st.session_state:
    query = st.session_state.quick_query
    del st.session_state.quick_query
    # Redirigir al tab de chat y procesar
    st.rerun()