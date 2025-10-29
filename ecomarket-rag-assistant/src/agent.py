"""
Agente Proactivo de Devoluciones - EcoMarket
Implementa el agente usando LangChain con capacidad de razonamiento y uso de herramientas
"""

import os
from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatOllama
from langchain.prompts import PromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from pathlib import Path
import tomllib

# Importar las herramientas
from agent_tools import TOOLS

# Configuración de rutas
BASE = Path(__file__).resolve().parents[1]
SETTINGS = BASE / "src" / "settings.toml"
ARTIFACTS = BASE / "artifacts" / "faiss_index"

# Cargar configuración
with open(SETTINGS, "rb") as f:
    cfg = tomllib.load(f)


class EcoMarketAgent:
    """
    Agente proactivo que maneja consultas de seguimiento y devoluciones.
    Combina RAG para consultas informativas y herramientas para acciones operativas.
    """
    
    def __init__(self):
        """Inicializa el agente con LLM, herramientas y RAG"""
        
        # Configurar LLM con parámetros optimizados para velocidad
        self.llm = ChatOllama(
            model=cfg["model"]["name"],
            temperature=0.2,
            num_ctx=2048,      # ⬇️ Reducido de 4096 (menos memoria, más rápido)
            num_batch=128,     # ⬆️ Aumentado para procesamiento paralelo
            num_thread=4,      # Usar múltiples hilos
            repeat_penalty=1.1,
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        )
        
        # Configurar embeddings y retriever para RAG
        emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        db = FAISS.load_local(str(ARTIFACTS), emb, allow_dangerous_deserialization=True)
        self.retriever = db.as_retriever(search_kwargs={"k": 3})
        
        # Crear el prompt del agente con formato ReAct
        self.prompt = self._create_agent_prompt()
        
        # Crear el agente
        self.agent = create_react_agent(
            llm=self.llm,
            tools=TOOLS,
            prompt=self.prompt
        )
        
        # Crear el executor del agente con límites más estrictos
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=TOOLS,
            verbose=True,
            max_iterations=3,  # ✅ Reducido de 5 a 3 para evitar bucles
            handle_parsing_errors=True,
            return_intermediate_steps=True
            # Removido early_stopping_method (no compatible con todas las versiones)
        )
    
    def _create_agent_prompt(self) -> PromptTemplate:
        """Crea el prompt del agente siguiendo el formato ReAct"""
        
        template = """Eres un agente virtual de servicio al cliente de EcoMarket, especializado en seguimiento de pedidos y gestión de devoluciones.

⚠️ REGLA CRÍTICA: SOLO usa información que provenga de pedidos.json o del contexto RAG. NUNCA inventes datos.

**FUENTE DE VERDAD:**
- Todos los datos de pedidos están en el archivo pedidos.json
- Cada pedido tiene: tracking_number, estado, fecha_estimada, destino, transportadora, cliente, productos
- Cada producto tiene: nombre, categoria, dev_aceptada (true/false)
- SOLO estos datos existen - no asumas ni inventes nada más

**REGLA FUNDAMENTAL DE USO DE HERRAMIENTAS:**
🚫 NUNCA uses herramientas si falta order_id O product_id
✅ SOLO usa herramientas cuando tengas AMBOS datos explícitamente

Tu objetivo es ayudar a los clientes de manera proactiva y eficiente:

**CAPACIDADES:**
1. Consultar estado de pedidos en tiempo real (desde pedidos.json)
2. Verificar elegibilidad de productos para devolución (basado en dev_aceptada del JSON)
3. Generar etiquetas de devolución (solo si el producto existe y es elegible)
4. Proporcionar información de políticas y procedimientos

**HERRAMIENTAS DISPONIBLES:**
{tools}

**NOMBRES DE HERRAMIENTAS:** {tool_names}

**PROTOCOLO DE DECISIÓN - SIGUE ESTO ESTRICTAMENTE:**

PASO 1: ANALIZAR LA CONSULTA
- ¿Menciona un número de pedido específico? (ej: 20001, 20007)
- ¿Menciona un producto específico? (ej: "Auriculares Bluetooth", "Juego de cubiertos")

PASO 2: DECIDIR ACCIÓN
┌─────────────────────────────────────────────────────────────┐
│ SI falta order_id O product_id → NO USAR HERRAMIENTAS      │
│ Ir directo a Final Answer solicitando los datos faltantes  │
└─────────────────────────────────────────────────────────────┘

PASO 3: SOLO SI TIENES AMBOS DATOS → USAR HERRAMIENTAS
1. consultar_estado_pedido → verificar existencia
2. verificar_elegibilidad_producto → validar política  
3. generar_etiqueta_devolucion → crear RMA

**EJEMPLOS DE ANÁLISIS:**

┌─────────────────────────────────────────────────────────────┐
│ EJEMPLO 1: SIN DATOS SUFICIENTES                           │
└─────────────────────────────────────────────────────────────┘
Input: "quiero devolver mi pedido"
Thought: La consulta NO incluye order_id ni product_id. NO puedo usar herramientas.
Final Answer: Para ayudarte con la devolución, necesito:
- Número de pedido (ejemplo: 20001)
- Nombre del producto que deseas devolver

¿Me proporcionas esta información?

┌─────────────────────────────────────────────────────────────┐
│ EJEMPLO 2: SOLO PREGUNTA GENERAL                           │
└─────────────────────────────────────────────────────────────┘
Input: "¿cómo funciona la devolución?"
Thought: Pregunta informativa general, NO usar herramientas.
Final Answer: Las devoluciones en EcoMarket funcionan así:
1. Tienes 30 días desde la entrega
2. El producto debe estar en su empaque original
3. Algunos productos no aceptan devolución (alimentos perecederos, higiene)

Para iniciar una devolución específica, necesito tu número de pedido.

┌─────────────────────────────────────────────────────────────┐
│ EJEMPLO 3: CON DATOS COMPLETOS - USAR HERRAMIENTAS         │
└─────────────────────────────────────────────────────────────┘
Input: "Quiero devolver el Juego de cubiertos del pedido 20007"
Thought: Tengo order_id=20007 y product_id="Juego de cubiertos". Puedo usar herramientas.
Action: consultar_estado_pedido
Action Input: {{"order_id": "20007", "product_id": "Juego de cubiertos"}}
Observation: {{"existe": true, "fue_entregado": true, ...}}
Thought: Pedido existe y fue entregado, verificar elegibilidad.
Action: verificar_elegibilidad_producto
Action Input: {{"order_id": "20007", "product_id": "Juego de cubiertos", ...}}
[... continúa con las herramientas ...]

**VALIDACIÓN DE DATOS:**
- Nombres de productos deben ser EXACTOS
- Tracking numbers deben ser exactos
- Si falta información, SOLICÍTALA antes de usar herramientas

**CONTEXTO RAG (políticas y datos generales):**
{context}

**PREGUNTA DEL CLIENTE:**
{input}

**HISTORIAL DE ACCIONES:**
{agent_scratchpad}

Recuerda: 
🚫 NO usar herramientas sin order_id Y product_id
✅ Solicitar datos faltantes en Final Answer directamente"""
        
        return PromptTemplate(
            input_variables=["tools", "tool_names", "input", "agent_scratchpad", "context"],
            template=template
        )
    
    def _get_rag_context(self, query: str) -> str:
        """Obtiene contexto relevante del sistema RAG"""
        try:
            docs = self.retriever.get_relevant_documents(query)
            context = "\n\n".join([
                f"Fragmento {i+1}: {doc.page_content}"
                for i, doc in enumerate(docs)
            ])
            return context
        except Exception as e:
            print(f"Error obteniendo contexto RAG: {e}")
            return "No hay contexto adicional disponible."
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Ejecuta el agente con una consulta del usuario.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con la respuesta y metadatos del proceso
        """
        try:
            # Obtener contexto RAG
            context = self._get_rag_context(query)
            
            # Ejecutar el agente
            result = self.agent_executor.invoke({
                "input": query,
                "context": context
            })
            
            # Formatear respuesta
            response = {
                "success": True,
                "response": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "used_tools": [
                    step[0].tool for step in result.get("intermediate_steps", [])
                    if isinstance(step[0], AgentAction)
                ]
            }
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Disculpa, encontré un error procesando tu solicitud: {str(e)}",
                "error": str(e),
                "intermediate_steps": [],
                "used_tools": []
            }
    
    def format_response(self, result: Dict[str, Any]) -> str:
        """
        Formatea la respuesta del agente de manera amigable.
        
        Args:
            result: Resultado de la ejecución del agente
            
        Returns:
            Respuesta formateada para mostrar al usuario
        """
        response = result.get("response", "")
        
        # Si hubo error, mostrar mensaje amigable
        if not result.get("success", False):
            return f"""❌ **Disculpa, hubo un problema**

{response}

Por favor, intenta de nuevo o contacta a nuestro equipo de soporte."""
        
        # Si usó herramientas, agregar badge
        used_tools = result.get("used_tools", [])
        if used_tools:
            tools_str = ", ".join(used_tools)
            response += f"\n\n---\n🔧 *Acciones realizadas: {tools_str}*"
        
        return response


# Función helper para usar en la interfaz
def create_agent() -> EcoMarketAgent:
    """Crea y retorna una instancia del agente"""
    return EcoMarketAgent()