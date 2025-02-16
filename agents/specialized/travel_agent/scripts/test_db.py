import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_connection():
    """Probar conexión a Supabase."""
    load_dotenv()
    
    url = os.getenv("PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("❌ Error: Faltan variables de entorno para Supabase")
        return False
    
    try:
        supabase: Client = create_client(url, key)
        
        # Probar una consulta simple
        result = supabase.table("travel_packages").select("*").limit(1).execute()
        
        print("✅ Conexión exitosa a Supabase!")
        print(f"URL: {url}")
        return True
        
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
