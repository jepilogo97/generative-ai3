import json
import sys
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Rutas robustas (BASE = /app)
BASE       = Path(__file__).resolve().parents[1]
DATA_PATH  = BASE / "data" / "pedidos.json"
OUT_DIR    = BASE / "artifacts" / "faiss_index"
META_PATH  = BASE / "artifacts" / "meta.jsonl"

OUT_DIR.mkdir(parents=True, exist_ok=True)
META_PATH.parent.mkdir(parents=True, exist_ok=True)

def s(x, default=""):
    """str seguro"""
    return "" if x is None else str(x)

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"No existe {DATA_PATH}. Crea data/pedidos.json o monta el volumen correctamente."
        )

    print("📥 Cargando pedidos...")
    try:
        pedidos = json.load(open(DATA_PATH, "r", encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"pedidos.json inválido: {e}")

    if not isinstance(pedidos, list):
        raise ValueError("pedidos.json debe ser una lista de pedidos")

    texts, metas = [], []

    for p in pedidos:
        # Soporta claves en español o inglés (por si tu dataset cambia)
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

    if not texts:
        raise ValueError("No hay textos para indexar (verifica pedidos.json).")

    print("🧠 Generando embeddings (CPU)…")
    # ✅ CORRECCIÓN: Eliminado torch_dtype de model_kwargs
    emb = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"},  # Sin torch_dtype
        encode_kwargs={"normalize_embeddings": True},
    )

    db = FAISS.from_texts(texts, emb, metadatas=metas)
    db.save_local(str(OUT_DIR))
    print(f"✅ Índice guardado en {OUT_DIR}")

    with open(META_PATH, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"🗂️  Metadatos guardados en {META_PATH}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR en ingest_data:", e, file=sys.stderr)
        sys.exit(1)