"""
Herramientas del Agente Proactivo de Devoluciones - EcoMarket
Define las acciones externas que el agente puede ejecutar
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from langchain.tools import tool

# Cargar datos de pedidos
BASE = Path(__file__).resolve().parents[1]
PEDIDOS_PATH = BASE / "data" / "pedidos.json"

def _cargar_pedidos() -> list:
    """Carga los pedidos desde el archivo JSON"""
    try:
        with open(PEDIDOS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando pedidos: {e}")
        return []


@tool
def consultar_estado_pedido(order_id: str, product_id: str = None) -> Dict[str, Any]:
    """
    Verifica que el producto pertenece al pedido, fue entregado y no tiene devolución activa.
    
    Args:
        order_id: Número de seguimiento del pedido (ej: "20001")
        product_id: Nombre del producto (opcional, si no se especifica verifica todo el pedido)
    
    Returns:
        Dict con información del pedido y estado de elegibilidad
    """
    pedidos = _cargar_pedidos()
    
    # Buscar el pedido
    pedido = next((p for p in pedidos if p.get("tracking_number") == order_id), None)
    
    if not pedido:
        return {
            "existe": False,
            "error": f"No se encontró el pedido {order_id}",
            "fue_entregado": False,
            "devolucion_en_progreso": False
        }
    
    # Verificar si fue entregado
    fue_entregado = pedido.get("estado") == "Entregado"
    fecha_entrega = pedido.get("fecha_entrega_real", "")
    
    # Verificar si hay devolución en progreso (simulado - en producción sería una consulta a BD)
    devolucion_en_progreso = False  # Por ahora siempre False
    
    # Si se especificó un producto, verificar que existe en el pedido
    producto_existe = True
    if product_id:
        productos = pedido.get("productos", [])
        producto_existe = any(
            p.get("nombre", "").lower() == product_id.lower() 
            for p in productos
        )
    
    return {
        "existe": True,
        "producto_existe": producto_existe if product_id else True,
        "fue_entregado": fue_entregado,
        "fecha_entrega": fecha_entrega,
        "devolucion_en_progreso": devolucion_en_progreso,
        "estado_actual": pedido.get("estado"),
        "transportadora": pedido.get("transportadora"),
        "destino": pedido.get("destino"),
        "productos": [p.get("nombre") for p in pedido.get("productos", [])]
    }


@tool
def verificar_elegibilidad_producto(
    order_id: str,
    product_id: str,
    motivo_devolucion: str,
    fecha_entrega: str,
    estado_producto: str = "sellado"
) -> Dict[str, Any]:
    """
    Confirma si el producto cumple con las políticas de devolución de EcoMarket.
    
    Args:
        order_id: Número de seguimiento del pedido
        product_id: Nombre del producto
        motivo_devolucion: Razón de la devolución
        fecha_entrega: Fecha de entrega del pedido (formato YYYY-MM-DD)
        estado_producto: Estado del producto (sellado, abierto_pero_nuevo, usado, dañado_transporte)
    
    Returns:
        Dict con elegibilidad y detalles del proceso
    """
    pedidos = _cargar_pedidos()
    
    # Buscar el pedido y producto
    pedido = next((p for p in pedidos if p.get("tracking_number") == order_id), None)
    
    if not pedido:
        return {
            "es_elegible": False,
            "razon": f"Pedido {order_id} no encontrado",
            "categoria_proceso": None,
            "pasos_siguientes": []
        }
    
    # Buscar el producto específico
    productos = pedido.get("productos", [])
    producto = next(
        (p for p in productos if p.get("nombre", "").lower() == product_id.lower()),
        None
    )
    
    if not producto:
        return {
            "es_elegible": False,
            "razon": f"Producto '{product_id}' no encontrado en el pedido {order_id}",
            "categoria_proceso": None,
            "pasos_siguientes": []
        }
    
    # Verificar categoría del producto
    categoria = producto.get("categoria", "")
    dev_aceptada = producto.get("dev_aceptada", False)
    
    # Regla 1: Categorías no retornables
    categorias_no_retornables = ["Alimento perecedero", "Higiene", "Medicamentos"]
    if categoria in categorias_no_retornables or not dev_aceptada:
        return {
            "es_elegible": False,
            "razon": f"Los productos de categoría '{categoria}' no aceptan devoluciones por política de seguridad",
            "categoria_proceso": None,
            "pasos_siguientes": ["Contactar soporte para casos excepcionales"]
        }
    
    # Regla 2: Ventana de tiempo (30 días)
    try:
        fecha_entrega_dt = datetime.strptime(fecha_entrega, "%Y-%m-%d")
        fecha_actual = datetime.now()
        dias_transcurridos = (fecha_actual - fecha_entrega_dt).days
        
        if dias_transcurridos > 30:
            return {
                "es_elegible": False,
                "razon": f"Han transcurrido {dias_transcurridos} días desde la entrega. El plazo máximo es de 30 días",
                "categoria_proceso": None,
                "pasos_siguientes": []
            }
    except ValueError:
        return {
            "es_elegible": False,
            "razon": "Fecha de entrega inválida",
            "categoria_proceso": None,
            "pasos_siguientes": []
        }
    
    # Regla 3: Estado del producto
    estados_no_elegibles = ["usado"]
    if estado_producto in estados_no_elegibles:
        return {
            "es_elegible": False,
            "razon": f"Producto en estado '{estado_producto}' no es elegible para devolución",
            "categoria_proceso": None,
            "pasos_siguientes": []
        }
    
    # Determinar categoría de proceso
    if estado_producto == "dañado_transporte":
        categoria_proceso = "recoleccion_prioritaria"
        pasos = [
            "Un mensajero recogerá el producto en las próximas 24 horas",
            "No necesitas empacar el producto",
            "Recibirás reembolso completo en 3-5 días hábiles"
        ]
    else:
        categoria_proceso = "recoleccion_domicilio"
        pasos = [
            "Imprimir etiqueta de devolución",
            "Empacar el producto en su caja original",
            "Entregar paquete al mensajero",
            "Reembolso procesado al confirmar recepción (5-7 días hábiles)"
        ]
    
    return {
        "es_elegible": True,
        "razon": f"Producto dentro de ventana de 30 días y estado '{estado_producto}' aceptable",
        "categoria_proceso": categoria_proceso,
        "dias_restantes": 30 - dias_transcurridos,
        "pasos_siguientes": pasos,
        "motivo_registrado": motivo_devolucion
    }


@tool
def generar_etiqueta_devolucion(
    order_id: str,
    product_id: str,
    categoria_proceso: str,
    direccion_cliente: str = None,
    nombre_cliente: str = None,
    motivo_devolucion: str = None
) -> Dict[str, Any]:
    """
    Crea la etiqueta de devolución y el identificador del proceso logístico.
    
    Args:
        order_id: Número de seguimiento del pedido
        product_id: Nombre del producto
        categoria_proceso: Tipo de proceso (recoleccion_domicilio, recoleccion_prioritaria)
        direccion_cliente: Dirección del cliente (opcional)
        nombre_cliente: Nombre del cliente (opcional)
        motivo_devolucion: Motivo de la devolución (opcional)
    
    Returns:
        Dict con RMA, transportadora e instrucciones
    """
    pedidos = _cargar_pedidos()
    
    # Buscar el pedido para obtener datos del cliente
    pedido = next((p for p in pedidos if p.get("tracking_number") == order_id), None)
    
    if not pedido:
        return {
            "error": f"Pedido {order_id} no encontrado",
            "rma_id": None
        }
    
    # Generar RMA único
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rma_id = f"RMA-{datetime.now().year}-{timestamp[-6:]}"
    
    # Determinar transportadora (usar la misma del envío original)
    transportadora = pedido.get("transportadora", "EcoExpress")
    
    # Obtener datos del cliente si no se proporcionaron
    if not nombre_cliente:
        nombre_cliente = pedido.get("cliente", "Cliente EcoMarket")
    
    if not direccion_cliente:
        direccion_cliente = pedido.get("destino", "Dirección registrada")
    
    # Instrucciones según categoría
    if categoria_proceso == "recoleccion_prioritaria":
        tipo_envio = "recoleccion_prioritaria"
        instrucciones = (
            "Un mensajero de {transportadora} pasará en las próximas 24 horas. "
            "Ten el producto disponible tal como lo recibiste. "
            "El reembolso se procesará automáticamente."
        ).format(transportadora=transportadora)
    else:
        tipo_envio = "recoleccion_domicilio"
        instrucciones = (
            "1. Descarga e imprime la etiqueta adjunta\n"
            "2. Empaca el producto en su caja original con todos los accesorios\n"
            "3. Pega la etiqueta en el exterior del paquete\n"
            "4. Entrega el paquete al mensajero de {transportadora}\n"
            "5. Recibirás confirmación por email y el reembolso en 5-7 días hábiles"
        ).format(transportadora=transportadora)
    
    # URL simulada de la etiqueta
    etiqueta_url = f"https://ecomarket.dev/devoluciones/{rma_id}.pdf"
    
    return {
        "rma_id": rma_id,
        "transportadora": transportadora,
        "tipo_envio": tipo_envio,
        "instrucciones_cliente": instrucciones,
        "etiqueta_pdf_url": etiqueta_url,
        "fecha_generacion": datetime.now().isoformat(),
        "orden_original": order_id,
        "producto": product_id,
        "cliente": nombre_cliente,
        "direccion_recoleccion": direccion_cliente,
        "motivo": motivo_devolucion or "No especificado",
        "estado_rma": "Iniciado",
        "tiempo_estimado_recoleccion": "24-48 horas" if tipo_envio == "recoleccion_domicilio" else "24 horas"
    }


# Metadatos de las herramientas para el agente
TOOLS = [
    consultar_estado_pedido,
    verificar_elegibilidad_producto,
    generar_etiqueta_devolucion
]