# Proyecto Final: Implementación de un Agente de IA para Automatización de Tareas


## 🧠 Fase 1: Diseño de la Arquitectura del Agente

El objetivo de esta fase es diseñar la arquitectura del **Agente Proactivo de Devoluciones** de EcoMarket, responsable de automatizar el proceso de verificación de elegibilidad y generación de etiqueta de devolución.

---

### 🧩 1️⃣ Definición de las Herramientas (Tools)

Las herramientas representan las acciones externas que el agente puede ejecutar.  
Para el flujo de devoluciones, se definieron tres herramientas principales:

#### 🛠 `consultar_estado_pedido`
**Propósito:** Verificar que el producto pertenece al pedido, fue entregado y no tiene una devolución activa.

**Entradas:**
- `order_id`
- `product_id`

**Salida ejemplo:**
```json
{
  "existe": true,
  "fue_entregado": true,
  "fecha_entrega": "2025-10-20",
  "devolucion_en_progreso": false
}
```

---

#### 🛠 `verificar_elegibilidad_producto`
**Propósito:** Confirmar si el producto cumple con las políticas de devolución de EcoMarket.

**Entradas:**
- `order_id`
- `product_id`
- `motivo_devolucion`
- `fecha_entrega`
- `fecha_solicitud`
- `estado_producto` (`sellado`, `abierto_pero_nuevo`, `usado`, `dañado_transporte`)

**Salida ejemplo:**
```json
{
  "es_elegible": true,
  "razon": "Producto dentro de ventana de 30 días y estado sellado.",
  "categoria_proceso": "recoleccion_domicilio",
  "pasos_siguientes": ["Imprimir etiqueta", "Entregar paquete al mensajero"]
}
```

---

#### 🛠 `generar_etiqueta_devolucion`
**Propósito:** Crear la etiqueta de devolución y el identificador del proceso logístico.

**Entradas:**
- `order_id`
- `product_id`
- `categoria_proceso`
- `direccion_cliente`
- `nombre_cliente`
- `motivo_devolucion`

**Salida ejemplo:**
```json
{
  "rma_id": "RMA-2025-000982",
  "transportadora": "EcoExpress",
  "tipo_envio": "recoleccion_domicilio",
  "instrucciones_cliente": "Empaca el producto y entrégalo al mensajero.",
  "etiqueta_pdf_url": "https://ecomarket.dev/devoluciones/RMA-2025-000982.pdf"
}
```

---

#### 🧾 Resumen general de herramientas

| Herramienta                       | Función principal                                   | Cuándo se ejecuta               |
|----------------------------------|-----------------------------------------------------|--------------------------------|
| `consultar_estado_pedido`        | Validar existencia y entrega del producto           | Antes del proceso               |
| `verificar_elegibilidad_producto`| Evaluar cumplimiento de políticas de devolución     | Tras validación del pedido      |
| `generar_etiqueta_devolucion`    | Emitir RMA y etiqueta logística                     | Si el producto es elegible      |

---

### 🧱 2️⃣ Selección del Marco de Agentes

Se compararon dos frameworks principales:

| Marco | Ventajas | Desventajas |
|-------|-----------|-------------|
| **LangChain** ✅ | - Integración directa con FAISS, Ollama y herramientas personalizadas.<br>- Mecanismo nativo de “tool calling”.<br>- Ideal para entornos Dockerizados y RAG. | Requiere control cuidadoso del flujo. |
| **LlamaIndex** | - Gestión avanzada de nodos y fuentes.<br>- Buena trazabilidad de contexto. | Menos intuitivo para agentes con herramientas externas. |

📊 **Decisión:**  
Se selecciona **LangChain** por su **flexibilidad, compatibilidad con el stack existente** (FAISS + Ollama) y facilidad para definir herramientas y flujos tipo “consulta → decisión → acción”.

---

### 🔁 3️⃣ Planificación del Flujo de Trabajo

El agente debe seguir una secuencia lógica que combine razonamiento con acciones automatizadas.

#### 🧩 Flujo paso a paso:

1. **Recepción de solicitud del cliente:**  
   Ejemplo: “Quiero devolver este producto, llegó roto.”

2. **Verificación de pedido:**  
   - El agente llama `consultar_estado_pedido`.  
   - Si el pedido no existe o no fue entregado → se informa y termina el flujo.  
   - Si ya hay devolución activa → se informa el estado actual.

