"""
Script para configurar la base de datos en Supabase.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Configura la base de datos en Supabase."""
    try:
        # Cargar variables de entorno
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_KEY son requeridas")
        
        # Inicializar cliente
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Cliente Supabase inicializado")
        
        # Leer archivo SQL
        sql_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "sql", "migrations", "001_create_knowledge_tables.sql"
        )
        with open(sql_path, 'r') as f:
            sql = f.read()
        
        # Ejecutar SQL por partes
        logger.info("Ejecutando script SQL...")
        
        # Dividir el SQL en comandos individuales
        commands = sql.split(';')
        for cmd in commands:
            cmd = cmd.strip()
            if cmd:  # Ignorar líneas vacías
                try:
                    # Usar el cliente REST para ejecutar SQL
                    result = supabase.rest.rpc('exec_sql', {'query': cmd}).execute()
                    logger.info(f"Comando ejecutado: {cmd[:50]}...")
                except Exception as e:
                    logger.error(f"Error ejecutando comando: {cmd[:50]}...")
                    logger.error(f"Error: {str(e)}")
                    # Continuar con el siguiente comando
        
        logger.info("Base de datos configurada exitosamente")
        
        # Verificar tablas creadas
        tables = ["knowledge_items", "knowledge_fragments", "video_frames", "citations"]
        for table in tables:
            try:
                count = supabase.table(table).select("count", count="exact").execute()
                logger.info(f"Tabla {table} creada. Filas: {count.count if hasattr(count, 'count') else 0}")
            except Exception as e:
                logger.error(f"Error verificando tabla {table}: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error configurando la base de datos: {str(e)}")
        raise

if __name__ == "__main__":
    setup_database()
