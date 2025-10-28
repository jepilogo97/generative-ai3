import json
import sys
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import torch

# Rutas robustas (BASE = /app)
BASE       = Path(__file__).resolve().parents[1]
DATA_PATH  = BASE / "data" / "pedidos.json"
PDF_PATH   = BASE / "data" / "politicas_devolucion.pdf"
FAQ_PATH   = BASE / "data" / "faqs.json"
OUT_DIR    = BASE / "artifacts" / "faiss_index"
META_PATH  = BASE / "artifacts" / "meta.jsonl"


OUT_DIR.mkdir(parents=True, exist_ok=True)
META_PATH.parent.mkdir(parents=True, exist_ok=True)

def s(x, default=""):
    """str seguro"""
    return "" if x is None else str(x)

def load_pdf_policies():
    """Carga y procesa el PDF de políticas de devolución"""
    if not PDF_PATH.exists():
        print(f"⚠️  No se encontró {PDF_PATH}, saltando políticas PDF")
        return [], []
    
    print(f"📄 Cargando políticas desde PDF...")
    
    # Cargar el PDF
    loader = PyPDFLoader(str(PDF_PATH))
    documents = loader.load()
    
    # Configurar el splitter para chunks más manejables
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # Tamaño del chunk en caracteres
        chunk_overlap=50,    # Solapamiento entre chunks
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # Dividir documentos en chunks
    chunks = text_splitter.split_documents(documents)
    
    texts = []
    metas = []
    
    for i, chunk in enumerate(chunks):
        text = chunk.page_content.strip()
        if len(text) < 50:  # Ignorar chunks muy pequeños
            continue
            
        texts.append(text)
        metas.append({
            "source": "politicas_devolucion.pdf",
            "type": "return_policy",
            "page": chunk.metadata.get("page", 0),
            "chunk_id": i,
            "doc_version": "2.1",
            "valid_from": "2025-01-01"
        })
    
    print(f"✅ {len(texts)} fragmentos extraídos del PDF")
    return texts, metas

