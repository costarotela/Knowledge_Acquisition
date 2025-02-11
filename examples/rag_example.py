import asyncio
import os
from dotenv import load_dotenv
from src.rag.knowledge_agent import KnowledgeAgent, KnowledgeQuery

load_dotenv()

async def main():
    # Crear el agente de conocimiento
    agent = KnowledgeAgent(
        model_name="gpt-4",
        temperature=0.7
    )
    
    # URLs de ejemplo para aprender
    urls = [
        "https://docs.python.org/3/library/asyncio.html",
        "https://docs.python.org/3/library/concurrent.futures.html"
    ]
    
    print("🤖 Aprendiendo de las URLs...")
    pages = await agent.learn_from_urls(urls)
    print(f"✅ Aprendido de {len(pages)} páginas")
    
    # Realizar algunas consultas
    queries = [
        "¿Cuál es la diferencia entre asyncio y concurrent.futures?",
        "¿Cómo se implementa un servidor asíncrono con asyncio?",
        "Explica el concepto de corrutinas en Python"
    ]
    
    for query_text in queries:
        print(f"\n🔍 Consulta: {query_text}")
        
        # Crear y ejecutar la consulta
        query = KnowledgeQuery(
            query=query_text,
            metadata_filters={"type": "documentation"}
        )
        
        response = await agent.query_knowledge(query)
        
        print(f"\n📝 Respuesta (Confianza: {response.confidence:.2f}):")
        print(response.answer)
        
        print("\n📚 Fuentes:")
        for i, source in enumerate(response.sources, 1):
            print(f"{i}. Score: {source['score']:.2f}")
            print(f"   {source['metadata'].get('url', 'N/A')}")
    
    # Mostrar estadísticas
    stats = agent.get_stats()
    print("\n📊 Estadísticas:")
    print(f"Total de documentos: {stats['vector_store']['total_documents']}")
    print(f"Modelo: {stats['model']['name']}")

if __name__ == "__main__":
    asyncio.run(main())
