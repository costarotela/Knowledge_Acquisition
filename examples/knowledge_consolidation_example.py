import asyncio
import os
from dotenv import load_dotenv
from src.rag.knowledge_consolidator import KnowledgeConsolidator
from src.embeddings.vector_store import VectorStore

load_dotenv()

async def main():
    # Crear el consolidador de conocimiento
    consolidator = KnowledgeConsolidator(
        model_name="gpt-4",
        temperature=0.7
    )
    
    # Ejemplo 1: Aprender sobre Python asyncio de diferentes fuentes
    print("🤖 Aprendiendo sobre asyncio de diferentes fuentes...")
    
    # Fuentes web
    web_sources = [
        "https://docs.python.org/3/library/asyncio.html",
        "https://realpython.com/async-io-python/",
    ]
    
    # YouTube videos
    youtube_sources = [
        "https://www.youtube.com/watch?v=F19R_M4Nay4",  # Python AsyncIO Tutorial
        "https://www.youtube.com/watch?v=t5Bo1Je9EmE"   # AsyncIO Best Practices
    ]
    
    # Agregar conocimiento de fuentes web
    for url in web_sources:
        print(f"\n📚 Procesando {url}")
        # Crawlear la página
        page = await consolidator.crawler.scrape(url)
        
        # Agregar cada chunk como un nodo de conocimiento
        for chunk in page.chunks:
            node = await consolidator.add_knowledge(
                content=chunk.content,
                source_url=url,
                source_type="web",
                metadata={
                    "title": page.title,
                    "chunk_index": chunk.metadata.get("chunk_index")
                }
            )
            print(f"✅ Agregado nodo {node.id} con confianza {node.confidence:.2f}")
    
    # Agregar conocimiento de YouTube
    for url in youtube_sources:
        print(f"\n🎥 Procesando {url}")
        video_data = await consolidator.youtube_scraper.scrape(url)
        
        # Agregar transcripción como conocimiento
        if video_data.captions:
            for lang, captions in video_data.captions.items():
                node = await consolidator.add_knowledge(
                    content=captions,
                    source_url=url,
                    source_type="youtube",
                    metadata={
                        "title": video_data.title,
                        "language": lang,
                        "views": video_data.views,
                        "author": video_data.author
                    }
                )
                print(f"✅ Agregado nodo {node.id} con confianza {node.confidence:.2f}")
    
    # Consolidar conocimiento sobre asyncio
    print("\n🧠 Consolidando conocimiento sobre asyncio...")
    consolidation = await consolidator.consolidate_knowledge(
        topic="asyncio",
        min_confidence=0.7
    )
    
    print("\n📊 Resultados de la consolidación:")
    print(f"Nodos consolidados: {consolidation['consolidated_nodes']}")
    print("\n🤔 Síntesis:")
    print(consolidation["synthesis"])
    
    # Validar y actualizar el conocimiento
    print("\n🔄 Revalidando conocimiento...")
    validation = await consolidator.validate_and_update()
    
    print("\n📈 Estadísticas de validación:")
    print(f"Nodos validados: {validation['validated_nodes']}")
    for result in validation["results"]:
        print(
            f"Nodo {result['node_id']}: "
            f"Confianza {result['old_confidence']:.2f} → {result['new_confidence']:.2f}"
        )
    
    # Mostrar estadísticas generales
    stats = consolidator.get_knowledge_stats()
    print("\n📊 Estadísticas generales:")
    print(f"Total de nodos: {stats['total_nodes']}")
    print(f"Confianza promedio: {stats['average_confidence']:.2f}")
    print("\nNodos por nivel de confianza:")
    print(f"  Alta (>0.8): {stats['nodes_by_confidence']['high']}")
    print(f"  Media (0.5-0.8): {stats['nodes_by_confidence']['medium']}")
    print(f"  Baja (<0.5): {stats['nodes_by_confidence']['low']}")

if __name__ == "__main__":
    asyncio.run(main())
