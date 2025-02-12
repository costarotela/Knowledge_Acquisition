import os
from src.processors.video_processor import EnhancedVideoProcessor
from src.storage.video_storage import VideoStorage

def main():
    # URL del video de YouTube
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - El primer video de YouTube
    
    # Crear directorio temporal para frames
    frames_dir = "temp_frames"
    os.makedirs(frames_dir, exist_ok=True)

    try:
        # Inicializar procesador y almacenamiento
        processor = EnhancedVideoProcessor(frames_dir)
        storage = VideoStorage()
        
        print("Procesando video...")
        # Procesar video
        knowledge = processor.process_youtube_video(url)
        
        # Mostrar resultados del procesamiento
        print("\nVideo procesado exitosamente:")
        print(f"Título: {knowledge.title}")
        print(f"Canal: {knowledge.channel}")
        print(f"Temas principales: {knowledge.main_topics}")
        print(f"Número de fragmentos: {len(knowledge.fragments)}")
        
        # Mostrar información del primer fragmento
        if knowledge.fragments:
            first_fragment = knowledge.fragments[0]
            print("\nPrimer Fragmento:")
            print(f"Duración: {first_fragment.start_time}s to {first_fragment.end_time}s")
            print(f"Temas: {first_fragment.topics}")
            print(f"Palabras clave: {first_fragment.keywords}")
            print(f"Número de frames: {first_fragment.frame_count}")
        
        print("\nAlmacenando en Supabase...")
        # Almacenar en Supabase
        video_id = storage.store_video_knowledge(knowledge)
        print(f"Video almacenado con ID: {video_id}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Limpiar frames temporales
        if os.path.exists(frames_dir):
            for file in os.listdir(frames_dir):
                os.remove(os.path.join(frames_dir, file))
            os.rmdir(frames_dir)

if __name__ == "__main__":
    main()
