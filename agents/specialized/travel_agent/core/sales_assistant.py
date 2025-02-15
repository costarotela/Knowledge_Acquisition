"""
Asistente AI para vendedores de turismo.

Este módulo implementa un asistente inteligente que:
1. Procesa instrucciones del vendedor
2. Extrae parámetros relevantes
3. Busca y analiza paquetes
4. Genera presupuestos personalizados
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime
import json
from pathlib import Path
from .schemas import SalesQuery, Budget, SalesReport, TravelPackage
from .session_manager import SessionManager
from .analysis_engine import AnalysisEngine, AnalysisResult
from .agent import TravelAgent

class SalesAssistant:
    """Asistente de ventas con capacidades de análisis avanzado."""
    
    def __init__(
        self,
        agent: TravelAgent,
        templates_dir: Optional[Path] = None
    ):
        self.agent = agent
        self.session_manager = SessionManager()
        self.analysis_engine = AnalysisEngine(
            browser_manager=agent.browser_manager
        )
        self.templates_dir = templates_dir or Path("config/templates")
        self.logger = logging.getLogger(__name__)
        
    async def start_interaction(
        self,
        query: SalesQuery
    ) -> Dict:
        """
        Iniciar una nueva interacción de venta.
        
        Args:
            query: Consulta inicial del vendedor
            
        Returns:
            Resultado inicial con ID de sesión
        """
        try:
            # Crear sesión
            session_id = self.session_manager.create_session(query)
            
            # Buscar paquetes
            packages = await self.agent.search_packages(
                destination=query.destination,
                dates=query.dates,
                **query.preferences
            )
            
            if not packages:
                return {
                    "status": "error",
                    "message": "No se encontraron paquetes",
                    "session_id": session_id
                }
                
            # Analizar paquetes
            analysis = await self.analysis_engine.analyze_packages(
                query,
                packages
            )
            
            # Generar presupuesto inicial
            budget = self._generate_budget(
                query,
                analysis,
                is_refined=False
            )
            
            # Guardar estado
            self.session_manager.update_session(
                session_id,
                {
                    "current_analysis": analysis,
                    "current_budget": budget,
                    "interaction_count": 1
                }
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "budget": budget,
                "insights": analysis.insights
            }
            
        except Exception as e:
            self.logger.error(f"Error en interacción: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def refine_search(
        self,
        session_id: str,
        feedback: Dict,
        parameter_updates: Optional[Dict] = None
    ) -> Dict:
        """
        Refinar búsqueda basado en feedback.
        
        Args:
            session_id: ID de sesión
            feedback: Feedback del vendedor
            parameter_updates: Actualizaciones a parámetros
            
        Returns:
            Nuevo resultado refinado
        """
        try:
            # Obtener estado actual
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ValueError("Sesión no encontrada")
                
            query = session["query"]
            
            # Actualizar parámetros
            if parameter_updates:
                query.preferences.update(parameter_updates)
                
            # Aplicar refinamientos basados en feedback
            refined_params = self._process_feedback(
                feedback,
                session["current_analysis"]
            )
            query.preferences.update(refined_params)
            
            # Nueva búsqueda
            packages = await self.agent.search_packages(
                destination=query.destination,
                dates=query.dates,
                **query.preferences
            )
            
            if not packages:
                return {
                    "status": "error",
                    "message": "No se encontraron paquetes",
                    "session_id": session_id
                }
                
            # Nuevo análisis
            analysis = await self.analysis_engine.analyze_packages(
                query,
                packages
            )
            
            # Generar presupuesto refinado
            budget = self._generate_budget(
                query,
                analysis,
                is_refined=True
            )
            
            # Actualizar estado
            session["current_analysis"] = analysis
            session["current_budget"] = budget
            session["interaction_count"] += 1
            self.session_manager.update_session(session_id, session)
            
            return {
                "status": "success",
                "session_id": session_id,
                "budget": budget,
                "insights": analysis.insights,
                "changes": self._summarize_changes(
                    session["previous_analysis"],
                    analysis
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error en refinamiento: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    def end_interaction(
        self,
        session_id: str,
        reason: str
    ) -> SalesReport:
        """
        Finalizar interacción y generar reporte.
        
        Args:
            session_id: ID de sesión
            reason: Razón de finalización
            
        Returns:
            Reporte de la interacción
        """
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ValueError("Sesión no encontrada")
                
            # Generar reporte
            report = SalesReport(
                query=session["query"],
                final_budget=session["current_budget"],
                interaction_count=session["interaction_count"],
                end_reason=reason,
                insights=session["current_analysis"].insights,
                metrics=session["current_analysis"].metrics
            )
            
            # Cerrar sesión
            self.session_manager.close_session(session_id)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error finalizando: {str(e)}")
            raise
            
    def _generate_budget(
        self,
        query: SalesQuery,
        analysis: AnalysisResult,
        is_refined: bool
    ) -> Budget:
        """Generar presupuesto basado en análisis."""
        try:
            # Cargar template
            template_path = self.templates_dir / "default.json"
            with open(template_path) as f:
                template = json.load(f)
                
            # Seleccionar opciones
            recommendations = analysis.recommendations[:3]
            if not recommendations:
                raise ValueError("Sin recomendaciones disponibles")
                
            # Construir presupuesto
            budget = Budget(
                client_name=query.client_name,
                destination=query.destination,
                dates=query.dates,
                recommended_package=recommendations[0],
                alternative_packages=recommendations[1:],
                price_analysis={
                    "mean": analysis.metrics["price_mean"],
                    "min": analysis.metrics["price_min"],
                    "max": analysis.metrics["price_max"]
                },
                value_insights=analysis.insights.get("valor", ""),
                seasonal_info=analysis.insights.get("temporada", ""),
                is_refined=is_refined,
                generated_at=datetime.now(),
                template=template
            )
            
            return budget
            
        except Exception as e:
            self.logger.error(f"Error generando presupuesto: {str(e)}")
            raise
            
    def _process_feedback(
        self,
        feedback: Dict,
        current_analysis: AnalysisResult
    ) -> Dict:
        """Procesar feedback y generar refinamientos."""
        refinements = {}
        
        # Procesar comentarios sobre precio
        if "precio" in feedback:
            comment = feedback["precio"].lower()
            current_mean = current_analysis.metrics["price_mean"]
            
            if "alto" in comment:
                refinements["max_budget"] = current_mean * 0.8
            elif "bajo" in comment:
                refinements["min_budget"] = current_mean * 1.2
                
        # Procesar comentarios sobre duración
        if "duracion" in feedback:
            comment = feedback["duracion"].lower()
            current_mean = current_analysis.metrics["duration_mean"]
            
            if "corta" in comment:
                refinements["min_nights"] = current_mean + 2
            elif "larga" in comment:
                refinements["max_nights"] = current_mean - 2
                
        # Procesar comentarios sobre actividades
        if "actividades" in feedback:
            current_activities = set()
            for p in current_analysis.recommendations:
                current_activities.update(p.activities)
                
            if isinstance(feedback["actividades"], list):
                refinements["activities"] = feedback["actividades"]
            else:
                comment = feedback["actividades"].lower()
                if "mas" in comment:
                    refinements["min_activities"] = 5
                elif "menos" in comment:
                    refinements["max_activities"] = 3
                    
        return refinements
        
    def _summarize_changes(
        self,
        previous: AnalysisResult,
        current: AnalysisResult
    ) -> Dict:
        """Resumir cambios entre análisis."""
        if not previous:
            return {}
            
        changes = {}
        
        # Cambios en precios
        prev_mean = previous.metrics["price_mean"]
        curr_mean = current.metrics["price_mean"]
        price_change = (curr_mean - prev_mean) / prev_mean * 100
        
        if abs(price_change) >= 5:
            changes["precio_medio"] = {
                "anterior": prev_mean,
                "actual": curr_mean,
                "variacion": f"{price_change:.1f}%"
            }
            
        # Cambios en opciones
        prev_ids = {p.id for p in previous.recommendations}
        curr_ids = {p.id for p in current.recommendations}
        new_options = len(curr_ids - prev_ids)
        
        if new_options > 0:
            changes["nuevas_opciones"] = new_options
            
        # Cambios en segmentos
        for segment, packages in current.segments.items():
            if (
                segment in previous.segments and
                len(packages) != len(previous.segments[segment])
            ):
                changes[f"segment_{segment}"] = {
                    "anterior": len(previous.segments[segment]),
                    "actual": len(packages)
                }
                
        return changes
