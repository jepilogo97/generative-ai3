"""
Agente Simplificado - EcoMarket (refactor)
"""

import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

import tomllib
from langchain_community.chat_models import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from agent_tools import (
    consultar_estado_pedido,
    verificar_elegibilidad_producto,
    generar_etiqueta_devolucion,
)

# ──────────────────────────────────────────────────────────────────────────────
# Configuración base
# ──────────────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[1]
SETTINGS = BASE / "src" / "settings.toml"
ARTIFACTS = BASE / "artifacts" / "faiss_index"

with open(SETTINGS, "rb") as f:
    cfg = tomllib.load(f)

# ──────────────────────────────────────────────────────────────────────────────
# Constantes de intención
# ──────────────────────────────────────────────────────────────────────────────
INTENT_INFORMATIVA = "informativa"
INTENT_DEVOLUCION = "devolucion"
INTENT_DESAMBIGUAR_PRODUCTO = "desambiguar_producto"

ACCIONES_EXPLICITAS = [
    "quiero devolver",
    "deseo devolver",
    "necesito devolver",
    "iniciar devolución",
    "empezar devolución",
    "comenzar devolución",
    "generar etiqueta",
    "crear etiqueta",
    "hacer devolución",
    "hacer una devolución",
    "solicitar devolución",
    "procesar devolución",
]

PALABRAS_INTERROGATIVAS = [
    "cuánto", "cuanto", "cuántos", "cuantos",
    "cuándo", "cuando",
    "cómo", "como",
    "qué", "que",
    "cuál", "cual", "cuáles", "cuales",
    "dónde", "donde",
    "por qué", "porque",
    "para qué",
]

PALABRAS_CONSULTA = [
    "política", "políticas",
    "plazo", "tiempo", "días",
    "requisito", "requisitos",
    "condición", "condiciones",
    "información", "info",
    "explica", "dime", "cuéntame",
    "comparte", "muestra",
]

ORDER_ID_REGEX = r"\b(\d{5,10})\b"


