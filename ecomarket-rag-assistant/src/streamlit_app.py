import os
import subprocess, sys
import torch
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
import tomllib
import streamlit as st

# ---- Configuración de entorno ----
st.set_page_config(page_title="EcoMarket Chat", page_icon="🛒")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ---- Paths ----
BASE = Path(__file__).resolve().parents[1]  # /app
SETTINGS = BASE / "src" / "settings.toml"
ARTIFACTS = BASE / "artifacts" / "faiss_index"
DATA_PATH = BASE / "data" / "pedidos.json"

# ---- Cargar configuración ----
with open(SETTINGS, "rb") as f:
    cfg = tomllib.load(f)

role = cfg["prompts"]["role_prompt"]
instr = cfg["prompts"]["instruction_prompt"]
model_name = cfg["model"]["name"]

# ---- Bootstrap: crea el índice si falta ----
INDEX_FAISS = ARTIFACTS / "index.faiss"
if not INDEX_FAISS.exists():
    with st.spinner("📦 Generando índice FAISS (primera vez puede tardar)…"):
        subprocess.run([sys.executable, str(BASE / "src" / "ingest_data.py")], check=True)

# ---- Embeddings (CPU) ----
emb = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# ---- Cargar FAISS ----
db = FAISS.load_local(str(ARTIFACTS), emb, allow_dangerous_deserialization=True)
retriever = db.as_retriever(search_kwargs={"k": 4})

# ---- LLM ----
llm = ChatOllama(
    model=model_name, 
    temperature=0.2,
    num_ctx=2048,      # menos memoria en runtime
    num_batch=32,
    base_url="http://host.docker.internal:11434" 
)

prompt = ChatPromptTemplate.from_template(
    "{role}\n\n{instr}\n\n>>>>>CONTENIDO<<<<<\n{context}\n<<<<<CONTENIDO>>>>>\n\nPregunta:\n{question}"
)


# ---------- UI ----------
from chat_manager import ChatManager, render_chat_sidebar, render_chat_history
render_chat_sidebar()
st.title("🛍️ Asistente de EcoMarket")
render_chat_history()
chat_manager = ChatManager()

# Botón opcional para reconstruir índice desde la UI
with st.sidebar:
    if st.button("🔁 Reconstruir índice FAISS"):
        with st.spinner("Reconstruyendo índice…"):
            subprocess.run([sys.executable, str(BASE / "src" / "ingest_data.py")], check=True)
        st.success("Índice reconstruido. Recarga la página (Ctrl+R).")
        
# Agregar ejemplos de consultas en el sidebar
st.sidebar.markdown("### 💡 Ejemplos de consultas:")
st.sidebar.markdown("""
**Seguimiento de pedidos:**
- ¿Dónde está mi pedido 20001?
- ¿Cuándo llega mi pedido 20003?

**Políticas de devolución:**
- ¿Cuál es el plazo para devolver?
- ¿Puedo devolver alimentos perecederos?
- ¿Cómo solicito una devolución?
- ¿Qué productos no son retornables?

**Productos:**
- ¿Puedo devolver la Laptop del pedido 20003?
- ¿El Yogur griego acepta devoluciones?
""")

user_query = st.chat_input(placeholder="Ej: ¿Dónde está mi pedido 20001?")
if user_query:
    chat_manager.save_message("user", user_query)
    with st.chat_message("user"):
        st.write(user_query)

    with st.chat_message("assistant"):
        with st.spinner("🤔 Procesando tu consulta..."):
            docs = retriever.get_relevant_documents(user_query)
            context = "\n".join(d.page_content for d in docs)
            full_prompt = prompt.format(role=role, instr=instr, context=context, question=user_query)
            resp = llm.invoke(full_prompt)
            st.write(resp.content)
            chat_manager.save_message("assistant", resp.content)
