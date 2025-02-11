import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_supabase_connection():
    load_dotenv()
    
    # Obtener credenciales
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: No se encontraron las credenciales de Supabase en el archivo .env")
        return
    
    try:
        # Inicializar cliente
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Probar conexión
        response = supabase.auth.get_session()
        print("✅ Conexión exitosa con Supabase!")
        print(f"URL: {supabase_url}")
        
        # Verificar acceso a las tablas
        try:
            # Probar lectura de knowledge_items
            result = supabase.table('knowledge_items').select("*").limit(1).execute()
            print("✅ Tabla knowledge_items accesible!")
            print(f"Registros encontrados: {len(result.data)}")
            
            # Probar lectura de citations
            result = supabase.table('citations').select("*").limit(1).execute()
            print("✅ Tabla citations accesible!")
            
            # Probar lectura de relationships
            result = supabase.table('relationships').select("*").limit(1).execute()
            print("✅ Tabla relationships accesible!")
            
            # Probar inserción (y luego eliminar el registro de prueba)
            test_data = {
                'source_url': 'test_url',
                'concept': 'test_concept',
                'content': 'test_content',
                'evidence_score': 1.0,
                'novelty_score': 1.0,
                'reference_list': '[]',
                'embedding': [0.0] * 384,  # Vector de prueba
                'category': 'test'
            }
            
            insert_result = supabase.table('knowledge_items').insert(test_data).execute()
            print("✅ Permisos de escritura verificados!")
            
            # Limpiar el registro de prueba
            test_id = insert_result.data[0]['id']
            supabase.table('knowledge_items').delete().eq('id', test_id).execute()
            print("✅ Registro de prueba eliminado correctamente!")
            
        except Exception as e:
            print(f"⚠️ Error al acceder a la base de datos: {str(e)}")
            print("Verifica que las tablas existan y tengas los permisos necesarios.")
        
    except Exception as e:
        print(f"❌ Error al conectar con Supabase: {str(e)}")

if __name__ == "__main__":
    test_supabase_connection()