class EcoMarketAgent:
    """
    Agente simplificado con detección mejorada de intención y flujo de devolución.
    """

    def __init__(self) -> None:
        # LLM
        self.llm = ChatOllama(
            model=cfg["model"]["name"],
            temperature=0.2,
            num_ctx=1024,
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        )

        # RAG
        emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        db = FAISS.load_local(str(ARTIFACTS), emb, allow_dangerous_deserialization=True)
        self.retriever = db.as_retriever(search_kwargs={"k": 3})

        # Contexto conversacional simple
        self.conversation_context: Dict[str, Optional[str]] = {
            "last_order_id": None,
            "last_product_id": None,
            "last_action": None,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Helpers de logging
    # ──────────────────────────────────────────────────────────────────────
    def _log(self, msg: str) -> None:
        # centralizar prints
        print(msg)

    # ──────────────────────────────────────────────────────────────────────
    # 1. Detección de intención
    # ──────────────────────────────────────────────────────────────────────
    def _detectar_intencion(self, query: str) -> str:
        """
        Devuelve una intención: informativa | devolucion
        """
        q = query.lower()
        self._log(f"\n🔍 Analizando intención de: '{query}'")

        # 1. Interrogativas → informativa
        if any(p in q for p in PALABRAS_INTERROGATIVAS):
            self._log("   ✅ Palabra interrogativa detectada → INFORMATIVA")
            return INTENT_INFORMATIVA

        # 2. Palabras de consulta → informativa
        if any(p in q for p in PALABRAS_CONSULTA):
            self._log("   ✅ Palabra de consulta detectada → INFORMATIVA")
            return INTENT_INFORMATIVA

        # 3. Puedo / se puede → informativa
        if ("puedo" in q or "se puede" in q) and "quiero" not in q:
            self._log("   ✅ 'puedo / se puede' → INFORMATIVA")
            return INTENT_INFORMATIVA

        # 4. Signo de interrogación → informativa
        if "?" in q:
            self._log("   ✅ Signo de interrogación → INFORMATIVA")
            return INTENT_INFORMATIVA

        # 5. Acciones explícitas → devolución
        for accion in ACCIONES_EXPLICITAS:
            if accion in q:
                self._log(f"   ❌ Acción explícita detectada: '{accion}' → DEVOLUCIÓN")
                return INTENT_DEVOLUCION

        # 6. ¿Trae número de pedido? → devolución
        if re.search(ORDER_ID_REGEX, q):
            self._log("   ❌ Número de pedido detectado → DEVOLUCIÓN")
            return INTENT_DEVOLUCION

        # Default
        self._log("   ✅ Default → INFORMATIVA")
        return INTENT_INFORMATIVA

    # ──────────────────────────────────────────────────────────────────────
    # 2. Extracción de datos del pedido
    # ──────────────────────────────────────────────────────────────────────
    def _extraer_datos_pedido(self, query: str) -> Dict[str, Optional[str]]:
        """Extrae order_id y product_id del texto usando regex y contexto."""
        order_id = None
        product_id = None

        # order_id
        numeros = re.findall(ORDER_ID_REGEX, query)
        if numeros:
            order_id = numeros[0]
        elif self.conversation_context.get("last_order_id"):
            order_id = self.conversation_context["last_order_id"]
            self._log(f"📝 Reutilizando order_id del contexto: {order_id}")

        # product_id (naive)
        patterns = [
            r'devolver (?:el |la |los |las )?([A-Za-zÁ-úñÑ\s]+?)(?:\s+del|\s+de|\s+pedido|\.|$)',
            r'producto ([A-Za-zÁ-úñÑ\s]+?)(?:\s+del|\s+de|\s+pedido|\.|$)',
            r'(?:el |la |los |las )([A-Za-zÁ-úñÑ\s]+?)(?:\s+del|\s+de|\s+pedido|\.|$)',
            r'^([A-Za-zÁ-úñÑ\s]+?)$',
        ]
        q = query.strip()
        for pattern in patterns:
            m = re.search(pattern, q, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > 3:
                    product_id = candidate
                    break

        # actualizar contexto
        if order_id:
            self.conversation_context["last_order_id"] = order_id
        if product_id:
            self.conversation_context["last_product_id"] = product_id

        return {"order_id": order_id, "product_id": product_id}

    # ──────────────────────────────────────────────────────────────────────
    # 3. RAG (informativo)
    # ──────────────────────────────────────────────────────────────────────
    def _responder_informativa(self, query: str) -> str:
        """Responde preguntas generales usando RAG con validación de contexto"""
        try:
            print(f"📚 Consultando base de conocimiento para: {query}")
            
            # Recuperar documentos relevantes
            docs = self.retriever.get_relevant_documents(query)
            
            if not docs:
                return self._respuesta_fallback()
            
            # Filtrar documentos relevantes (score mínimo)
            docs_relevantes = []
            for doc in docs[:5]:  # Considerar top 5
                # Solo incluir si es relevante para la pregunta
                if self._es_documento_relevante(query, doc.page_content):
                    docs_relevantes.append(doc)
            
            if not docs_relevantes:
                print(f"⚠️  No se encontraron documentos suficientemente relevantes")
                return self._respuesta_fallback()
            
            # Crear contexto desde los documentos relevantes
            context = "\n\n---\n\n".join([doc.page_content for doc in docs_relevantes[:3]])
            
            print(f"📄 Usando {len(docs_relevantes)} documentos relevantes")
            
            # Prompt mejorado con validación estricta
            prompt = f"""Eres un asistente experto de EcoMarket especializado en políticas de devolución.

            CONTEXTO PROPORCIONADO:
            {context}

            PREGUNTA DEL USUARIO:
            {query}

            INSTRUCCIONES CRÍTICAS:
            1. Responde SOLO basándote en el contexto proporcionado
            2. Si el contexto habla de "alimentos perecederos" pero la pregunta NO menciona alimentos, NO uses esa información
            3. Si la pregunta es sobre un "producto defectuoso", busca información sobre defectos, NO sobre perecederos
            4. Si el contexto no tiene información relevante, di "No tengo información específica sobre eso"
            5. NO inventes políticas ni mezcles información de diferentes categorías de productos
            6. Usa un tono profesional y empático
            7. Máximo 3 párrafos

            REGLAS ESPECIALES:
            - Producto defectuoso o dañado en transporte = SIEMPRE elegible para devolución
            - Alimentos perecederos, higiene, medicamentos = NO elegibles para devolución
            - Plazo general = 30 días desde la entrega
            - NO confundas categorías de productos

            RESPUESTA:"""
                    
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # Validación post-generación
            if self._respuesta_tiene_errores(query, answer):
                print(f"⚠️  Respuesta del LLM parece tener errores, usando fallback")
                return self._respuesta_fallback()
            
            print(f"✅ Respuesta generada y validada")
            return answer
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return self._respuesta_fallback()

    def _es_documento_relevante(self, query: str, doc_content: str) -> bool:
        """
        Verifica si un documento es relevante para la consulta.
        Evita que contexto sobre 'perecederos' se use para preguntas sobre 'defectuosos'.
        """
        query_lower = query.lower()
        doc_lower = doc_content.lower()
        
        # Si pregunta sobre defectuoso/dañado, solo docs sobre eso
        if "defectuoso" in query_lower or "dañado" in query_lower or "roto" in query_lower:
            # Rechazar docs sobre perecederos
            if "perecedero" in doc_lower and "defectuoso" not in doc_lower:
                print(f"   🚫 Rechazando doc sobre perecederos (pregunta sobre defectuoso)")
                return False
        
        # Si pregunta sobre perecederos, solo docs relevantes
        if "perecedero" in query_lower or "alimento" in query_lower:
            if "perecedero" in doc_lower or "alimento" in doc_lower:
                return True
            return False
        
        # Por defecto, aceptar doc (tiene score alto de similitud)
        return True

    def _respuesta_tiene_errores(self, query: str, answer: str) -> bool:
        """
        Detecta si la respuesta del LLM tiene errores obvios.
        """
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        # Error 1: Pregunta sobre defectuoso, responde sobre perecedero
        if ("defectuoso" in query_lower or "dañado" in query_lower or "roto" in query_lower):
            if "perecedero" in answer_lower and "defectuoso" not in answer_lower:
                print(f"   ❌ Error detectado: Responde sobre perecederos cuando pregunta sobre defectuoso")
                return True
        
        # Error 2: Dice que NO puede devolver cuando pregunta sobre defectuoso
        if ("defectuoso" in query_lower or "dañado" in query_lower):
            if "no puedo devolver" in answer_lower or "no aceptamos devoluciones" in answer_lower:
                print(f"   ❌ Error detectado: Rechaza devolución de producto defectuoso")
                return True
        
        return False

    def _respuesta_fallback(self) -> str:
        """Respuesta por defecto cuando falla el RAG"""
        return """**Políticas generales de devolución de EcoMarket:**

        📅 **Plazo:** Tienes 30 días desde la fecha de entrega para devolver tu producto

        ✅ **SÍ puedes devolver:**
        - Productos defectuosos o dañados en el transporte
        - Productos que no cumplen con la descripción
        - Productos en su empaque original sin uso

        ❌ **NO puedes devolver:**
        - Alimentos perecederos
        - Productos de higiene personal
        - Medicamentos

        🚨 **Productos defectuosos:**
        Si recibiste un producto defectuoso o dañado, puedes devolverlo incluso si el empaque fue abierto. Contáctanos para iniciar el proceso de devolución prioritaria.

        💡 ¿Tienes un pedido específico? Proporcióname el número de pedido y te ayudo con el proceso."""

    # ──────────────────────────────────────────────────────────────────────
    # 4. Flujo operativo de devolución
    # ──────────────────────────────────────────────────────────────────────
    def _flujo_devolucion(self, order_id: str, product_id: Optional[str]) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de devolución, asumiendo que ya sabemos
        que la intención es operativa.
        """
        # 1. Si no hay order_id, pedirlo
        if not order_id:
            return self._resp(
                True,
                "Para procesar la devolución necesito el **número de pedido**.\n\n"
                'Ejemplo: "Quiero devolver el Perfume floral del pedido 20002"\n\n'
                "¿Cuál es tu número de pedido?",
            )

        # 2. Si no hay product_id, intentar listar productos
        if not product_id:
            try:
                estado = consultar_estado_pedido.invoke({"order_id": order_id})
            except Exception as e:
                return self._resp(False, f"Error consultando pedido: {str(e)}")

            if not estado.get("existe"):
                return self._resp(True, f"No encontré el pedido {order_id}. Por favor verifica el número.")

            productos = estado.get("productos", [])
            productos_str = "\n".join([f"  • {p}" for p in productos])
            return self._resp(
                True,
                f"Encontré el pedido {order_id}. ¿Cuál producto deseas devolver?\n\n"
                f"Productos en este pedido:\n{productos_str}\n\n"
                "Por favor especifica el nombre del producto.",
                used_tools=["consultar_estado_pedido"],
                intermediate=[estado],
            )

        # 3. Flujo completo
        try:
            # Paso 1: consultar estado
            estado = consultar_estado_pedido.invoke(
                {"order_id": order_id, "product_id": product_id}
            )

            if not estado.get("existe"):
                return self._resp(
                    True,
                    f"❌ No encontré el pedido {order_id} en nuestros registros.",
                    used_tools=["consultar_estado_pedido"],
                    intermediate=[estado],
                )

            if not estado.get("producto_existe"):
                productos = estado.get("productos", [])
                productos_str = "\n".join([f"  • {p}" for p in productos])
                return self._resp(
                    True,
                    f"""❌ El producto "{product_id}" no está en el pedido {order_id}.

            Productos disponibles:
            {productos_str}

            ¿Cuál deseas devolver?""",
                                used_tools=["consultar_estado_pedido"],
                                intermediate=[estado],
                            )

            if not estado.get("fue_entregado"):
                return self._resp(
                    True,
                    f"""⏳ El pedido {order_id} está en estado: **{estado.get('estado_actual')}**

                    Para iniciar una devolución, el pedido debe estar entregado primero.

                    📅 Fecha estimada de entrega: {estado.get('fecha_estimada', 'No disponible')}

                    Una vez lo recibas, podrás solicitar la devolución dentro de los 30 días siguientes.""",
                                        used_tools=["consultar_estado_pedido"],
                                        intermediate=[estado],
                )

            # Paso 2: elegibilidad
            elegibilidad = verificar_elegibilidad_producto.invoke(
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "motivo_devolucion": "Solicitud del cliente",
                    "fecha_entrega": estado.get("fecha_entrega"),
                    "estado_producto": "sellado",
                }
            )

            if not elegibilidad.get("es_elegible"):
                pasos = elegibilidad.get("pasos_siguientes", [])
                pasos_str = "\n".join([f"• {p}" for p in pasos]) if pasos else ""
                return self._resp(
                    True,
                    f"""❌ **Devolución No Permitida**

            {elegibilidad.get('razon')}

            {pasos_str}""",
                    used_tools=["consultar_estado_pedido", "verificar_elegibilidad_producto"],
                    intermediate=[estado, elegibilidad],
                )

            # Paso 3: etiqueta
            etiqueta = generar_etiqueta_devolucion.invoke(
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "categoria_proceso": elegibilidad.get("categoria_proceso"),
                    "motivo_devolucion": "Solicitud del cliente",
                }
            )

            final_msg = f"""✅ **¡Devolución Aprobada!**

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

            return self._resp(
                True,
                final_msg,
                used_tools=[
                    "consultar_estado_pedido",
                    "verificar_elegibilidad_producto",
                    "generar_etiqueta_devolucion",
                ],
                intermediate=[estado, elegibilidad, etiqueta],
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return self._resp(False, f"❌ Error procesando la solicitud: {str(e)}")

    # ──────────────────────────────────────────────────────────────────────
    # 5. Orquestador público
    # ──────────────────────────────────────────────────────────────────────
    def run(self, query: str) -> Dict[str, Any]:
        self._log("\n" + "=" * 70)
        self._log(f"🔍 NUEVA QUERY: {query}")
        self._log("=" * 70)

        intencion = self._detectar_intencion(query)
        self._log(f"\n📊 DECISIÓN: {intencion.upper()}")
        self._log("=" * 70 + "\n")

        if intencion == INTENT_INFORMATIVA:
            answer = self._responder_informativa(query)
            return self._resp(True, answer)

        # intenciones operativas
        datos = self._extraer_datos_pedido(query)
        return self._flujo_devolucion(datos["order_id"], datos["product_id"])

    # ──────────────────────────────────────────────────────────────────────
    # 6. Utilidades de respuesta
    # ──────────────────────────────────────────────────────────────────────
    def _resp(
        self,
        success: bool,
        message: str,
        used_tools: Optional[List[str]] = None,
        intermediate: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "success": success,
            "response": message,
            "used_tools": used_tools or [],
            "intermediate_steps": intermediate or [],
        }

    def format_response(self, result: Dict[str, Any]) -> str:
        response = result.get("response", "")
        if not result.get("success", False):
            return f"❌ **Error**\n\n{response}\n\nPor favor intenta de nuevo o contacta a soporte."

        used_tools = result.get("used_tools", [])
        if used_tools:
            response += f"\n\n---\n🔧 *Acciones realizadas: {', '.join(used_tools)}*"
        return response


def create_agent() -> EcoMarketAgent:
    return EcoMarketAgent()
