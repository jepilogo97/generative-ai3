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
        
        # Crear el executor del agente
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=TOOLS,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def _create_agent_prompt(self) -> PromptTemplate:
        """Crea el prompt del agente siguiendo el formato ReAct"""
        
        template = """Eres un agente virtual de servicio al cliente de EcoMarket, especializado en seguimiento de pedidos y gestión de devoluciones.

Tu objetivo es ayudar a los clientes de manera proactiva y eficiente:

**CAPACIDADES:**
1. Consultar estado de pedidos en tiempo real
2. Verificar elegibilidad de productos para devolución
3. Generar etiquetas de devolución
4. Proporcionar información de políticas y procedimientos

**HERRAMIENTAS DISPONIBLES:**
{tools}

**NOMBRES DE HERRAMIENTAS:** {tool_names}

**PROTOCOLO DE DECISIÓN:**

Para cada consulta, sigue este proceso:

1. **ANALIZAR LA INTENCIÓN:**
   - ¿El cliente pregunta sobre el estado de un pedido?
   - ¿El cliente quiere devolver un producto?
   - ¿El cliente busca información general de políticas?

2. **DECIDIR EL ENFOQUE:**
   
   **CASO A - Seguimiento de pedido (consulta informativa):**
   - Si solo pregunta "¿dónde está mi pedido?" o "¿cuándo llega?"
   - NO uses herramientas
   - Responde directamente con la información del contexto RAG
   
   **CASO B - Solicitud de devolución (acción operativa):**
   - Si dice "quiero devolver", "iniciar devolución", "generar etiqueta"
   - DEBES usar las herramientas en este orden:
     1. consultar_estado_pedido - Verificar que el pedido existe y fue entregado
     2. verificar_elegibilidad_producto - Confirmar que cumple políticas
     3. generar_etiqueta_devolucion - Crear RMA y etiqueta
   
   **CASO C - Pregunta sobre políticas (consulta informativa):**
   - Si pregunta "¿puedo devolver?", "¿cuál es la política?", "¿qué productos no se devuelven?"
   - NO uses herramientas
   - Responde con información del contexto RAG

3. **EJECUTAR Y RESPONDER:**
   - Si usas herramientas, explica cada paso al cliente
   - Maneja errores con empatía
   - Formatea la respuesta final de manera clara y amigable

**CONTEXTO RAG (políticas y datos generales):**
{context}

**FORMATO DE USO DE HERRAMIENTAS:**

Thought: [Analiza qué necesitas hacer]
Action: [nombre_herramienta]
Action Input: {{"parametro": "valor"}}
Observation: [resultado de la herramienta]
... (repite Thought/Action/Observation según necesites)
Thought: Ahora sé la respuesta final
Final Answer: [Respuesta completa y amigable para el cliente]

**PREGUNTA DEL CLIENTE:**
{input}

**HISTORIAL DE ACCIONES:**
{agent_scratchpad}

Recuerda: Solo usa herramientas para ACCIONES OPERATIVAS (iniciar devolución, generar etiqueta). Para consultas informativas, responde directamente."""
        
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