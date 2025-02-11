"""
Script de prueba para el extractor de conceptos.
"""

import sys
import os
import time
from pathlib import Path
import json

# Agregar el directorio src al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.processors.domain_categorizer import DomainCategorizer
from src.processors.concept_extractor import ConceptExtractor

def test_concept_extraction():
    # Texto de ejemplo con definiciones y relaciones
    test_text = """
    Sports nutrition is a specialized field that focuses on optimizing athletic performance through diet.
    Protein synthesis is a crucial process for muscle recovery and growth. Amino acids are the building
    blocks of protein, and they are essential for muscle repair.

    Carbohydrates are the primary energy source for high-intensity exercise. Complex carbohydrates
    contain multiple sugar molecules and provide sustained energy. Simple sugars, which are a type of
    carbohydrate, provide quick energy but can cause energy crashes.

    Recovery is part of the training process and requires proper nutrition. Post-workout nutrition
    affects muscle recovery and impacts overall performance. Mental preparation influences athletic
    performance and requires proper stress management techniques.

    HIIT, or High-Intensity Interval Training, is a type of cardio training that alternates between
    intense bursts of activity and periods of rest. This training method affects both aerobic and
    anaerobic fitness levels.
    """
    
    print("\n=== Test de Extracción de Conceptos ===")
    
    # 1. Categorizar el contenido primero
    print("\nCategorizando contenido...")
    start_time = time.time()
    categorizer = DomainCategorizer()
    domains = categorizer.categorize(test_text)
    categorization_time = time.time() - start_time
    print(f"✓ Tiempo de categorización: {categorization_time:.4f} segundos")
    
    # 2. Extraer conceptos y relaciones
    print("\nExtrayendo conceptos y relaciones...")
    start_time = time.time()
    extractor = ConceptExtractor()
    knowledge_graph = extractor.extract_knowledge_graph(test_text, domains)
    extraction_time = time.time() - start_time
    print(f"✓ Tiempo de extracción: {extraction_time:.4f} segundos")
    
    # 3. Mostrar resultados
    print("\nGrafo de Conocimiento:")
    print("=" * 50)
    
    # Conceptos por dominio
    print("\n📚 Conceptos por Dominio:")
    for domain, concepts in knowledge_graph["concepts"].items():
        print(f"\n   🔍 {domain}:")
        for concept in concepts:
            relevance = concept["relevance"] * 100
            print(f"      • {concept['term']} ({relevance:.1f}% relevancia)")
    
    # Definiciones
    print("\n📖 Definiciones:")
    for definition in knowledge_graph["definitions"]:
        confidence = definition["confidence"] * 100
        print(f"\n   • {definition['term']} ({confidence:.1f}% confianza):")
        print(f"     {definition['definition']}")
    
    # Relaciones
    print("\n🔗 Relaciones:")
    for rel_type, relations in knowledge_graph["relations"].items():
        if relations:  # Solo mostrar tipos de relación con al menos una relación
            print(f"\n   • {rel_type}:")
            for rel in relations:
                confidence = rel["confidence"] * 100
                print(f"     {rel['source']} → {rel['target']} ({confidence:.1f}% confianza)")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_concept_extraction()