def load_pedidos():
    """Carga y procesa pedidos desde JSON"""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"No existe {DATA_PATH}. Crea data/pedidos.json o monta el volumen correctamente."
        )

    print("📥 Cargando pedidos desde JSON...")
    try:
        pedidos = json.load(open(DATA_PATH, "r", encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"pedidos.json inválido: {e}")

    if not isinstance(pedidos, list):
        raise ValueError("pedidos.json debe ser una lista de pedidos")

    texts, metas = [], []

    for p in pedidos:
        # Soporta claves en español o inglés
        tracking = p.get("tracking_number") or p.get("tracking") or p.get("order_id")
        estado   = p.get("estado") or p.get("status")
        destino  = p.get("destino") or (p.get("customer") or {}).get("city")
        trans    = p.get("transportadora") or p.get("carrier")
        f_est    = p.get("fecha_estimada") or p.get("estimated_delivery")

        # Registro principal del pedido
        desc_basica = (
            f"Pedido {s(tracking)}: {s(estado)}"
            + (f" con destino {s(destino)}" if destino else "")
            + (f" vía {s(trans)}" if trans else "")
            + (f". Fecha estimada: {s(f_est)}" if f_est else "")
            + "."
        ).strip()

        texts.append(desc_basica)
        metas.append({
            "source": "pedidos.json",
            "type": "order_status",
            "tracking_number": s(tracking),
            "estado": s(estado),
            "destino": s(destino),
            "transportadora": s(trans),
            "fecha_estimada": s(f_est),
        })

        # Productos y políticas por producto
        for prod in p.get("productos", p.get("items", [])) or []:
            nombre = prod.get("nombre") or prod.get("name")
            categoria = prod.get("categoria") or prod.get("category")
            dev_aceptada = prod.get("dev_aceptada", prod.get("returnable", False))

            dev_text = "acepta devoluciones" if dev_aceptada else "NO acepta devoluciones"
            desc_prod = f"Producto: {s(nombre)} (categoría: {s(categoria)}). Este producto {dev_text}."
            texts.append(desc_prod)
            metas.append({
                "source": "pedidos.json",
                "type": "product_info",
                "tracking_number": s(tracking),
                "producto": s(nombre),
                "categoria": s(categoria),
                "dev_aceptada": bool(dev_aceptada),
            })

        # Política especial: Alimento perecedero
        tiene_perecedero = any(
            (prod.get("categoria") or prod.get("category")) == "Alimento perecedero"
            for prod in (p.get("productos", p.get("items", [])) or [])
        )
        if tiene_perecedero:
            policy_text = (
                "Política especial: Los alimentos perecederos NO pueden ser devueltos "
                "por razones de seguridad alimentaria."
            )
            texts.append(policy_text)
            metas.append({
                "source": "policies",
                "type": "return_policy",
                "categoria": "Alimento perecedero",
                "policy": "no_return",
                "tracking_number": s(tracking),
            })
    
    print(f"✅ {len(texts)} fragmentos extraídos de pedidos")
    return texts, metas

def load_faqs():
    """Carga y procesa FAQs desde JSON"""
    if not FAQ_PATH.exists():
        print(f"⚠️  No se encontró {FAQ_PATH}, saltando FAQs")
        return [], []

    print("❓ Cargando FAQs desde JSON...")
    try:
        faqs = json.load(open(FAQ_PATH, "r", encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"faqs.json inválido: {e}")

    if not isinstance(faqs, list):
        raise ValueError("faqs.json debe ser una lista de FAQs")

    texts, metas = [], []
    for faq in faqs:
        pregunta  = faq.get("pregunta") or faq.get("question") or ""
        respuesta = faq.get("respuesta") or faq.get("answer") or ""
        categoria = faq.get("categoria") or faq.get("category") or "General"
        fid       = faq.get("id")

        if not pregunta or not respuesta:
            # si falta alguno, no indexamos ese ítem
            continue

        txt = f"Pregunta frecuente: {pregunta}\nRespuesta: {respuesta}"
        texts.append(txt)
        metas.append({
            "source": "faqs.json",
            "type": "faq",
            "categoria": categoria,
            "id": fid
        })

    print(f"✅ {len(texts)} FAQs preparadas")
    return texts, metas


def main():
    print("=" * 60)
    print("🚀 INICIANDO INGESTA DE DATOS")
    print("=" * 60)

    all_texts = []
    all_metas = []

    # 1) Pedidos
    try:
        texts_pedidos, metas_pedidos = load_pedidos()
        all_texts.extend(texts_pedidos)
        all_metas.extend(metas_pedidos)
    except Exception as e:
        print(f"⚠️  Error cargando pedidos: {e}")

    # 2) FAQs
    try:
        texts_faq, metas_faq = load_faqs()
        all_texts.extend(texts_faq)
        all_metas.extend(metas_faq)
    except Exception as e:
        print(f"⚠️  Error cargando FAQs: {e}")

    # 3) Políticas PDF
    try:
        texts_pdf, metas_pdf = load_pdf_policies()
        all_texts.extend(texts_pdf)
        all_metas.extend(metas_pdf)
    except Exception as e:
        print(f"⚠️  Error cargando PDF: {e}")

    if not all_texts:
        raise ValueError("No hay textos para indexar. Verifica tus archivos de datos.")

    print(f"\n📊 Total de fragmentos a indexar: {len(all_texts)}")
    print("   - Pedidos JSON:", len([m for m in all_metas if m.get("source") == "pedidos.json"]))
    print("   - FAQs JSON:", len([m for m in all_metas if m.get("source") == "faqs.json"]))
    print("   - Políticas PDF:", len([m for m in all_metas if m.get("source") == "politicas_devolucion.pdf"]))

    print("\n🧠 Generando embeddings (CPU)…")
    emb = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    print("💾 Creando índice FAISS...")
    db = FAISS.from_texts(all_texts, emb, metadatas=all_metas)
    db.save_local(str(OUT_DIR))
    print(f"✅ Índice guardado en {OUT_DIR}")

    print("📝 Guardando metadatos...")
    with open(META_PATH, "w", encoding="utf-8") as f:
        for m in all_metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"✅ Metadatos guardados en {META_PATH}")

    print("\n" + "=" * 60)
    print("✅ INGESTA COMPLETADA EXITOSAMENTE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR EN INGESTA")
        print("=" * 60)
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)