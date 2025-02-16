"""
Motor de visualización para análisis de paquetes turísticos.
Genera gráficos y visualizaciones para ayudar en la toma de decisiones.
"""

from typing import List, Dict, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from .schemas import TravelPackage, PriceHistory, CustomerProfile

class VisualizationEngine:
    """
    Motor de visualización para análisis de paquetes turísticos.
    Genera gráficos interactivos para la toma de decisiones.
    """
    
    def __init__(self, theme: str = 'light'):
        self.theme = theme
        self.colors = {
            'primary': '#2C3E50',
            'secondary': '#3498DB',
            'accent': '#E74C3C',
            'success': '#2ECC71',
            'warning': '#F1C40F'
        }
        
    def generate_package_dashboard(
        self,
        package: TravelPackage,
        analysis_results: Dict,
        price_history: Optional[List[PriceHistory]] = None,
        similar_packages: Optional[List[TravelPackage]] = None
    ) -> Dict[str, go.Figure]:
        """
        Genera un dashboard completo para un paquete específico.
        
        Returns:
            Dict con figuras de Plotly para cada visualización
        """
        figures = {}
        
        # 1. Radar chart de scores
        figures['scores'] = self._create_score_radar(
            analysis_results['scores']
        )
        
        # 2. Tendencia de precios
        if price_history:
            figures['price_trend'] = self._create_price_trend(
                package,
                price_history,
                analysis_results['analysis']['price_trend']
            )
            
        # 3. Comparativa de valor
        if similar_packages:
            figures['value_comparison'] = self._create_value_comparison(
                package,
                similar_packages,
                analysis_results
            )
            
        # 4. Desglose de beneficios
        figures['benefits'] = self._create_benefits_breakdown(package)
        
        return figures
    
    def generate_market_overview(
        self,
        packages: List[TravelPackage],
        price_history: List[PriceHistory]
    ) -> go.Figure:
        """
        Genera una visualización del panorama general del mercado.
        """
        # Crear figura con subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Distribución de Precios',
                'Tendencia del Mercado',
                'Categorías de Alojamiento',
                'Duración de Paquetes'
            )
        )
        
        # 1. Distribución de precios (boxplot)
        prices = [p.price for p in packages]
        fig.add_trace(
            go.Box(
                y=prices,
                name='Precios',
                boxpoints='outliers',
                marker_color=self.colors['primary']
            ),
            row=1, col=1
        )
        
        # 2. Tendencia del mercado
        df_history = pd.DataFrame([
            {
                'date': ph.timestamp,
                'price': ph.price,
                'package_id': ph.package_id
            }
            for ph in price_history
        ])
        
        if not df_history.empty:
            df_avg = df_history.groupby('date')['price'].mean().reset_index()
            fig.add_trace(
                go.Scatter(
                    x=df_avg['date'],
                    y=df_avg['price'],
                    name='Precio Promedio',
                    line=dict(color=self.colors['secondary'])
                ),
                row=1, col=2
            )
            
        # 3. Categorías de alojamiento
        accommodation_types = {}
        for p in packages:
            if p.accommodation:
                acc_type = p.accommodation.type
                accommodation_types[acc_type] = accommodation_types.get(acc_type, 0) + 1
                
        fig.add_trace(
            go.Pie(
                labels=list(accommodation_types.keys()),
                values=list(accommodation_types.values()),
                name='Tipos de Alojamiento'
            ),
            row=2, col=1
        )
        
        # 4. Duración de paquetes
        durations = [
            (p.end_date - p.start_date).days
            for p in packages
            if p.end_date and p.start_date
        ]
        
        fig.add_trace(
            go.Histogram(
                x=durations,
                name='Duración',
                marker_color=self.colors['accent']
            ),
            row=2, col=2
        )
        
        # Actualizar layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text='Panorama del Mercado',
            template='plotly_white' if self.theme == 'light' else 'plotly_dark'
        )
        
        return fig
    
    def _create_score_radar(self, scores: Dict[str, float]) -> go.Figure:
        """
        Crea un gráfico radar de los scores del paquete.
        """
        fig = go.Figure()
        
        # Preparar datos
        categories = list(scores.keys())
        values = list(scores.values())
        
        # Agregar trace
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],  # Cerrar el polígono
            theta=categories + [categories[0]],
            fill='toself',
            name='Scores',
            line_color=self.colors['primary']
        ))
        
        # Actualizar layout
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=False,
            title='Análisis de Scores'
        )
        
        return fig
    
    def _create_price_trend(
        self,
        package: TravelPackage,
        price_history: List[PriceHistory],
        trend_analysis: Dict
    ) -> go.Figure:
        """
        Crea un gráfico de tendencia de precios.
        """
        fig = go.Figure()
        
        # Filtrar historial para este paquete
        package_history = [
            ph for ph in price_history
            if ph.package_id == package.id
        ]
        
        if package_history:
            # Ordenar por fecha
            package_history.sort(key=lambda x: x.timestamp)
            
            # Crear series
            dates = [ph.timestamp for ph in package_history]
            prices = [ph.price for ph in package_history]
            
            # Línea principal
            fig.add_trace(go.Scatter(
                x=dates,
                y=prices,
                name='Precio',
                line=dict(color=self.colors['primary'])
            ))
            
            # Precio actual
            fig.add_trace(go.Scatter(
                x=[dates[-1]],
                y=[package.price],
                name='Precio Actual',
                mode='markers',
                marker=dict(
                    size=12,
                    color=self.colors['accent']
                )
            ))
            
            # Agregar bandas de volatilidad si hay suficientes datos
            if len(prices) > 2:
                mean = np.mean(prices)
                std = np.std(prices)
                
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[mean + std] * len(dates),
                    fill=None,
                    mode='lines',
                    line_color='rgba(0,0,0,0)',
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[mean - std] * len(dates),
                    fill='tonexty',
                    mode='lines',
                    line_color='rgba(0,0,0,0)',
                    fillcolor='rgba(52, 152, 219, 0.2)',
                    name='Banda de Volatilidad'
                ))
            
            # Agregar anotaciones de tendencia
            if trend_analysis:
                fig.add_annotation(
                    x=dates[-1],
                    y=max(prices),
                    text=f"Tendencia: {trend_analysis['trend']}<br>"
                         f"Cambio: {trend_analysis['avg_change_percent']:.1f}%",
                    showarrow=True,
                    arrowhead=1
                )
        
        # Actualizar layout
        fig.update_layout(
            title='Tendencia de Precios',
            xaxis_title='Fecha',
            yaxis_title='Precio',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_value_comparison(
        self,
        package: TravelPackage,
        similar_packages: List[TravelPackage],
        analysis_results: Dict
    ) -> go.Figure:
        """
        Crea un gráfico comparativo de valor entre paquetes similares.
        """
        fig = go.Figure()
        
        # Preparar datos
        packages = [package] + similar_packages
        
        # Calcular métricas por paquete
        data = []
        for pkg in packages:
            duration = (
                (pkg.end_date - pkg.start_date).days
                if pkg.end_date and pkg.start_date
                else 0
            )
            
            activities = len(pkg.activities) if pkg.activities else 0
            stars = pkg.accommodation.stars if pkg.accommodation else 0
            
            price_per_day = pkg.price / duration if duration > 0 else pkg.price
            
            data.append({
                'id': pkg.id,
                'title': pkg.title,
                'price': pkg.price,
                'price_per_day': price_per_day,
                'activities': activities,
                'stars': stars,
                'is_current': pkg.id == package.id
            })
            
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        # Normalizar valores
        for col in ['price_per_day', 'activities', 'stars']:
            if df[col].std() != 0:
                df[f'{col}_norm'] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
            else:
                df[f'{col}_norm'] = 1.0
                
        # Calcular score de valor
        df['value_score'] = (
            df['activities_norm'] * 0.4 +
            df['stars_norm'] * 0.3 +
            (1 - df['price_per_day_norm']) * 0.3
        )
        
        # Crear gráfico de burbujas
        fig.add_trace(go.Scatter(
            x=df['price_per_day'],
            y=df['value_score'],
            text=df['title'],
            mode='markers',
            marker=dict(
                size=(df['activities'] + 1) * 10,
                sizemode='area',
                sizeref=2.*max(df['activities']+1)/(40.**2),
                color=[
                    self.colors['accent'] if is_current else self.colors['primary']
                    for is_current in df['is_current']
                ]
            ),
            name='Paquetes'
        ))
        
        # Actualizar layout
        fig.update_layout(
            title='Comparación de Valor',
            xaxis_title='Precio por Día',
            yaxis_title='Score de Valor',
            showlegend=False,
            hovermode='closest'
        )
        
        return fig
    
    def _create_benefits_breakdown(
        self,
        package: TravelPackage
    ) -> go.Figure:
        """
        Crea un desglose visual de los beneficios del paquete.
        """
        fig = go.Figure()
        
        # Preparar datos de beneficios
        benefits = []
        values = []
        
        # Alojamiento
        if package.accommodation:
            benefits.append('Alojamiento')
            values.append(package.accommodation.stars if package.accommodation.stars else 3)
            
        # Actividades
        if package.activities:
            for activity in package.activities:
                benefits.append(activity.title)
                # Valor basado en duración si está disponible
                if activity.duration:
                    try:
                        hours = float(activity.duration.split()[0])
                        values.append(hours)
                    except:
                        values.append(1)
                else:
                    values.append(1)
                    
        # Si no hay beneficios, agregar placeholder
        if not benefits:
            benefits = ['Paquete Básico']
            values = [1]
            
        # Crear gráfico de barras horizontal
        fig.add_trace(go.Bar(
            y=benefits,
            x=values,
            orientation='h',
            marker_color=self.colors['secondary']
        ))
        
        # Actualizar layout
        fig.update_layout(
            title='Desglose de Beneficios',
            xaxis_title='Valor Relativo',
            yaxis_title='Beneficio',
            showlegend=False,
            height=max(300, len(benefits) * 40)
        )
        
        return fig
