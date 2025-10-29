"""
Agente Simplificado - EcoMarket
"""

import os
import re
from typing import Dict, Any
from langchain_community.chat_models import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from pathlib import Path
import tomllib

from agent_tools import (
    consultar_estado_pedido,
    verificar_elegibilidad_producto,
    generar_etiqueta_devolucion
)

# Configuración
BASE = Path(__file__).resolve().parents[1]
SETTINGS = BASE / "src" / "settings.toml"
ARTIFACTS = BASE / "artifacts" / "faiss_index"

with open(SETTINGS, "rb") as f:
    cfg = tomllib.load(f)


class EcoMarketAgent:
    """
    Agente simplificado que NO usa ReAct.
    """
    
    def __init__(self):
        self.llm = ChatOllama(
            model=cfg["model"]["name"],
            temperature=0.2,
            num_ctx=1024,
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        )
        
        # Setup RAG
        emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        db = FAISS.load_local(str(ARTIFACTS), emb, allow_dangerous_deserialization=True)
        self.retriever = db.as_retriever(search_kwargs={"k": 3})
    
    def _extraer_datos_pedido(self, query: str) -> Dict[str, str]:
        """Extrae order_id y product_id del texto usando regex"""
        
        # Buscar número de pedido (5 dígitos)
        numeros = re.findall(r'\b(\d{5})\b', query)
        order_id = numeros[0] if numeros else None
        
        # Buscar nombre de producto
        product_id = None
        
        # Patrones para extraer nombre de producto
        patterns = [
            r'devolver (?:el |la |los |las )?([A-Za-zÁ-úñÑ\s]+?)(?:\s+del|\s+de|\s+pedido|\s+$)',
            r'producto ([A-Za-zÁ-úñÑ\s]+?)(?:\s+del|\s+de|\s+pedido|\s+$)',
            r'(?:el |la |los |las )([A-Za-zÁ-úñÑ\s]+?)(?:\s+del|\s+de|\s+pedido)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                product_id = match.group(1).strip()
                break
        
        return {"order_id": order_id, "product_id": product_id}
    
    def _es_consulta_informativa(self, query: str) -> bool:
        """Detecta si es una pregunta general (no acción)"""
        palabras_pregunta = [
            "cómo", "como", "qué", "que", "cuál", "cual", 
            "cuándo", "cuando", "política", "plazo", "puedo"
        ]
        query_lower = query.lower()
        
        # Si tiene palabra de pregunta Y NO tiene número de pedido, es informativa
        tiene_pregunta = any(palabra in query_lower for palabra in palabras_pregunta)
        numeros = re.findall(r'\b(\d{5})\b', query)
        
        return tiene_pregunta and len(numeros) == 0
    
    def _responder_informativa(self, query: str) -> str:
        """Responde preguntas generales usando RAG"""
        try:
            docs = self.retriever.get_relevant_documents(query)
            context = "\n".join([doc.page_content for doc in docs[:2]])
            
            prompt = f"""Responde esta pregunta de forma clara y concisa basándote en el contexto.

Contexto:
{context}

Pregunta: {query}

Respuesta:"""
            
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error obteniendo información: {str(e)}"
    
    def run(self, query: str) -> Dict[str, Any]:
        """Ejecuta el agente con lógica simplificada"""
        
        # 1. Detectar si es consulta informativa
        if self._es_consulta_informativa(query):
            response = self._responder_informativa(query)
            return {
                "success": True,
                "response": response,
                "used_tools": [],
                "intermediate_steps": []
            }
        
        # 2. Extraer datos del pedido
        datos = self._extraer_datos_pedido(query)
        order_id = datos["order_id"]
        product_id = datos["product_id"]
        
        print(f"🔍 Datos extraídos: order_id={order_id}, product_id={product_id}")
        
        # 3. Si faltan datos, solicitarlos
        if not order_id:
            return {
                "success": True,
                "response": """Para ayudarte necesito el **número de pedido**.

Ejemplo: "Quiero devolver el Perfume floral del pedido 20002"

¿Cuál es tu número de pedido?""",
                "used_tools": [],
                "intermediate_steps": []
            }
        
        if not product_id:
            # Si solo tiene order_id, buscar productos del pedido
            try:
                estado = consultar_estado_pedido.invoke({"order_id": order_id})
                if estado.get("existe"):
                    productos = estado.get("productos", [])
                    productos_str = "\n".join([f"  • {p}" for p in productos])
                    return {
                        "success": True,
                        "response": f"""Encontré el pedido {order_id}. ¿Cuál producto deseas devolver?

Productos en este pedido:
{productos_str}

Por favor especifica el nombre del producto.""",
                        "used_tools": ["consultar_estado_pedido"],
                        "intermediate_steps": [estado]
                    }
                else:
                    return {
                        "success": True,
                        "response": f"No encontré el pedido {order_id}. Por favor verifica el número.",
                        "used_tools": [],
                        "intermediate_steps": []
                    }
            except Exception as e:
                return {
                    "success": False,
                    "response": f"Error consultando pedido: {str(e)}",
                    "used_tools": [],
                    "intermediate_steps": []
                }
        
        # 4. Ejecutar flujo de devolución con datos completos
        try:
            print(f"✅ Iniciando flujo de devolución: {order_id} / {product_id}")
            
            # Paso 1: Consultar estado del pedido
            estado = consultar_estado_pedido.invoke({
                "order_id": order_id,
                "product_id": product_id
            })
            
            if not estado.get("existe"):
                return {
                    "success": True,
                    "response": f"❌ No encontré el pedido {order_id} en nuestros registros.",
                    "used_tools": ["consultar_estado_pedido"],
                    "intermediate_steps": [estado]
                }
            
            if not estado.get("producto_existe"):
                productos = estado.get("productos", [])
                productos_str = "\n".join([f"  • {p}" for p in productos])
                return {
                    "success": True,
                    "response": f"""❌ El producto "{product_id}" no está en el pedido {order_id}.

Productos disponibles:
{productos_str}

¿Cuál deseas devolver?""",
                    "used_tools": ["consultar_estado_pedido"],
                    "intermediate_steps": [estado]
                }
            
            if not estado.get("fue_entregado"):
                return {
                    "success": True,
                    "response": f"""⏳ El pedido {order_id} está en estado: **{estado.get('estado_actual')}**

Para iniciar una devolución, el pedido debe estar entregado primero.

📅 Fecha estimada de entrega: {estado.get('fecha_estimada', 'No disponible')}

Una vez lo recibas, podrás solicitar la devolución dentro de los 30 días siguientes.""",
                    "used_tools": ["consultar_estado_pedido"],
                    "intermediate_steps": [estado]
                }
            
            # Paso 2: Verificar elegibilidad
            elegibilidad = verificar_elegibilidad_producto.invoke({
                "order_id": order_id,
                "product_id": product_id,
                "motivo_devolucion": "Solicitud del cliente",
                "fecha_entrega": estado.get("fecha_entrega"),
                "estado_producto": "sellado"
            })
            
            if not elegibilidad.get("es_elegible"):
                pasos = elegibilidad.get('pasos_siguientes', [])
                pasos_str = "\n".join([f"• {p}" for p in pasos]) if pasos else ""
                
                return {
                    "success": True,
                    "response": f"""❌ **Devolución No Permitida**

{elegibilidad.get('razon')}

{pasos_str}""",
                    "used_tools": ["consultar_estado_pedido", "verificar_elegibilidad_producto"],
                    "intermediate_steps": [estado, elegibilidad]
                }
            
            # Paso 3: Generar etiqueta de devolución
            etiqueta = generar_etiqueta_devolucion.invoke({
                "order_id": order_id,
                "product_id": product_id,
                "categoria_proceso": elegibilidad.get("categoria_proceso"),
                "motivo_devolucion": "Solicitud del cliente"
            })
            
            # Respuesta final exitosa
            response = f"""✅ **¡Devolución Aprobada!**

📋 **Número de caso:** {etiqueta.get('rma_id')}
📦 **Producto:** {product_id}
🚚 **Transportadora:** {etiqueta.get('transportadora')}
⏱️ **Tiempo estimado de recolección:** {etiqueta.get('tiempo_estimado_recoleccion')}

📝 **Instrucciones:**
{etiqueta.get('instrucciones_cliente')}

🔗 **Etiqueta de devolución:**
{etiqueta.get('etiqueta_pdf_url')}

💰 Recibirás tu reembolso en 5-7 días hábiles después de que recibamos el producto.

¿Necesitas ayuda con algo más?"""
            
            return {
                "success": True,
                "response": response,
                "used_tools": [
                    "consultar_estado_pedido",
                    "verificar_elegibilidad_producto", 
                    "generar_etiqueta_devolucion"
                ],
                "intermediate_steps": [estado, elegibilidad, etiqueta]
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "response": f"❌ Error procesando la solicitud: {str(e)}",
                "error": str(e),
                "used_tools": [],
                "intermediate_steps": []
            }
    
    def format_response(self, result: Dict[str, Any]) -> str:
        """Formatea la respuesta para el usuario"""
        response = result.get("response", "")
        
        if not result.get("success", False):
            return f"❌ **Error**\n\n{response}\n\nPor favor intenta de nuevo o contacta a soporte."
        
        used_tools = result.get("used_tools", [])
        if used_tools:
            tools_str = ", ".join(used_tools)
            response += f"\n\n---\n🔧 *Acciones realizadas: {tools_str}*"
        
        return response


def create_agent() -> EcoMarketAgent:
    """Crea instancia del agente simplificado"""
    return EcoMarketAgent()