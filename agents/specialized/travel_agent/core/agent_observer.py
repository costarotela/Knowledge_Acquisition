"""
Sistema de observación y síntesis del agente.
Monitorea todas las actividades y genera insights accionables.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

class InsightType(Enum):
    """Tipos de insights que el observador puede generar."""
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    TREND = "trend"
    OPTIMIZATION = "optimization"
    ALERT = "alert"

@dataclass
class ComponentActivity:
    """Registro de actividad de un componente."""
    component_id: str
    action: str
    timestamp: datetime
    duration: float
    success: bool
    data: Dict
    metrics: Dict

@dataclass
class AgentInsight:
    """Insight generado por el observador."""
    type: InsightType
    priority: int
    description: str
    source_components: List[str]
    timestamp: datetime
    data: Dict
    recommendations: List[str]

class AgentObserver:
    """
    Sistema de observación que:
    1. Monitorea todas las actividades del agente
    2. Detecta patrones y anomalías
    3. Genera insights accionables
    4. Mantiene estado global
    """
    
    def __init__(self):
        self.activities = defaultdict(list)
        self.insights = []
        self.state = {}
        self.patterns = defaultdict(list)
        self.metrics = defaultdict(list)
        
    def register_activity(
        self,
        component_id: str,
        action: str,
        data: Dict,
        metrics: Dict,
        success: bool,
        duration: float
    ) -> None:
        """
        Registra una actividad de un componente.
        """
        activity = ComponentActivity(
            component_id=component_id,
            action=action,
            timestamp=datetime.now(),
            duration=duration,
            success=success,
            data=data,
            metrics=metrics
        )
        
        self.activities[component_id].append(activity)
        self._update_patterns(activity)
        self._update_metrics(activity)
        self._generate_insights()
        
    def get_component_status(
        self,
        component_id: str
    ) -> Dict:
        """
        Obtiene el estado actual de un componente.
        """
        activities = self.activities[component_id]
        if not activities:
            return {
                'status': 'unknown',
                'last_activity': None,
                'success_rate': 0.0,
                'avg_duration': 0.0
            }
            
        recent = [
            a for a in activities
            if (datetime.now() - a.timestamp).total_seconds() < 3600
        ]
        
        return {
            'status': 'active' if recent else 'idle',
            'last_activity': activities[-1].timestamp,
            'success_rate': sum(1 for a in recent if a.success) / len(recent) if recent else 0,
            'avg_duration': sum(a.duration for a in recent) / len(recent) if recent else 0
        }
        
    def get_system_health(self) -> Dict:
        """
        Obtiene el estado de salud general del sistema.
        """
        component_stats = {
            comp_id: self.get_component_status(comp_id)
            for comp_id in self.activities.keys()
        }
        
        return {
            'overall_status': self._calculate_overall_status(component_stats),
            'components': component_stats,
            'active_insights': len([
                i for i in self.insights
                if (datetime.now() - i.timestamp).total_seconds() < 3600
            ]),
            'performance_metrics': self._get_performance_metrics()
        }
        
    def get_latest_insights(
        self,
        max_count: int = 10,
        min_priority: int = 0
    ) -> List[AgentInsight]:
        """
        Obtiene los insights más recientes y relevantes.
        """
        return sorted(
            [i for i in self.insights if i.priority >= min_priority],
            key=lambda x: (x.priority, x.timestamp),
            reverse=True
        )[:max_count]
        
    def synthesize_state(self) -> Dict:
        """
        Sintetiza el estado actual del sistema.
        """
        current_state = {
            'timestamp': datetime.now(),
            'health': self.get_system_health(),
            'active_patterns': self._get_active_patterns(),
            'key_metrics': self._get_key_metrics(),
            'recent_insights': [
                {
                    'type': i.type.value,
                    'priority': i.priority,
                    'description': i.description,
                    'recommendations': i.recommendations
                }
                for i in self.get_latest_insights(max_count=5)
            ]
        }
        
        self.state = current_state
        return current_state
        
    def _update_patterns(self, activity: ComponentActivity) -> None:
        """
        Actualiza los patrones detectados.
        """
        # Patrones de tiempo
        self.patterns['timing'].append({
            'component': activity.component_id,
            'action': activity.action,
            'hour': activity.timestamp.hour,
            'success': activity.success
        })
        
        # Mantener solo últimas 1000 actividades
        if len(self.patterns['timing']) > 1000:
            self.patterns['timing'] = self.patterns['timing'][-1000:]
            
        # Patrones de rendimiento
        self.patterns['performance'].append({
            'component': activity.component_id,
            'duration': activity.duration,
            'timestamp': activity.timestamp
        })
        
        # Limpiar datos antiguos
        cutoff = datetime.now() - timedelta(days=7)
        self.patterns['performance'] = [
            p for p in self.patterns['performance']
            if p['timestamp'] > cutoff
        ]
        
    def _update_metrics(self, activity: ComponentActivity) -> None:
        """
        Actualiza métricas del sistema.
        """
        timestamp = activity.timestamp
        
        # Métricas por componente
        self.metrics[activity.component_id].append({
            'timestamp': timestamp,
            'duration': activity.duration,
            'success': activity.success,
            **activity.metrics
        })
        
        # Limpiar métricas antiguas
        cutoff = datetime.now() - timedelta(days=7)
        for component_id in self.metrics:
            self.metrics[component_id] = [
                m for m in self.metrics[component_id]
                if m['timestamp'] > cutoff
            ]
            
    def _generate_insights(self) -> None:
        """
        Genera nuevos insights basados en patrones y métricas.
        """
        new_insights = []
        
        # 1. Detectar anomalías de rendimiento
        for component_id, metrics in self.metrics.items():
            if not metrics:
                continue
                
            recent_durations = [m['duration'] for m in metrics[-50:]]
            if recent_durations:
                avg_duration = np.mean(recent_durations)
                std_duration = np.std(recent_durations)
                
                latest_duration = recent_durations[-1]
                if latest_duration > avg_duration + 2 * std_duration:
                    new_insights.append(AgentInsight(
                        type=InsightType.ALERT,
                        priority=2,
                        description=f"Rendimiento degradado en {component_id}",
                        source_components=[component_id],
                        timestamp=datetime.now(),
                        data={
                            'avg_duration': avg_duration,
                            'current_duration': latest_duration
                        },
                        recommendations=[
                            "Revisar carga del componente",
                            "Verificar recursos disponibles",
                            "Considerar optimización de caché"
                        ]
                    ))
                    
        # 2. Detectar patrones de uso
        timing_df = pd.DataFrame(self.patterns['timing'])
        if not timing_df.empty:
            # Analizar patrones por hora
            hourly_success = timing_df.groupby('hour')['success'].mean()
            best_hours = hourly_success[hourly_success > 0.8].index.tolist()
            
            if best_hours:
                new_insights.append(AgentInsight(
                    type=InsightType.OPTIMIZATION,
                    priority=1,
                    description="Identificados horarios óptimos de operación",
                    source_components=['timing_analysis'],
                    timestamp=datetime.now(),
                    data={'best_hours': best_hours},
                    recommendations=[
                        f"Priorizar operaciones en horas: {', '.join(map(str, best_hours))}",
                        "Ajustar recursos según patrón horario"
                    ]
                ))
                
        # 3. Detectar oportunidades de optimización
        for component_id, metrics in self.metrics.items():
            if not metrics:
                continue
                
            success_rate = sum(
                1 for m in metrics[-50:]
                if m['success']
            ) / min(50, len(metrics))
            
            if success_rate < 0.7:
                new_insights.append(AgentInsight(
                    type=InsightType.RISK,
                    priority=3,
                    description=f"Baja tasa de éxito en {component_id}",
                    source_components=[component_id],
                    timestamp=datetime.now(),
                    data={'success_rate': success_rate},
                    recommendations=[
                        "Revisar logs de errores",
                        "Verificar configuración",
                        "Considerar ajustes de parámetros"
                    ]
                ))
                
        # Agregar nuevos insights
        self.insights.extend(new_insights)
        
        # Mantener solo últimos 100 insights
        self.insights = sorted(
            self.insights,
            key=lambda x: (x.timestamp, x.priority),
            reverse=True
        )[:100]
        
    def _calculate_overall_status(
        self,
        component_stats: Dict[str, Dict]
    ) -> str:
        """
        Calcula el estado general del sistema.
        """
        active_components = sum(
            1 for stats in component_stats.values()
            if stats['status'] == 'active'
        )
        
        avg_success = np.mean([
            stats['success_rate']
            for stats in component_stats.values()
        ])
        
        if active_components == 0:
            return 'inactive'
        elif avg_success < 0.5:
            return 'degraded'
        elif avg_success < 0.8:
            return 'suboptimal'
        else:
            return 'healthy'
            
    def _get_performance_metrics(self) -> Dict:
        """
        Obtiene métricas de rendimiento agregadas.
        """
        all_metrics = []
        for component_metrics in self.metrics.values():
            all_metrics.extend(component_metrics)
            
        if not all_metrics:
            return {
                'avg_duration': 0,
                'success_rate': 0,
                'total_activities': 0
            }
            
        return {
            'avg_duration': np.mean([m['duration'] for m in all_metrics]),
            'success_rate': sum(1 for m in all_metrics if m['success']) / len(all_metrics),
            'total_activities': len(all_metrics)
        }
        
    def _get_active_patterns(self) -> Dict:
        """
        Obtiene patrones activos en el sistema.
        """
        patterns = {}
        
        # Patrones de tiempo
        timing_df = pd.DataFrame(self.patterns['timing'])
        if not timing_df.empty:
            patterns['timing'] = {
                'peak_hours': timing_df.groupby('hour')['success'].mean().nlargest(3).index.tolist(),
                'component_activity': timing_df['component'].value_counts().to_dict()
            }
            
        # Patrones de rendimiento
        perf_df = pd.DataFrame(self.patterns['performance'])
        if not perf_df.empty:
            patterns['performance'] = {
                'avg_duration_by_component': perf_df.groupby('component')['duration'].mean().to_dict(),
                'trend': 'improving' if perf_df['duration'].is_monotonic_decreasing else 'degrading'
            }
            
        return patterns
        
    def _get_key_metrics(self) -> Dict:
        """
        Obtiene métricas clave del sistema.
        """
        metrics = {}
        
        for component_id, component_metrics in self.metrics.items():
            if not component_metrics:
                continue
                
            recent_metrics = component_metrics[-50:]
            metrics[component_id] = {
                'success_rate': sum(1 for m in recent_metrics if m['success']) / len(recent_metrics),
                'avg_duration': np.mean([m['duration'] for m in recent_metrics]),
                'trend': self._calculate_metric_trend(recent_metrics)
            }
            
        return metrics
        
    def _calculate_metric_trend(
        self,
        metrics: List[Dict]
    ) -> str:
        """
        Calcula la tendencia de una métrica.
        """
        if len(metrics) < 2:
            return 'stable'
            
        durations = [m['duration'] for m in metrics]
        first_half = np.mean(durations[:len(durations)//2])
        second_half = np.mean(durations[len(durations)//2:])
        
        diff = second_half - first_half
        if abs(diff) < first_half * 0.1:
            return 'stable'
        return 'improving' if diff < 0 else 'degrading'