3. **Evaluación de elegibilidad:**  
   - El agente llama `verificar_elegibilidad_producto`.  
   - Si no cumple las políticas → se explica el motivo y se termina el flujo.  
   - Si es elegible → pasa al siguiente paso.

4. **Generación de etiqueta:**  
   - Llama `generar_etiqueta_devolucion`.  
   - Obtiene número de caso (`rma_id`), instrucciones y URL del PDF.

5. **Respuesta final al cliente:**  
   El agente genera una respuesta clara y empática, por ejemplo:  
   > “Tu devolución fue aprobada ✅.  
   > Este es tu número de caso: RMA-2025-000982.  
   > El mensajero pasará mañana. Aquí tienes tu etiqueta: [Descargar PDF].”

---

#### 🧭 Diagrama lógico del flujo

```text
[Cliente solicita devolución]
        |
        v
[consultar_estado_pedido]
   ├─ no existe / no entregado → informar y cerrar
   └─ válido → continuar
        |
        v
[verificar_elegibilidad_producto]
   ├─ no elegible → explicar motivo y cerrar
   └─ elegible → continuar
        |
        v
[generar_etiqueta_devolucion]
        |
        v
[Respuesta final: RMA + etiqueta + instrucciones]
```

---

### 🎯 Resultado esperado

- El asistente deja de ser informativo y se convierte en **operativo**.  
- Cada paso está sustentado por una **herramienta auditable**, no por inferencia libre del modelo.  
- La arquitectura permite migrar fácilmente a un entorno **microservicios**, manteniendo control, trazabilidad y cumplimiento de políticas.

📘 **En resumen:**  
La Fase 1 define un **agente modular**, gobernado por LangChain, con herramientas estructuradas para verificar elegibilidad y generar etiquetas de devolución, garantizando precisión, transparencia y autonomía en la atención al cliente.



## 📘 Fase 2: Implementación y Conexión de Componentes

### 🎯 Objetivo

Implementar el **Agente Proactivo de Devoluciones** de EcoMarket, integrando las herramientas definidas en la Fase 1 con el sistema RAG existente del Taller 2.

---

## 🏗️ Arquitectura Implementada

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                   INTERFAZ STREAMLIT                        │
│                    (streamlit_app.py)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  AGENTE PROACTIVO                           │
│                     (agent.py)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   LLM        │  │    RAG       │  │  Herramientas    │  │
│  │  (Llama 3)   │  │   (FAISS)    │  │  (agent_tools)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    HERRAMIENTAS                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. consultar_estado_pedido                           │  │
│  │ 2. verificar_elegibilidad_producto                   │  │
│  │ 3. generar_etiqueta_devolucion                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FUENTES DE DATOS                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ pedidos.json │  │  faqs.json   │  │  politicas.pdf   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Estructura del Proyecto

```bash
ecomarket-rag-assistant/
├── 📄 Dockerfile                # Imagen base Python 3.11 con dependencias
├── 📦 docker-compose.yml        # Orquestación: app + Ollama
├── 📦 requirements.txt          # Dependencias Python (LangChain, FAISS, Streamlit)
├── 🧮 test_agent.py             # Suite de pruebas
├── 📘 README.md                 # Documentación principal del proyecto
├── 🧾 Makefile                  # Comandos automáticos para build, up, ingest, etc.
├── 🔒 .env.example              # Variables de entorno de ejemplo
├── 🐳 .dockerignore             # Archivos excluidos del build
├── 🧹 .gitignore                # Archivos ignorados por Git
│
├── 📁 data/
│   ├── 📄 pedidos.json               # Dataset demo con 30 pedidos
│   └── 📄 politicas_devolucion.pdf   # Políticas oficiales 
│
├── 📁 artifacts/
│   ├── 📁 faiss_index/          # Índice FAISS generado
│   │   ├── index.faiss
│   │   └── index.pkl
│   └── 📄 meta.jsonl            # Metadatos de los chunks
│
└── 📁 src/
    ├── 🧮 ingest_data.py        # Pipeline: genera embeddings e índice FAISS
    ├── 💬 streamlit_app.py      # Interfaz de chat interactiva
    ├── 💬 agent.py              # Lógica del agente
    ├── 💬 agent_tools.py        # Definición de herramientas
    └── ⚙️ settings.toml         # Configuración de prompts y modelos
```

