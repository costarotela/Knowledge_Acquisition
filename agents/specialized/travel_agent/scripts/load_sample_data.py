import os
from datetime import datetime, timedelta
from decimal import Decimal
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import openai
from typing import List, Dict

# Datos de ejemplo
SAMPLE_PACKAGES = [
    {
        "title": "Aventura en Bariloche",
        "description": "Paquete de ski y aventura en Bariloche con alojamiento en hotel 4 estrellas",
        "destination": "Bariloche, Argentina",
        "price": 2500.00,
        "currency": "USD",
        "duration": 7,
        "start_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "end_date": (datetime.now() + timedelta(days=37)).isoformat(),
        "provider": "Despegar",
        "url": "https://www.despegar.com.ar/paquetes/bariloche-ski",
        "accommodation": {
            "name": "Hotel Alma del Lago",
            "type": "Hotel",
            "rating": 4.5,
            "amenities": ["Piscina", "Spa", "Restaurant", "WiFi", "Ski storage"],
            "room_types": ["Standard", "Suite", "Family"],
            "location": {"lat": -41.1335, "lon": -71.3103}
        },
        "activities": [
            "Clase de ski",
            "Excursión Cerro Catedral",
            "Tour Circuito Chico",
            "Navegación Lago Nahuel Huapi"
        ],
        "included_services": [
            "Vuelos ida y vuelta",
            "Traslados",
            "Alojamiento",
            "Desayuno",
            "Pase de ski 5 días",
            "Equipamiento completo de ski"
        ]
    },
    {
        "title": "Playas de Cancún All Inclusive",
        "description": "Vacaciones todo incluido en las mejores playas de Cancún",
        "destination": "Cancún, México",
        "price": 3200.00,
        "currency": "USD",
        "duration": 10,
        "start_date": (datetime.now() + timedelta(days=45)).isoformat(),
        "end_date": (datetime.now() + timedelta(days=55)).isoformat(),
        "provider": "Aero",
        "url": "https://www.aero.com.ar/paquetes/cancun-all-inclusive",
        "accommodation": {
            "name": "Hard Rock Hotel Cancún",
            "type": "Resort",
            "rating": 4.8,
            "amenities": ["Playa privada", "Piscinas", "Spa", "Gimnasio", "Restaurantes"],
            "room_types": ["Deluxe", "Diamond", "Rock Suite"],
            "location": {"lat": 21.1289, "lon": -86.7365}
        },
        "activities": [
            "Snorkel en arrecifes",
            "Tour a Chichén Itzá",
            "Fiesta en barco",
            "Nado con delfines"
        ],
        "included_services": [
            "Vuelos ida y vuelta",
            "Traslados",
            "All inclusive premium",
            "Acceso a todas las instalaciones",
            "Shows nocturnos",
            "Actividades deportivas"
        ]
    }
]

def get_embedding(text: str) -> List[float]:
    """Obtener embedding usando OpenAI."""
    client = openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def prepare_package_data(package: Dict) -> Dict:
    """Preparar datos del paquete para inserción."""
    # Crear texto para embedding
    embedding_text = f"{package['title']} {package['description']} {package['destination']} "
    embedding_text += f"Actividades: {', '.join(package['activities'])} "
    embedding_text += f"Servicios: {', '.join(package['included_services'])}"
    
    embedding = get_embedding(embedding_text)
    
    return {
        "data": package,
        "embedding": embedding  # OpenAI ya devuelve una lista de flotantes
    }

def load_sample_data():
    """Cargar datos de ejemplo en Supabase."""
    load_dotenv()
    
    # Configurar clientes
    url = os.getenv("PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    if not all([url, key, openai.api_key]):
        print("❌ Error: Faltan variables de entorno")
        return
    
    try:
        supabase: Client = create_client(url, key)
        
        # Insertar paquetes
        for package in SAMPLE_PACKAGES:
            data = prepare_package_data(package)
            
            # Insertar en Supabase
            result = supabase.table("travel_packages").insert(data).execute()
            
            # Crear historial de precios simulado
            package_id = result.data[0]["id"]
            base_price = Decimal(str(package["price"]))
            
            # Generar 10 precios históricos
            for i in range(10):
                days_ago = 10 - i
                # Simular variación de precio (-5% a +5%)
                variation = Decimal(str(0.95 + (i * 0.01)))
                historic_price = base_price * variation
                
                price_data = {
                    "package_id": package_id,
                    "price": float(historic_price),
                    "timestamp": (datetime.now() - timedelta(days=days_ago)).isoformat()
                }
                
                supabase.table("price_history").insert(price_data).execute()
            
            print(f"✅ Insertado: {package['title']}")
            
        print("✅ Datos de ejemplo cargados correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    load_sample_data()
