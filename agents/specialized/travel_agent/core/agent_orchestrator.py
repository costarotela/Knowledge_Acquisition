"""
Orquestador central del agente de viajes.
Coordina y optimiza todas las tareas para maximizar eficiencia.
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from dataclasses import dataclass
from enum import Enum
import numpy as np
from .package_analyzer import PackageAnalyzer
from .recommendation_engine import RecommendationEngine
from .visualization_engine import VisualizationEngine
from .opportunity_tracker import OpportunityTracker
from .agent_observer import AgentObserver
from .cache_manager import CacheManager
from .schemas import (
    TravelPackage,
    CustomerProfile,
    SaleRecord,
    Interaction,
    TaskResult,
    AgentContext
)

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Prioridades de tareas del agente."""
    HIGH = 3    # Respuesta inmediata requerida
    MEDIUM = 2  # Importante pero no urgente
    LOW = 1     # Puede esperar
    
class TaskType(Enum):
    """Tipos de tareas que el agente puede realizar."""
    SEARCH = "search"
    ANALYZE = "analyze"
    RECOMMEND = "recommend"
    VISUALIZE = "visualize"
    TRACK = "track"
    UPDATE = "update"

@dataclass
class AgentTask:
    """Tarea a ejecutar por el agente."""
    type: TaskType
    priority: TaskPriority
    data: Dict[str, Any]
    deadline: Optional[datetime] = None
    dependencies: List[str] = None
    cache_key: Optional[str] = None