---

## 🔧 Implementación Detallada

### 1. **Herramientas del Agente** (`src/agent_tools.py`)

Implementa tres herramientas principales usando el decorador `@tool` de LangChain:

#### **Herramienta 1: `consultar_estado_pedido`**
```python
@tool
def consultar_estado_pedido(order_id: str, product_id: str = None):
    """Verifica que el pedido existe, fue entregado y no tiene devolución activa"""
```

**Entradas:**
- `order_id`: Número de seguimiento (ej: "20001")
- `product_id`: Nombre del producto (opcional)

**Salida:**
```json
{
  "existe": true,
  "fue_entregado": true,
  "fecha_entrega": "2025-09-20",
  "devolucion_en_progreso": false,
  "estado_actual": "Entregado",
  "productos": ["Perfume floral"]
}
```

---

#### **Herramienta 2: `verificar_elegibilidad_producto`**
```python
@tool
def verificar_elegibilidad_producto(
    order_id, product_id, motivo_devolucion, 
    fecha_entrega, estado_producto="sellado"
):
    """Confirma si el producto cumple con las políticas de devolución"""
```

**Validaciones implementadas:**
1. ✅ **Categorías no retornables**: Alimento perecedero, Higiene, Medicamentos
2. ✅ **Ventana de tiempo**: Máximo 30 días desde la entrega
3. ✅ **Estado del producto**: Rechaza productos "usados"
4. ✅ **Categorización del proceso**: 
   - `recoleccion_prioritaria` (productos dañados en transporte)
   - `recoleccion_domicilio` (devoluciones estándar)

**Salida:**
```json
{
  "es_elegible": true,
  "razon": "Producto dentro de ventana de 30 días y estado sellado",
  "categoria_proceso": "recoleccion_domicilio",
  "dias_restantes": 25,
  "pasos_siguientes": [
    "Imprimir etiqueta de devolución",
    "Empacar el producto en su caja original",
    "Entregar paquete al mensajero"
  ]
}
```

---

#### **Herramienta 3: `generar_etiqueta_devolucion`**
```python
@tool
def generar_etiqueta_devolucion(
    order_id, product_id, categoria_proceso,
    direccion_cliente=None, nombre_cliente=None, motivo_devolucion=None
):
    """Crea la etiqueta de devolución y el identificador RMA"""
```

**Salida:**
```json
{
  "rma_id": "RMA-2025-000982",
  "transportadora": "FedEx",
  "tipo_envio": "recoleccion_domicilio",
  "instrucciones_cliente": "1. Descarga e imprime la etiqueta...",
  "etiqueta_pdf_url": "https://ecomarket.dev/devoluciones/RMA-2025-000982.pdf",
  "tiempo_estimado_recoleccion": "24-48 horas"
}
```

---

### 2. **Lógica del Agente** (`src/agent.py`)

Implementa el agente usando el patrón **ReAct** (Reason + Act) de LangChain.

#### **Clase Principal: `EcoMarketAgent`**

```python
class EcoMarketAgent:
    def __init__(self):
        # Inicializa LLM, RAG y herramientas
        
    def run(self, query: str) -> Dict[str, Any]:
        # Ejecuta el agente con razonamiento
        
    def format_response(self, result: Dict) -> str:
        # Formatea la respuesta para el usuario
```

#### **Protocolo de Decisión**

El agente implementa un protocolo inteligente para decidir cuándo usar herramientas:

**CASO A - Consulta Informativa:**
- Pregunta: "¿Cuál es el plazo para devolver?"
- Acción: Responde directamente con información del RAG
- Herramientas usadas: Ninguna

**CASO B - Acción Operativa:**
- Pregunta: "Quiero devolver el producto del pedido 20001"
- Acción: Ejecuta secuencia de herramientas
- Herramientas usadas: `consultar_estado_pedido` → `verificar_elegibilidad_producto` → `generar_etiqueta_devolucion`

**CASO C - Consulta sobre Políticas:**
- Pregunta: "¿Puedo devolver alimentos perecederos?"
- Acción: Responde con información del RAG
- Herramientas usadas: Ninguna

---

### 3. **Integración con Streamlit** (`src/streamlit_app.py`)

#### **Inicialización del Agente**
```python
if 'agent' not in st.session_state:
    st.session_state.agent = create_agent()
```

