"""
Motor de recomendaciones basado en Machine Learning.
Utiliza técnicas de collaborative filtering y content-based filtering
para generar recomendaciones personalizadas.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestClassifier
import joblib
from datetime import datetime
import logging
from .schemas import (
    TravelPackage,
    CustomerProfile,
    SaleRecord,
    PackageFeatures
)

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Motor de recomendaciones que combina múltiples técnicas:
    1. Collaborative Filtering
    2. Content-Based Filtering
    3. Predicción de conversión
    4. Optimización de precios
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        min_similarity: float = 0.3
    ):
        self.scaler = StandardScaler()
        self.min_similarity = min_similarity
        self.conversion_model = None
        
        if model_path:
            try:
                self.conversion_model = joblib.load(model_path)
                logger.info("Modelo de conversión cargado exitosamente")
            except Exception as e:
                logger.warning(f"No se pudo cargar el modelo: {e}")
                
    def generate_recommendations(
        self,
        customer: CustomerProfile,
        available_packages: List[TravelPackage],
        sale_history: List[SaleRecord],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Genera recomendaciones personalizadas combinando múltiples técnicas.
        
        Args:
            customer: Perfil del cliente
            available_packages: Paquetes disponibles
            sale_history: Historial de ventas
            top_n: Número de recomendaciones a generar
            
        Returns:
            Lista de recomendaciones con scores y explicaciones
        """
        # 1. Obtener recomendaciones por contenido
        content_recs = self._content_based_recommendations(
            customer,
            available_packages
        )
        
        # 2. Obtener recomendaciones colaborativas
        collab_recs = self._collaborative_recommendations(
            customer,
            available_packages,
            sale_history
        )
        
        # 3. Predecir probabilidad de conversión
        conversion_probs = self._predict_conversion_probability(
            customer,
            available_packages,
            sale_history
        )
        
        # 4. Calcular precios óptimos
        price_adjustments = self._calculate_price_adjustments(
            available_packages,
            sale_history
        )
        
        # Combinar todos los scores
        final_recommendations = []
        for package in available_packages:
            content_score = content_recs.get(package.id, 0.0)
            collab_score = collab_recs.get(package.id, 0.0)
            conv_prob = conversion_probs.get(package.id, 0.0)
            price_adj = price_adjustments.get(package.id, 0.0)
            
            # Score final ponderado
            final_score = (
                content_score * 0.3 +
                collab_score * 0.3 +
                conv_prob * 0.25 +
                (1.0 - abs(price_adj)) * 0.15
            )
            
            if final_score >= self.min_similarity:
                final_recommendations.append({
                    'package': package,
                    'score': final_score,
                    'details': {
                        'content_similarity': content_score,
                        'collaborative_score': collab_score,
                        'conversion_probability': conv_prob,
                        'price_adjustment': price_adj
                    },
                    'explanation': self._generate_explanation(
                        package,
                        content_score,
                        collab_score,
                        conv_prob,
                        price_adj
                    )
                })
                
        # Ordenar por score y tomar los top_n
        final_recommendations.sort(
            key=lambda x: x['score'],
            reverse=True
        )
        return final_recommendations[:top_n]
    
    def _content_based_recommendations(
        self,
        customer: CustomerProfile,
        packages: List[TravelPackage]
    ) -> Dict[str, float]:
        """
        Genera recomendaciones basadas en el contenido del paquete
        y las preferencias del cliente.
        """
        # Extraer características de los paquetes
        package_features = []
        for package in packages:
            features = self._extract_package_features(package)
            package_features.append(features)
            
        if not package_features:
            return {}
            
        # Crear matriz de características
        feature_matrix = pd.DataFrame(package_features)
        
        # Normalizar características
        normalized_features = self.scaler.fit_transform(feature_matrix)
        
        # Crear perfil del cliente
        customer_profile = self._create_customer_profile(customer)
        
        # Calcular similitud coseno
        similarities = cosine_similarity(
            [customer_profile],
            normalized_features
        )[0]
        
        # Crear diccionario de scores
        return {
            package.id: similarity
            for package, similarity in zip(packages, similarities)
        }
    
    def _collaborative_recommendations(
        self,
        customer: CustomerProfile,
        packages: List[TravelPackage],
        sale_history: List[SaleRecord]
    ) -> Dict[str, float]:
        """
        Genera recomendaciones basadas en ventas similares.
        """
        if not sale_history:
            return {}
            
        # Crear matriz de ventas
        sales_df = pd.DataFrame([
            {
                'customer_type': sale.customer_profile.type,
                'package_id': sale.package_id,
                'success': sale.success,
                'satisfaction': sale.satisfaction or 0.0
            }
            for sale in sale_history
        ])
        
        if sales_df.empty:
            return {}
            
        # Filtrar ventas exitosas de clientes similares
        similar_sales = sales_df[
            (sales_df['customer_type'] == customer.type) &
            (sales_df['success'] == True)
        ]
        
        if similar_sales.empty:
            return {}
            
        # Calcular score por paquete
        package_scores = {}
        for package in packages:
            package_sales = similar_sales[
                similar_sales['package_id'] == package.id
            ]
            
            if not package_sales.empty:
                # Score basado en satisfacción y frecuencia
                satisfaction = package_sales['satisfaction'].mean()
                frequency = len(package_sales) / len(similar_sales)
                package_scores[package.id] = (satisfaction + frequency) / 2
            else:
                package_scores[package.id] = 0.0
                
        return package_scores
    
    def _predict_conversion_probability(
        self,
        customer: CustomerProfile,
        packages: List[TravelPackage],
        sale_history: List[SaleRecord]
    ) -> Dict[str, float]:
        """
        Predice la probabilidad de conversión para cada paquete.
        """
        if not self.conversion_model or not sale_history:
            return {package.id: 0.5 for package in packages}
            
        # Preparar características para predicción
        X = []
        for package in packages:
            features = self._extract_sale_features(
                customer,
                package,
                sale_history
            )
            X.append(features)
            
        if not X:
            return {package.id: 0.5 for package in packages}
            
        # Realizar predicción
        try:
            probabilities = self.conversion_model.predict_proba(X)[:, 1]
            return {
                package.id: prob
                for package, prob in zip(packages, probabilities)
            }
        except Exception as e:
            logger.error(f"Error en predicción de conversión: {e}")
            return {package.id: 0.5 for package in packages}
    
    def _calculate_price_adjustments(
        self,
        packages: List[TravelPackage],
        sale_history: List[SaleRecord]
    ) -> Dict[str, float]:
        """
        Calcula ajustes de precio recomendados basados en histórico.
        Retorna porcentaje de ajuste sugerido (-0.1 = reducir 10%).
        """
        if not sale_history:
            return {package.id: 0.0 for package in packages}
            
        adjustments = {}
        for package in packages:
            # Obtener ventas históricas del paquete
            package_sales = [
                sale for sale in sale_history
                if sale.package_id == package.id
            ]
            
            if not package_sales:
                adjustments[package.id] = 0.0
                continue
                
            # Analizar éxito de ventas
            success_rate = sum(
                1 for sale in package_sales if sale.success
            ) / len(package_sales)
            
            # Analizar precios históricos
            historical_prices = [sale.price for sale in package_sales]
            current_price = package.price
            avg_price = np.mean(historical_prices)
            
            # Calcular ajuste
            if success_rate < 0.3 and current_price > avg_price:
                # Baja tasa de éxito y precio alto: sugerir reducción
                adjustments[package.id] = -0.1
            elif success_rate > 0.7 and current_price < avg_price:
                # Alta tasa de éxito y precio bajo: sugerir aumento
                adjustments[package.id] = 0.1
            else:
                adjustments[package.id] = 0.0
                
        return adjustments
    
    def _extract_package_features(
        self,
        package: TravelPackage
    ) -> PackageFeatures:
        """
        Extrae características numéricas de un paquete.
        """
        duration = (
            (package.end_date - package.start_date).days
            if package.end_date and package.start_date
            else 0
        )
        
        return PackageFeatures(
            price=package.price,
            duration=duration,
            price_per_day=(
                package.price / duration if duration > 0
                else package.price
            ),
            activities_count=len(package.activities or []),
            accommodation_quality=(
                package.accommodation.stars
                if package.accommodation
                else 0
            )
        )
    
    def _create_customer_profile(
        self,
        customer: CustomerProfile
    ) -> np.ndarray:
        """
        Crea un vector de características del cliente.
        """
        # Mapear tipo de cliente a valores numéricos
        type_values = {
            'default': [0.5, 0.5, 0.5, 0.5],
            'premium': [0.8, 0.9, 0.3, 0.8],
            'corporate': [0.7, 0.8, 0.4, 0.9],
            'family': [0.6, 0.7, 0.7, 0.5]
        }
        
        return np.array(
            type_values.get(
                customer.type,
                type_values['default']
            )
        )
    
    def _extract_sale_features(
        self,
        customer: CustomerProfile,
        package: TravelPackage,
        sale_history: List[SaleRecord]
    ) -> List[float]:
        """
        Extrae características para el modelo de conversión.
        """
        package_features = self._extract_package_features(package)
        customer_profile = self._create_customer_profile(customer)
        
        # Características del historial
        similar_sales = [
            sale for sale in sale_history
            if (
                sale.customer_profile.type == customer.type and
                sale.package_id == package.id
            )
        ]
        
        historical_success = (
            sum(1 for sale in similar_sales if sale.success) /
            len(similar_sales)
        ) if similar_sales else 0.5
        
        # Combinar todas las características
        return [
            *asdict(package_features).values(),
            *customer_profile,
            historical_success
        ]
    
    def _generate_explanation(
        self,
        package: TravelPackage,
        content_score: float,
        collab_score: float,
        conv_prob: float,
        price_adj: float
    ) -> str:
        """
        Genera una explicación en lenguaje natural de la recomendación.
        """
        reasons = []
        
        if content_score > 0.7:
            reasons.append(
                "Este paquete coincide muy bien con sus preferencias"
            )
        elif content_score > 0.5:
            reasons.append(
                "Este paquete se ajusta a sus preferencias"
            )
            
        if collab_score > 0.7:
            reasons.append(
                "Ha sido muy popular entre clientes similares"
            )
        elif collab_score > 0.5:
            reasons.append(
                "Otros clientes similares han disfrutado este paquete"
            )
            
        if conv_prob > 0.7:
            reasons.append(
                "Tiene una alta probabilidad de satisfacer sus necesidades"
            )
            
        if price_adj < -0.05:
            reasons.append(
                "Actualmente tiene un precio competitivo"
            )
            
        if not reasons:
            reasons.append(
                "Podría ser una opción interesante para considerar"
            )
            
        return " y ".join(reasons) + "."
    
    def train_conversion_model(
        self,
        sale_history: List[SaleRecord],
        model_path: Optional[str] = None
    ) -> None:
        """
        Entrena el modelo de predicción de conversión.
        """
        if not sale_history:
            logger.warning("No hay suficientes datos para entrenar el modelo")
            return
            
        # Preparar datos de entrenamiento
        X = []
        y = []
        
        for sale in sale_history:
            features = self._extract_sale_features(
                sale.customer_profile,
                sale.package,
                sale_history
            )
            X.append(features)
            y.append(1 if sale.success else 0)
            
        if not X:
            logger.warning("No se pudieron extraer características para entrenamiento")
            return
            
        # Entrenar modelo
        self.conversion_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        
        try:
            self.conversion_model.fit(X, y)
            logger.info("Modelo de conversión entrenado exitosamente")
            
            if model_path:
                joblib.dump(self.conversion_model, model_path)
                logger.info(f"Modelo guardado en {model_path}")
                
        except Exception as e:
            logger.error(f"Error entrenando el modelo: {e}")
            self.conversion_model = None