class AgentOrchestrator:
    """
    Orquestador central que:
    1. Coordina todas las tareas del agente
    2. Optimiza recursos y rendimiento
    3. Mantiene contexto y estado
    4. Gestiona caché y persistencia
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        cache_ttl: int = 3600,
        enable_async: bool = True
    ):
        self.analyzer = PackageAnalyzer()
        self.recommender = RecommendationEngine()
        self.visualizer = VisualizationEngine()
        self.tracker = OpportunityTracker()
        self.cache = CacheManager(ttl=cache_ttl)
        self.observer = AgentObserver()  # Nuevo: Agregamos el observador
        
        self.max_workers = max_workers
        self.enable_async = enable_async
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.context = AgentContext()
        
        # Cola de tareas por prioridad
        self.task_queues = {
            TaskPriority.HIGH: [],
            TaskPriority.MEDIUM: [],
            TaskPriority.LOW: []
        }
        
    async def process_request(
        self,
        request_type: str,
        data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> TaskResult:
        """
        Procesa una solicitud del usuario.
        Determina tareas necesarias y las ejecuta optimizadamente.
        """
        # Actualizar contexto
        if context:
            self.context.update(context)
            
        # Generar tareas necesarias
        tasks = self._generate_tasks(request_type, data)
        
        # Priorizar y ordenar tareas
        ordered_tasks = self._prioritize_tasks(tasks)
        
        # Ejecutar tareas
        if self.enable_async:
            results = await self._execute_tasks_async(ordered_tasks)
        else:
            results = self._execute_tasks_sync(ordered_tasks)
            
        # Procesar y combinar resultados
        final_result = self._process_results(results)
        
        # Actualizar caché y estado
        self._update_state(final_result)
        
        return final_result
    
    def _generate_tasks(
        self,
        request_type: str,
        data: Dict[str, Any]
    ) -> List[AgentTask]:
        """
        Genera lista de tareas necesarias para procesar la solicitud.
        """
        tasks = []
        
        if request_type == "search_packages":
            # 1. Búsqueda inicial
            tasks.append(AgentTask(
                type=TaskType.SEARCH,
                priority=TaskPriority.HIGH,
                data=data,
                cache_key=f"search_{hash(str(data))}"
            ))
            
            # 2. Análisis de resultados
            tasks.append(AgentTask(
                type=TaskType.ANALYZE,
                priority=TaskPriority.MEDIUM,
                data={'search_results': None},  # Se completará con resultados de búsqueda
                dependencies=['search']
            ))
            
            # 3. Generación de recomendaciones
            tasks.append(AgentTask(
                type=TaskType.RECOMMEND,
                priority=TaskPriority.MEDIUM,
                data={'analyzed_packages': None},  # Se completará con resultados de análisis
                dependencies=['analyze']
            ))
            
        elif request_type == "track_opportunity":
            # 1. Actualizar seguimiento
            tasks.append(AgentTask(
                type=TaskType.TRACK,
                priority=TaskPriority.HIGH,
                data=data
            ))
            
            # 2. Actualizar visualizaciones
            tasks.append(AgentTask(
                type=TaskType.VISUALIZE,
                priority=TaskPriority.LOW,
                data={'tracking_data': None},
                dependencies=['track']
            ))
            
        elif request_type == "update_recommendations":
            # 1. Reanalizar datos
            tasks.append(AgentTask(
                type=TaskType.ANALYZE,
                priority=TaskPriority.MEDIUM,
                data=data
            ))
            
            # 2. Actualizar recomendaciones
            tasks.append(AgentTask(
                type=TaskType.UPDATE,
                priority=TaskPriority.MEDIUM,
                data={'analysis_results': None},
                dependencies=['analyze']
            ))
            
        return tasks
    
    def _prioritize_tasks(
        self,
        tasks: List[AgentTask]
    ) -> List[AgentTask]:
        """
        Ordena tareas por prioridad y dependencias.
        """
        # Separar por prioridad
        for task in tasks:
            self.task_queues[task.priority].append(task)
            
        # Ordenar considerando dependencias
        ordered_tasks = []
        completed_types = set()
        
        # Procesar por nivel de prioridad
        for priority in TaskPriority:
            priority_tasks = self.task_queues[priority]
            
            while priority_tasks:
                # Encontrar tareas que pueden ejecutarse
                ready_tasks = [
                    task for task in priority_tasks
                    if not task.dependencies or
                    all(dep in completed_types for dep in task.dependencies)
                ]
                
                if not ready_tasks:
                    break
                    
                # Agregar tareas listas a la lista ordenada
                for task in ready_tasks:
                    ordered_tasks.append(task)
                    completed_types.add(task.type.value)
                    priority_tasks.remove(task)
                    
        return ordered_tasks
    
    async def _execute_tasks_async(
        self,
        tasks: List[AgentTask]
    ) -> List[TaskResult]:
        """
        Ejecuta tareas de forma asíncrona.
        """
        results = []
        
        for task in tasks:
            # Verificar caché
            if task.cache_key:
                cached_result = self.cache.get(task.cache_key)
                if cached_result:
                    results.append(cached_result)
                    continue
                    
            # Ejecutar tarea
            if task.type == TaskType.SEARCH:
                result = await self._execute_search(task)
            elif task.type == TaskType.ANALYZE:
                result = await self._execute_analysis(task)
            elif task.type == TaskType.RECOMMEND:
                result = await self._execute_recommendation(task)
            elif task.type == TaskType.VISUALIZE:
                result = await self._execute_visualization(task)
            elif task.type == TaskType.TRACK:
                result = await self._execute_tracking(task)
            elif task.type == TaskType.UPDATE:
                result = await self._execute_update(task)
                
            # Guardar en caché si corresponde
            if task.cache_key:
                self.cache.set(task.cache_key, result)
                
            results.append(result)
            
        return results
    
    def _execute_tasks_sync(
        self,
        tasks: List[AgentTask]
    ) -> List[TaskResult]:
        """
        Ejecuta tareas de forma síncrona.
        """
        results = []
        
        for task in tasks:
            # Verificar caché
            if task.cache_key:
                cached_result = self.cache.get(task.cache_key)
                if cached_result:
                    results.append(cached_result)
                    continue
                    
            # Ejecutar tarea
            if task.type == TaskType.SEARCH:
                result = self._execute_search_sync(task)
            elif task.type == TaskType.ANALYZE:
                result = self._execute_analysis_sync(task)
            elif task.type == TaskType.RECOMMEND:
                result = self._execute_recommendation_sync(task)
            elif task.type == TaskType.VISUALIZE:
                result = self._execute_visualization_sync(task)
            elif task.type == TaskType.TRACK:
                result = self._execute_tracking_sync(task)
            elif task.type == TaskType.UPDATE:
                result = self._execute_update_sync(task)
                
            # Guardar en caché si corresponde
            if task.cache_key:
                self.cache.set(task.cache_key, result)
                
            results.append(result)
            
        return results
    
    async def _execute_search(self, task: AgentTask) -> TaskResult:
        """Ejecuta búsqueda de paquetes."""
        start_time = datetime.now()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._execute_search_sync,
                task
            )
            
            # Registrar actividad en el observador
            duration = (datetime.now() - start_time).total_seconds()
            self.observer.register_activity(
                component_id="search",
                action="execute_search",
                data={'task_type': task.type.value},
                metrics={'duration': duration},
                success=result.success,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.observer.register_activity(
                component_id="search",
                action="execute_search",
                data={'task_type': task.type.value, 'error': str(e)},
                metrics={'duration': duration},
                success=False,
                duration=duration
            )
            raise

    def _execute_search_sync(self, task: AgentTask) -> TaskResult:
        """Ejecuta búsqueda de forma síncrona."""
        try:
            # Implementar lógica de búsqueda
            search_params = task.data
            # ... lógica de búsqueda ...
            return TaskResult(
                success=True,
                data={'packages': []},
                error=None
            )
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return TaskResult(
                success=False,
                data=None,
                error=str(e)
            )
            
    async def _execute_analysis(self, task: AgentTask) -> TaskResult:
        """Ejecuta análisis de paquetes."""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self._execute_analysis_sync,
            task
        )
        
    def _execute_analysis_sync(self, task: AgentTask) -> TaskResult:
        """Ejecuta análisis de forma síncrona."""
        try:
            packages = task.data.get('packages', [])
            results = []
            
            for package in packages:
                analysis = self.analyzer.analyze_package(
                    package,
                    self.context.customer_profile,
                    self.context.sale_history
                )
                results.append(analysis)
                
            return TaskResult(
                success=True,
                data={'analysis_results': results},
                error=None
            )
        except Exception as e:
            logger.error(f"Error en análisis: {e}")
            return TaskResult(
                success=False,
                data=None,
                error=str(e)
            )
            
    def _process_results(
        self,
        results: List[TaskResult]
    ) -> TaskResult:
        """
        Procesa y combina resultados de múltiples tareas.
        """
        if not results:
            return TaskResult(
                success=False,
                data=None,
                error="No se obtuvieron resultados"
            )
            
        # Verificar si hubo errores críticos
        errors = [
            r.error for r in results
            if not r.success and r.error
        ]
        
        if errors:
            return TaskResult(
                success=False,
                data=None,
                error="; ".join(errors)
            )
            
        # Combinar datos de resultados
        combined_data = {}
        for result in results:
            if result.data:
                combined_data.update(result.data)
                
        return TaskResult(
            success=True,
            data=combined_data,
            error=None
        )
    
    def _update_state(self, result: TaskResult) -> None:
        """
        Actualiza el estado interno del agente.
        """
        if not result.success:
            return
            
        # Actualizar contexto con nuevos datos
        if result.data:
            self.context.update_from_result(result.data)
            
        # Limpiar colas de tareas completadas
        for priority in TaskPriority:
            self.task_queues[priority].clear()
            
    def optimize_performance(self) -> None:
        """
        Optimiza el rendimiento del agente.
        """
        # Obtener insights del observador
        insights = self.observer.get_latest_insights(min_priority=2)
        
        # Aplicar optimizaciones basadas en insights
        for insight in insights:
            if insight.type == InsightType.OPTIMIZATION:
                self._apply_optimization_insight(insight)
            elif insight.type == InsightType.ALERT:
                self._handle_alert_insight(insight)
                
        # Ajustar workers según carga
        system_health = self.observer.get_system_health()
        if system_health['overall_status'] == 'degraded':
            self.max_workers = min(self.max_workers + 2, 8)
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
        # Limpiar caché si rendimiento está degradado
        performance_metrics = system_health['performance_metrics']
        if performance_metrics['success_rate'] < 0.7:
            self.cache.cleanup()
            
        # Optimizar prioridades
        self._optimize_priorities()
        
    def _apply_optimization_insight(self, insight: AgentInsight) -> None:
        """
        Aplica optimizaciones basadas en insights.
        """
        if 'best_hours' in insight.data:
            # Ajustar prioridades según horario óptimo
            current_hour = datetime.now().hour
            if current_hour in insight.data['best_hours']:
                # Promover tareas en horario óptimo
                for task in self.task_queues[TaskPriority.MEDIUM]:
                    if not task.deadline:
                        self.task_queues[TaskPriority.HIGH].append(task)
                self.task_queues[TaskPriority.MEDIUM].clear()
                
    def _handle_alert_insight(self, insight: AgentInsight) -> None:
        """
        Maneja insights de tipo alerta.
        """
        if 'component_id' in insight.data:
            component = insight.data['component_id']
            if component == 'search':
                # Reducir carga en búsqueda
                self.cache.extend_ttl(category='search', extension=1800)
            elif component == 'analyze':
                # Simplificar análisis temporalmente
                self.analyzer.set_analysis_depth('basic')
                
    def get_system_status(self) -> Dict:
        """
        Obtiene estado completo del sistema.
        """
        # Obtener estado sintetizado del observador
        system_state = self.observer.synthesize_state()
        
        # Agregar métricas propias
        system_state.update({
            'tasks_pending': sum(len(q) for q in self.task_queues.values()),
            'cache_status': self.cache.get_status(),
            'worker_utilization': len(self.executor._threads) / self.max_workers
        })
        
        return system_state
        
    def get_insights_and_recommendations(self) -> Dict:
        """
        Obtiene insights y recomendaciones actuales.
        """
        insights = self.observer.get_latest_insights()
        
        return {
            'insights': [
                {
                    'type': i.type.value,
                    'priority': i.priority,
                    'description': i.description,
                    'recommendations': i.recommendations
                }
                for i in insights
            ],
            'system_health': self.observer.get_system_health(),
            'active_patterns': self.observer.patterns,
            'optimization_opportunities': [
                i for i in insights
                if i.type == InsightType.OPTIMIZATION
            ]
        }