#### **Flujo de Interacción**
1. Usuario escribe consulta
2. Se guarda en historial (SQLite)
3. Agente procesa la consulta
4. Se formatea y muestra la respuesta
5. Se guardan metadatos de ejecución

#### **Interfaz Mejorada**
- **Tabs**: Chat | Información
- **Modo selector**: Agente Proactivo vs Solo Consulta
- **Debug expandible**: Muestra herramientas usadas
- **Métricas**: Estado del agente en tiempo real

---

## 🧪 Suite de Pruebas (`test_agent.py`)

### Categorías de Pruebas

#### **1. Pruebas de Herramientas** (6 tests)
- ✅ Consultar pedido existente
- ✅ Consultar pedido entregado
- ✅ Consultar pedido inexistente
- ✅ Verificar producto no retornable
- ✅ Verificar producto retornable
- ✅ Generar etiqueta de devolución

#### **2. Pruebas de Escenarios** (5 tests)
- ✅ Consulta informativa (no debe usar herramientas)
- ✅ Consulta de seguimiento (no debe usar herramientas)
- ✅ Solicitud de devolución (DEBE usar herramientas)
- ✅ Producto no retornable (debe rechazar)
- ✅ Pedido no entregado (debe detectar)

#### **3. Pruebas de Razonamiento** (3 tests)
- ✅ Ambigüedad: distinguir consulta vs acción
- ✅ Acción explícita con palabras clave
- ✅ Consulta general de políticas

---

## 🚀 Instrucciones de Uso

### Opción 1: Docker

```bash
# 1. Construir imagen
make build

# 2. Levantar servicios
make up

# 3. Ejecutar pruebas del agente
make test-agent

# 4. Acceder a la aplicación
# http://localhost:8501
```

### Opción 2: Local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Inicializar base de datos
python init_db.py

# 3. Generar índice FAISS
python src/ingest_data.py

# 4. Ejecutar pruebas
python test_agent.py

