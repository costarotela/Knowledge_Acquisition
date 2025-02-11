"""
Script de prueba para el procesador de video.
"""

import sys
import os
from pathlib import Path
import logging

# Agregar el directorio src al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.processors.video_processor import EnhancedVideoProcessor

def test_video_processor():
    """Prueba el procesador de video."""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Video de prueba (un video corto)
    video_path = "test_data/sample_video.mp4"
    transcript = """
    Este es un video de ejemplo que muestra diferentes escenas.
    En la primera escena vemos una persona caminando.
    En la segunda escena hay un auto en movimiento.
    Finalmente, vemos un paisaje natural con árboles y montañas.
    """
    
    print("\n=== Test de Procesamiento de Video ===")
    
    # 1. Inicializar procesador
    print("\nInicializando procesador...")
    processor = EnhancedVideoProcessor()
    
    # 2. Procesar video
    print("\nProcesando video...")
    fragments = processor.process_video(video_path, transcript)
    
    if fragments:
        print("\n✓ Video procesado exitosamente")
        
        # 3. Mostrar resultados
        print("\nFragmentos Extraídos:")
        print("=" * 50)
        
        for i, fragment in enumerate(fragments, 1):
            print(f"\n📽️ Fragmento {i}:")
            print(f"⏱️ Tiempo: {fragment.start_time:.1f}s - {fragment.end_time:.1f}s")
            
            # Mostrar objetos detectados
            objects = set()
            for frame in fragment.frames:
                objects.update(frame.objects)
            if objects:
                print("\n🔍 Objetos Detectados:")
                for obj in objects:
                    print(f"   • {obj}")
            
            # Mostrar dominios de conocimiento
            if fragment.knowledge_domains:
                print("\n🎯 Dominios de Conocimiento:")
                for domain in fragment.knowledge_domains:
                    print(f"   • {domain.name} ({domain.confidence * 100:.1f}% confianza)")
            
            # Mostrar grafo de conocimiento
            if fragment.knowledge_graph:
                print("\n🕸️ Grafo de Conocimiento:")
                
                # Conceptos
                if "concepts" in fragment.knowledge_graph:
                    print("\n   📚 Conceptos:")
                    for domain, concepts in fragment.knowledge_graph["concepts"].items():
                        print(f"\n      🔍 {domain}:")
                        for concept in concepts:
                            relevance = concept["relevance"] * 100
                            print(f"         • {concept['term']} ({relevance:.1f}% relevancia)")
                
                # Definiciones
                if "definitions" in fragment.knowledge_graph:
                    print("\n   📖 Definiciones:")
                    for definition in fragment.knowledge_graph["definitions"]:
                        confidence = definition["confidence"] * 100
                        print(f"\n      • {definition['term']} ({confidence:.1f}% confianza):")
                        print(f"        {definition['definition']}")
                
                # Relaciones
                if "relations" in fragment.knowledge_graph:
                    print("\n   🔗 Relaciones:")
                    for rel_type, relations in fragment.knowledge_graph["relations"].items():
                        if relations:
                            print(f"\n      • {rel_type}:")
                            for rel in relations:
                                confidence = rel["confidence"] * 100
                                print(f"         {rel['source']} → {rel['target']} ({confidence:.1f}% confianza)")
            
            print("\n" + "-" * 30)
        
        print("\n" + "=" * 50)
    else:
        print("\n❌ Error al procesar el video")

if __name__ == "__main__":
    test_video_processor()
