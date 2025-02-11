import os
import json
from typing import List, Dict, Any
import asyncio
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm import tqdm

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def save_to_json(data: Dict[str, Any], filename: str = "knowledge_base.json") -> None:
    """Guarda los datos en un archivo JSON."""
    try:
        # Si el archivo existe, cargar datos existentes
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = {"items": []}
        
        # Agregar nuevo item
        existing_data["items"].append(data)
        
        # Guardar datos actualizados
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Datos guardados en {filename}")
    except Exception as e:
        logger.error(f"Error guardando datos: {str(e)}")

def extract_video_id(url: str) -> str:
    """Extrae el ID del video de una URL de YouTube."""
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return url.split("/")[-1]

async def process_video_chunks(video_url: str) -> None:
    try:
        # Extraer ID del video
        video_id = extract_video_id(video_url)
        logger.info(f"Procesando video: {video_id}")
        
        # Obtener transcripción en español
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es'])
        logger.info("Transcripción obtenida en español")
        
        # Procesar en chunks de 5 minutos
        chunk_size = 5  # minutos
        current_chunk = []
        current_duration = 0
        all_chunks = []
        
        for entry in transcript:
            current_chunk.append(entry['text'])
            current_duration += entry['duration']
            
            if current_duration >= chunk_size * 60:  # Convertir minutos a segundos
                chunk_text = ' '.join(current_chunk)
                all_chunks.append(chunk_text)
                current_chunk = []
                current_duration = 0
        
        # Procesar último chunk si existe
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            all_chunks.append(chunk_text)
        
        logger.info(f"Video dividido en {len(all_chunks)} chunks")
        
        # Procesar cada chunk
        for i, chunk in enumerate(tqdm(all_chunks, desc="Procesando chunks")):
            try:
                # Extraer conocimiento usando GPT
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Eres un experto en extraer conocimiento estructurado de texto en español. Extrae los conceptos principales, sus relaciones y organízalos en formato JSON con las siguientes claves: conceptos_clave (lista), relaciones (lista de {concepto1, tipo_relacion, concepto2}), ideas_principales (lista), y conclusiones (lista). Mantén tu respuesta en español."},
                        {"role": "user", "content": f"Analiza el siguiente texto y extrae el conocimiento estructurado:\n\n{chunk}"}
                    ]
                )
                
                # Estructurar y guardar el conocimiento
                knowledge_item = {
                    "source": f"youtube_{video_id}",
                    "chunk_index": i,
                    "timestamp": datetime.now().isoformat(),
                    "content": response.choices[0].message.content,
                    "raw_text": chunk
                }
                
                # Guardar en archivo JSON
                save_to_json(knowledge_item)
                
                logger.info(f"Chunk {i+1}/{len(all_chunks)} procesado exitosamente")
                
            except Exception as e:
                logger.error(f"Error procesando chunk {i}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error en el proceso: {str(e)}")

if __name__ == "__main__":
    # Video sobre nutrición y suplementación
    VIDEO_URL = "https://www.youtube.com/watch?v=LPCHhkMd4N0"
    asyncio.run(process_video_chunks(VIDEO_URL))
