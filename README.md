# generative-ai3
Proyecto Final: Implementación de un Agente de IA para Automatización de Tareas


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


