"""
Script de prueba para el procesador de YouTube.
"""

import sys
import os
from pathlib import Path
import json

# Agregar el directorio src al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.youtube_processor import YouTubeProcessor

def test_youtube_processor():
    """Prueba el procesador de YouTube."""
    
    # URL de ejemplo (un video corto sobre nutrición deportiva)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Reemplazar con una URL válida
    
    print("\n=== Test de Procesamiento de Video ===")
    
    # 1. Inicializar procesador
    print("\nInicializando procesador...")
    processor = YouTubeProcessor()
    
    # 2. Procesar video
    print("\nProcesando video...")
    knowledge = processor.process_video(url)
    
    if knowledge:
        print("\n✓ Video procesado exitosamente")
        
        # 3. Mostrar resultados
        print("\nConocimiento Extraído:")
        print("=" * 50)
        
        # Información básica
        print(f"\n📺 Video ID: {knowledge.video_id}")
        print(f"🔗 URL: {knowledge.url}")
        
        # Dominios detectados
        print("\n🎯 Dominios de Conocimiento:")
        for domain in knowledge.knowledge_domains:
            print(f"\n   • {domain.name} ({domain.confidence * 100:.1f}% confianza)")
            print(f"     Sub-dominios: {', '.join(domain.sub_domains)}")
            print(f"     Conceptos clave: {', '.join(domain.key_concepts)}")
        
        # Grafo de conocimiento
        print("\n🕸️ Grafo de Conocimiento:")
        
        # Conceptos por dominio
        print("\n   📚 Conceptos por Dominio:")
        for domain, concepts in knowledge.knowledge_graph["concepts"].items():
            print(f"\n      🔍 {domain}:")
            for concept in concepts:
                relevance = concept["relevance"] * 100
                print(f"         • {concept['term']} ({relevance:.1f}% relevancia)")
        
        # Definiciones
        print("\n   📖 Definiciones:")
        for definition in knowledge.knowledge_graph["definitions"]:
            confidence = definition["confidence"] * 100
            print(f"\n      • {definition['term']} ({confidence:.1f}% confianza):")
            print(f"        {definition['definition']}")
        
        # Relaciones
        print("\n   🔗 Relaciones:")
        for rel_type, relations in knowledge.knowledge_graph["relations"].items():
            if relations:
                print(f"\n      • {rel_type}:")
                for rel in relations:
                    confidence = rel["confidence"] * 100
                    print(f"         {rel['source']} → {rel['target']} ({confidence:.1f}% confianza)")
        
        # Fragmentos
        print("\n📋 Fragmentos:")
        for i, fragment in enumerate(knowledge.fragments[:3], 1):  # Mostrar solo los primeros 3
            print(f"\n   Fragmento {i}:")
            print(f"   Tiempo: {fragment.start_time:.1f}s - {fragment.end_time:.1f}s")
            print(f"   Dominios: {', '.join(d.name for d in fragment.knowledge_domains)}")
            print(f"   Texto: {fragment.text[:100]}...")  # Mostrar solo los primeros 100 caracteres
        
        if len(knowledge.fragments) > 3:
            print(f"\n   ... y {len(knowledge.fragments) - 3} fragmentos más")
        
        print("\n" + "=" * 50)
    else:
        print("\n❌ Error al procesar el video")

if __name__ == "__main__":
    test_youtube_processor()