# 5. Iniciar aplicación
streamlit run src/streamlit_app.py
```

---

## 🎨 Ejemplos de Prompts por Categoría

### 1. Consultas Informativas (No usan herramientas)

| Prompt | Comportamiento Esperado |
|--------|------------------------|
| "¿Cuál es el plazo para devolver?" | Responde con política de 30 días |
| "¿Qué productos no se pueden devolver?" | Lista categorías no retornables |
| "¿Cómo funciona el proceso de devolución?" | Explica pasos del proceso |
| "¿Dónde está mi pedido 20001?" | Informa estado desde RAG |

### 2. Acciones Operativas (Usan herramientas)

| Prompt | Herramientas Usadas |
|--------|---------------------|
| "Quiero devolver el producto X del pedido Y" | consultar_estado → verificar_elegibilidad → generar_etiqueta |
| "Iniciar devolución del pedido 20007" | consultar_estado → verificar_elegibilidad → generar_etiqueta |
| "Generar etiqueta de devolución para pedido Z" | consultar_estado → verificar_elegibilidad → generar_etiqueta |

### 3. Casos Ambiguos (Razonamiento)

| Prompt | Razonamiento del Agente |
|--------|------------------------|
| "¿Puedo devolver el producto del pedido 20007?" | Interpreta como consulta → No usa herramientas |
| "¿El pedido 20001 fue entregado?" | Consulta informativa → Responde desde RAG |
| "Devolver producto" (sin detalles) | Solicita aclaración |

--
## 🎓 Conclusión

La Fase 2 logra exitosamente:

✅ **Integración completa** del agente con el sistema RAG existente  
✅ **Implementación robusta** de tres herramientas operativas  
✅ **Protocolo de decisión inteligente** que distingue consultas de acciones  
✅ **Manejo de errores** con respuestas empáticas  
✅ **Suite de pruebas completa** con cobertura de casos edge  
✅ **Documentación exhaustiva** para mantenimiento y extensión  

---


## Fase 3: Análisis Crítico y Propuestas de Mejora

En esta fase se realiza un análisis reflexivo sobre las implicaciones éticas, técnicas y operativas del agente de IA desarrollado para EcoMarket, así como propuestas para su monitoreo y evolución.

---

### 🧠 Análisis de Seguridad y Ética

### 1. Riesgos éticos identificados
El agente propuesto tiene la capacidad de **tomar acciones automatizadas**, como aprobar devoluciones o generar etiquetas de envío. Esto introduce riesgos éticos y de seguridad que deben abordarse:

- **Decisiones sin supervisión humana:** si el modelo comete un error (por ejemplo, aprueba una devolución fraudulenta), puede generar pérdidas económicas o daño reputacional.
- **Privacidad de los datos:** el agente accede a información sensible de pedidos y clientes. Debe evitar exponer datos personales en respuestas generadas.
- **Sesgos en decisiones:** si los datos de entrenamiento contienen sesgos, el agente podría favorecer o penalizar ciertos perfiles de usuarios injustamente.
- **Uso indebido del sistema:** actores malintencionados podrían intentar manipular el flujo del agente para ejecutar acciones indebidas.

### 2. Estrategias de mitigación
Para reducir estos riesgos se proponen las siguientes medidas:

| Riesgo | Mitigación | Nivel de prioridad |
|--------|-------------|--------------------|
| Decisiones autónomas erróneas | Mantener un flujo de **revisión humana** en casos críticos (montos altos o usuarios reincidentes). | Alta |
| Filtración de información | Implementar **sanitización de entradas** y anonimización de respuestas. | Alta |
| Sesgos en los datos | Auditar y reentrenar periódicamente con datos balanceados. | Media |
| Manipulación externa | Aplicar validaciones de entrada y **restricciones de contexto** para evitar ejecución de comandos no autorizados. | Alta |

Además, se debe mantener un **código de conducta para agentes de IA**, basado en los principios de transparencia, equidad, privacidad y responsabilidad.

---

## 📈 Monitoreo y Observabilidad

Para garantizar que el agente funcione correctamente y no genere acciones no deseadas, se propone implementar un **sistema integral de monitoreo**.

### 1. Registro de acciones (Audit Log)
Cada interacción debe registrarse con metadatos clave:
- ID del usuario
- Acción ejecutada (ej. `verificar_elegibilidad_producto`, `generar_etiqueta_devolucion`)
- Fecha y hora
- Resultado (éxito, error, revisión manual)
- Contexto de decisión (fragmentos RAG o input original)

Este registro permitirá **trazar decisiones** y realizar auditorías ante cualquier incidencia.

### 2. Sistema de alertas y métricas
Propuesta de observabilidad basada en tres capas:

| Capa | Descripción | Herramientas sugeridas |
|------|--------------|------------------------|
| **Aplicación (agente)** | Logs de ejecución, latencia, errores, número de acciones por hora. | Prometheus / Grafana |
| **Modelo (IA)** | Monitoreo de tokens, tiempos de inferencia y detección de anomalías en respuestas. | LangSmith / OpenTelemetry |
| **Negocio** | Métricas de impacto: tiempo promedio de resolución, tasa de aprobación de devoluciones, satisfacción del cliente. | Power BI / Streamlit Dashboard |

Un sistema de **alertas automáticas** notificará al equipo de soporte si se detecta:
- Repetición de errores en inferencia.
- Aumento anormal en devoluciones automáticas.
- Tiempos de respuesta excesivos.

---

## 🚀 Propuestas de Mejora

El agente desarrollado puede evolucionar hacia un ecosistema de **agentes colaborativos** dentro del entorno de atención al cliente. Algunas funcionalidades propuestas son:

### 1. Agente de reemplazo automático
Permitir que, tras verificar una devolución válida, el agente cree una **orden de reemplazo** automáticamente, consultando el stock y generando un nuevo pedido sin intervención humana.

### 2. Agente de actualización de CRM
Integrar el agente con el sistema CRM de EcoMarket para **actualizar datos del cliente**, como dirección, contacto o historial de interacciones, garantizando consistencia entre plataformas.

### 3. Agente de conciliación logística
Un agente que compare datos del sistema interno con información de transportadoras para detectar **paquetes retrasados o extraviados** y notificar automáticamente al cliente.

### 4. Agente supervisor
Un agente de nivel superior encargado de **monitorear las acciones de otros agentes**, detectando comportamientos anómalos o decisiones fuera de política.

### 5. Integración con canales omnicanal
Expansión del flujo conversacional a **WhatsApp, Telegram o correo electrónico**, permitiendo que los usuarios gestionen devoluciones o consultas desde cualquier canal de atención.

---

## 📘 Conclusión

El desarrollo del agente de devoluciones en EcoMarket es un avance significativo hacia la automatización inteligente, pero también implica nuevas responsabilidades éticas y técnicas.
La implementación de **monitoreo, auditoría y control de sesgos** es esencial para garantizar la confiabilidad del sistema.  
Finalmente, las **propuestas de mejora** orientadas a la colaboración entre agentes y la integración con otros sistemas consolidan una visión sostenible y escalable para la atención al cliente impulsada por IA.

---

## Fase 4: Implementación de la Interfaz de Usuario

En esta última fase se materializa la solución desarrollada, permitiendo la interacción directa entre el usuario final y el agente de IA de EcoMarket. La interfaz actúa como un puente entre el modelo, la base de conocimiento RAG y las herramientas de acción automatizada.

---

## 🧩 Selección de la Herramienta

### Herramienta elegida: **Streamlit**

### 🔍 Justificación:

1. **Facilidad de uso:** Streamlit permite construir aplicaciones web interactivas con pocas líneas de código en Python, sin necesidad de manejar frameworks front-end complejos.
2. **Integración directa con el flujo RAG:** Es altamente compatible con proyectos de IA y NLP que usan LangChain, FAISS y Ollama, ya que permite ejecutar procesos asincrónicos y mostrar resultados en tiempo real.
3. **Interfaz intuitiva y limpia:** Ofrece componentes visuales (campos de texto, botones, loaders, expanders) ideales para construir una experiencia de usuario fluida.
4. **Despliegue rápido:** La aplicación puede ejecutarse localmente o desplegarse fácilmente mediante Docker, manteniendo la portabilidad del proyecto.
5. **Compatibilidad con Docker y Makefile:** Streamlit se adapta perfectamente al entorno definido en el proyecto, integrándose con los comandos `make build`, `make up` y `make ingest`.

📊 **Alternativa considerada:** Gradio. Si bien Gradio es más rápido para prototipar interfaces de chat, se optó por Streamlit por su mayor capacidad de personalización visual y compatibilidad con scripts Python existentes.

---

## 💻 Implementación de la Interfaz

### Descripción general

La interfaz fue diseñada con un enfoque **minimalista y funcional**, priorizando la claridad de la conversación y la trazabilidad de las acciones del agente. 

La aplicación permite:
- Recibir un **prompt del usuario** relacionado con devoluciones o estado de pedidos.
- Consultar la base de conocimiento vectorial (FAISS) para recuperar el contexto relevante.
- Generar una **respuesta explicativa y empática** usando el modelo Llama 3 vía Ollama.

## 🔄 Demostración Funcional

### Flujo completo de interacción

1. **Entrada del usuario:** El cliente escribe una solicitud (por ejemplo, *“¿Puedo devolver un producto usado?”*).
2. **Procesamiento del agente:**
   - El texto se convierte en embedding mediante *MiniLM-L12-v2*.
   - Se consulta la base FAISS para obtener fragmentos relevantes de políticas o FAQ.
   - Llama 3 genera una respuesta contextualizada y empática.
3. **Respuesta visual:** El resultado se muestra en la interfaz Streamlit, acompañado de indicadores visuales (emoji, color, o loader).

### Ejemplo de interacción

**Entrada:**
> "Compré un producto defectuoso hace 20 días, ¿puedo devolverlo?"

**Respuesta del agente:**
> "Sí, EcoMarket permite devoluciones hasta 30 días después de la compra. Para generar tu etiqueta de envío, ingresa el número de pedido y sigue las instrucciones del correo de confirmación."

### Evidencia de demostración
- Flujo de extremo a extremo validado con `make first-run` y `make ingest`.
- Comunicación correcta entre el front-end Streamlit, el backend de agente (LangChain + Ollama) y la base de conocimiento FAISS.
- Respuestas generadas con contexto actualizado y tono coherente con la atención al cliente.

---

## 🧩 Conclusión

Esta fase consolida el proyecto al convertir el sistema RAG en una herramienta tangible y accesible.  
La interfaz Streamlit no solo permite probar la funcionalidad del agente, sino que también ofrece una experiencia de usuario clara, empática y visualmente atractiva.  
Con esta implementación, EcoMarket cuenta con un **asistente inteligente funcional**, listo para ser desplegado en entornos reales o extendido con nuevas capacidades.