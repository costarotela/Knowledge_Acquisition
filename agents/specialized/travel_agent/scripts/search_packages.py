import os
from dotenv import load_dotenv
from supabase import create_client, Client
import openai
from typing import List, Dict
import json
from datetime import datetime

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

def search_packages(query: str, limit: int = 5) -> List[Dict]:
    """Buscar paquetes usando similitud semántica."""
    load_dotenv()
    
    # Configurar clientes
    url = os.getenv("PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    if not all([url, key, openai.api_key]):
        print("❌ Error: Faltan variables de entorno")
        return []
    
    try:
        supabase: Client = create_client(url, key)
        
        # Obtener embedding de la consulta
        query_embedding = get_embedding(query)
        
        # Buscar paquetes similares usando una consulta directa
        result = supabase.table("travel_packages")\
            .select("*")\
            .execute()
            
        # Calcular similitud manualmente
        packages = []
        for package in result.data:
            if package.get("embedding"):
                # Convertir embedding a lista de flotantes si es necesario
                pkg_embedding = [float(x) for x in package["embedding"]]
                # Calcular similitud coseno
                dot_product = sum(a * b for a, b in zip(pkg_embedding, query_embedding))
                magnitude1 = sum(a * a for a in pkg_embedding) ** 0.5
                magnitude2 = sum(b * b for b in query_embedding) ** 0.5
                similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 0
                
                if similarity > 0.5:  # Umbral de similitud
                    package["similarity"] = similarity
                    packages.append(package)
        
        # Ordenar por similitud
        packages.sort(key=lambda x: x["similarity"], reverse=True)
        packages = packages[:limit]
        
        # Obtener historial de precios para cada paquete
        for package in packages:
            price_history = supabase.table("price_history")\
                .select("*")\
                .eq("package_id", package["id"])\
                .order("timestamp", desc=True)\
                .execute()
            
            package["price_history"] = price_history.data
        
        return packages
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def print_package(package: Dict):
    """Imprimir detalles del paquete de forma legible."""
    data = package["data"]
    print("\n" + "="*50)
    print(f"📍 {data['title']}")
    print(f"📝 {data['description']}")
    print(f"💰 {data['price']} {data['currency']}")
    print(f"📅 {data['duration']} días")
    print(f"🏨 {data['accommodation']['name']} ({data['accommodation']['rating']}⭐)")
    print("\n🎯 Actividades:")
    for activity in data['activities']:
        print(f"  • {activity}")
    print("\n💎 Servicios incluidos:")
    for service in data['included_services']:
        print(f"  • {service}")
    if package.get("price_history"):
        print("\n📊 Historial de precios:")
        for price in package["price_history"][:5]:
            date = datetime.fromisoformat(price["timestamp"]).strftime("%Y-%m-%d")
            print(f"  • {date}: {price['price']} {data['currency']}")
    print("="*50)

def main():
    """Función principal."""
    print("🔍 Buscador de Paquetes Turísticos")
    print("Ejemplos de búsqueda:")
    print("  • Vacaciones en la playa con actividades acuáticas")
    print("  • Viaje de aventura con deportes de invierno")
    print("  • Paquete todo incluido en resort de lujo")
    
    while True:
        query = input("\n🔎 Ingrese su búsqueda (o 'salir' para terminar): ")
        if query.lower() == "salir":
            break
            
        print("\n🔄 Buscando paquetes...")
        packages = search_packages(query)
        
        if not packages:
            print("❌ No se encontraron paquetes que coincidan con su búsqueda")
            continue
            
        print(f"✅ Se encontraron {len(packages)} paquetes:")
        for package in packages:
            print_package(package)

if __name__ == "__main__":
    main()
