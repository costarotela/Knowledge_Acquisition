"""
Pruebas unitarias para el analizador de paquetes.
"""

import unittest
from datetime import datetime, timedelta
from ..core.package_analyzer import PackageAnalyzer
from ..core.schemas import (
    TravelPackage,
    CustomerProfile,
    PriceHistory,
    Accommodation,
    Activity
)

class TestPackageAnalyzer(unittest.TestCase):
    def setUp(self):
        """Configura el ambiente de pruebas."""
        self.analyzer = PackageAnalyzer()
        
        # Crear paquete de prueba base
        self.base_package = TravelPackage(
            id="test-package-1",
            title="Paquete de Prueba",
            description="Descripción del paquete",
            price=1000.0,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            accommodation=Accommodation(
                name="Hotel Test",
                type="Resort",
                stars=4
            ),
            activities=[
                Activity(
                    title="Actividad 1",
                    duration="2 horas"
                ),
                Activity(
                    title="Actividad 2",
                    duration="3 horas"
                )
            ]
        )
        
        # Cliente de prueba
        self.customer = CustomerProfile(
            name="Test User",
            type="default",
            email="test@example.com"
        )
        
        # Historial de precios
        self.price_history = [
            PriceHistory(
                package_id="test-package-1",
                price=950.0,
                timestamp=datetime.now() - timedelta(days=30)
            ),
            PriceHistory(
                package_id="test-package-1",
                price=1000.0,
                timestamp=datetime.now() - timedelta(days=15)
            ),
            PriceHistory(
                package_id="test-package-1",
                price=1050.0,
                timestamp=datetime.now() - timedelta(days=7)
            )
        ]
        
    def test_analyze_packages(self):
        """Prueba el análisis completo de paquetes."""
        packages = [self.base_package]
        results = self.analyzer.analyze_packages(
            packages,
            self.customer,
            self.price_history
        )
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Verificar estructura del resultado
        self.assertIn('package_id', result)
        self.assertIn('scores', result)
        self.assertIn('metrics', result)
        self.assertIn('analysis', result)
        
        # Verificar scores
        scores = result['scores']
        for key in ['price', 'value', 'quality', 'relevance']:
            self.assertIn(key, scores)
            self.assertGreaterEqual(scores[key], 0.0)
            self.assertLessEqual(scores[key], 1.0)
            
        # Verificar métricas
        metrics = result['metrics']
        self.assertEqual(metrics['duration'], 7)
        self.assertEqual(metrics['activities_count'], 2)
        self.assertEqual(metrics['accommodation_quality'], 4)
        
    def test_price_trend_analysis(self):
        """Prueba el análisis de tendencias de precios."""
        results = self.analyzer.analyze_packages(
            [self.base_package],
            self.customer,
            self.price_history
        )
        
        trend = results[0]['analysis']['price_trend']
        self.assertIsNotNone(trend)
        self.assertIn('trend', trend)
        self.assertIn('avg_change_percent', trend)
        self.assertIn('recent_change_percent', trend)
        self.assertIn('volatility', trend)
        
    def test_customer_type_relevance(self):
        """Prueba la relevancia según tipo de cliente."""
        # Probar con cliente premium
        premium_customer = CustomerProfile(
            name="Premium User",
            type="premium",
            email="premium@example.com"
        )
        
        premium_results = self.analyzer.analyze_packages(
            [self.base_package],
            premium_customer,
            self.price_history
        )
        
        # Probar con cliente familiar
        family_customer = CustomerProfile(
            name="Family User",
            type="family",
            email="family@example.com"
        )
        
        # Agregar actividad familiar al paquete
        family_package = self.base_package
        family_package.activities.append(
            Activity(
                title="Actividad para niños",
                duration="2 horas"
            )
        )
        
        family_results = self.analyzer.analyze_packages(
            [family_package],
            family_customer,
            self.price_history
        )
        
        # Verificar que las recomendaciones son diferentes
        premium_recs = premium_results[0]['analysis']['recommendations']
        family_recs = family_results[0]['analysis']['recommendations']
        self.assertNotEqual(premium_recs, family_recs)
        
    def test_promotions_detection(self):
        """Prueba la detección de promociones."""
        # Crear paquete con precio promocional
        promo_package = self.base_package
        promo_package.price = 800.0  # 20% menos que el promedio histórico
        
        results = self.analyzer.analyze_packages(
            [promo_package],
            self.customer,
            self.price_history
        )
        
        promotions = results[0]['analysis']['promotions']
        self.assertTrue(len(promotions) > 0)
        self.assertTrue(
            any(p['type'] == 'price_drop' for p in promotions)
        )
        
    def test_edge_cases(self):
        """Prueba casos límite y valores extremos."""
        # Paquete sin datos
        empty_package = TravelPackage(
            id="empty-package",
            title="Empty Package",
            price=100.0
        )
        
        results = self.analyzer.analyze_packages(
            [empty_package],
            self.customer,
            None
        )
        
        self.assertEqual(len(results), 1)
        self.assertTrue(all(
            0.0 <= score <= 1.0
            for score in results[0]['scores'].values()
        ))
        
        # Lista vacía de paquetes
        empty_results = self.analyzer.analyze_packages(
            [],
            self.customer,
            None
        )
        self.assertEqual(len(empty_results), 0)
        
if __name__ == '__main__':
    unittest.main()
