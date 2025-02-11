"""
Script de prueba para el categorizador de dominios.
"""

import sys
import os
import time
from pathlib import Path

# Agregar el directorio src al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.processors.domain_categorizer import DomainCategorizer
from src.models.video_models import KnowledgeDomain

def test_categorization():
    # Texto de ejemplo con múltiples dominios
    test_text = """
    This comprehensive guide covers the essential aspects of sports nutrition and workout planning.
    We'll discuss how protein intake affects muscle recovery and growth, along with the best
    pre-workout supplements for maximum performance. The video also covers cardio training
    techniques and their impact on overall fitness levels.
    
    Key topics include:
    - Proper meal timing for muscle growth
    - Essential vitamins and minerals for athletes
    - High-intensity interval training (HIIT)
    - Recovery strategies and injury prevention
    - Mental preparation and stress management
    
    Remember to consult with your healthcare provider before starting any new exercise routine
    or making significant changes to your diet.
    """
    
    # Crear instancia del categorizador
    print("\n=== Test de Categorización ===")
    print("\nInicializando categorizador...")
    start_time = time.time()
    categorizer = DomainCategorizer()
    init_time = time.time() - start_time
    print(f"✓ Tiempo de inicialización: {init_time:.4f} segundos")
    
    # Realizar categorización
    print("\nCategorizando texto...")
    start_time = time.time()
    domains = categorizer.categorize(test_text)
    categorization_time = time.time() - start_time
    print(f"✓ Tiempo de categorización: {categorization_time:.4f} segundos")
    
    # Mostrar resultados
    print("\nDominios detectados:")
    print("=" * 50)
    for domain in domains:
        print(f"\n🔍 Dominio: {domain.name}")
        print(f"   Confianza: {domain.confidence:.2f}")
        if domain.sub_domains:
            print(f"   Sub-dominios: {', '.join(domain.sub_domains)}")
        if domain.key_concepts:
            print(f"   Conceptos clave: {', '.join(domain.key_concepts)}")
        print(f"   Descripción: {domain.description}")
        print("-" * 50)

if __name__ == "__main__":
    test_categorization()
