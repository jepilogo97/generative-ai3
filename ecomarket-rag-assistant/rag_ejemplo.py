from langchain.prompts import ChatPromptTemplate
# ⚠️ usa HuggingFaceEmbeddings (más robusto) o fija device en SentenceTransformerEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOllama
from langchain.chains import RetrievalQA
import tomllib
from pathlib import Path
import os
import torch
import subprocess, sys

# Sugerencias de entorno (opcional, ayudan en contenedor)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HOME", "/app/.cache/huggingface")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Paths
BASE = Path(__file__).parent
SETTINGS = BASE / "src" / "settings.toml"
ARTIFACTS = BASE / "artifacts" / "faiss_index"

# Load prompts
with open(SETTINGS, "rb") as f:
    conf = tomllib.load(f)

role = conf["prompts"]["role_prompt"]
instr = conf["prompts"]["instruction_prompt"]
model_name = conf["model"]["name"]

# Embeddings (CPU explícito para evitar meta device)
MODEL_EMB = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
emb = HuggingFaceEmbeddings(
    model_name=MODEL_EMB,
    model_kwargs={"device": "cpu", "torch_dtype": torch.float32},
    encode_kwargs={"normalize_embeddings": True},
)

# Bootstrap: si no existe el índice, créalo
if not (ARTIFACTS / "index.faiss").exists():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    print("⚠️ No existe el índice FAISS. Ejecutando ingest_data.py …")
    subprocess.run([sys.executable, str(BASE / "src" / "ingest_data.py")], check=True)

# Cargar FAISS
db = FAISS.load_local(str(ARTIFACTS), emb, allow_dangerous_deserialization=True)
retriever = db.as_retriever(search_kwargs={"k": 4})

# LLM (Ollama)
llm = ChatOllama(model=model_name, temperature=0.2)

prompt = ChatPromptTemplate.from_template(
    "{role}\n\n{instr}\n\n>>>>>CONTENIDO<<<<<\n{context}\n<<<<<CONTENIDO>>>>>\n\nPregunta:\n{question}"
)

chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt.partial(role=role, instr=instr)},
    return_source_documents=True,
)

if __name__ == "__main__":
    q = input("🗨️  Pregunta: ")
    res = chain({"query": q})
    print("\n🧾 Respuesta:\n", res["result"])
