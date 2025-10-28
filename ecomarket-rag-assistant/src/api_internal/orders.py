from fastapi import FastAPI, HTTPException

app = FastAPI()

# Ejemplo de endpoint simulado
@app.get("/internal/order/{tracking_number}")
def get_order(tracking_number: str):
    demo_data = {
        "20001": {
            "estado": "En tránsito",
            "transportadora": "DHL",
            "fecha_estimada": "2025-10-01",
            "destino": "Bogotá, Colombia",
            "enlace": "https://www.dhl.com/track?num=20001"
        }
    }
    if tracking_number not in demo_data:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return demo_data[tracking_number]
