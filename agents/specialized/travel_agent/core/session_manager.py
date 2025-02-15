"""
Gestor de sesiones de venta interactivas.

Este módulo maneja el ciclo completo de una consulta de venta,
permitiendo refinamiento iterativo basado en feedback del vendedor.
"""

from typing import List, Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass, field

from .schemas import SalesQuery, Budget
from .analysis_engine import AnalysisEngine

if TYPE_CHECKING:
    from .sales_assistant import SalesAssistant

@dataclass
class SessionIteration:
    """Una iteración en la sesión de venta."""
    
    query: SalesQuery
    budget: Budget
    feedback: Dict
    timestamp: datetime = field(default_factory=datetime.now)
    
class SalesSession:
    """
    Sesión interactiva de venta que:
    1. Mantiene estado de la consulta
    2. Procesa feedback del vendedor
    3. Refina búsquedas iterativamente
    4. Registra historial de iteraciones
    5. Identifica mejores opciones
    """
    
    def __init__(
        self,
        sales_assistant: 'SalesAssistant',
        session_id: str,
        initial_query: SalesQuery
    ):
        self.assistant = sales_assistant
        self.session_id = session_id
        self.initial_query = initial_query
        self.current_query = initial_query
        self.iterations: List[SessionIteration] = []
        self.best_options: List[Dict] = []
        self.status = "active"
        self.logger = logging.getLogger(__name__)
        
    async def start_session(self) -> Budget:
        """Iniciar sesión con consulta inicial."""
        try:
            # Procesar consulta inicial
            budget = await self.assistant.process_sales_query(
                self.initial_query
            )
            
            # Registrar primera iteración
            self.iterations.append(
                SessionIteration(
                    query=self.initial_query,
                    budget=budget,
                    feedback={}
                )
            )
            
            # Actualizar mejores opciones
            self._update_best_options(budget)
            
            return budget
            
        except Exception as e:
            self.logger.error(f"Error iniciando sesión: {str(e)}")
            return Budget(
                status="error",
                message=f"Error iniciando sesión: {str(e)}"
            )
            
    async def iterate(
        self,
        feedback: Dict,
        parameter_updates: Optional[Dict] = None
    ) -> Budget:
        """
        Refinar búsqueda basado en feedback.
        
        Args:
            feedback: Feedback del vendedor
            parameter_updates: Nuevos parámetros de búsqueda
            
        Returns:
            Nuevo presupuesto
        """
        try:
            # Actualizar query con nuevos parámetros
            if parameter_updates:
                self.current_query = self._update_query(
                    parameter_updates
                )
                
            # Procesar nueva búsqueda
            budget = await self.assistant.process_sales_query(
                self.current_query
            )
            
            # Registrar iteración
            self.iterations.append(
                SessionIteration(
                    query=self.current_query,
                    budget=budget,
                    feedback=feedback
                )
            )
            
            # Actualizar mejores opciones
            self._update_best_options(budget)
            
            return budget
            
        except Exception as e:
            self.logger.error(f"Error en iteración: {str(e)}")
            return Budget(
                status="error",
                message=f"Error en iteración: {str(e)}"
            )
            
    def get_session_summary(self) -> Dict:
        """Obtener resumen de la sesión."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "iterations": len(self.iterations),
            "current_query": self.current_query,
            "best_options": self.best_options,
            "history": [
                {
                    "timestamp": it.timestamp,
                    "feedback": it.feedback,
                    "budget_status": it.budget.status
                }
                for it in self.iterations
            ]
        }
        
    def end_session(
        self,
        reason: str = "completed"
    ) -> Dict:
        """
        Finalizar sesión.
        
        Args:
            reason: Razón de finalización
            
        Returns:
            Resumen final de la sesión
        """
        self.status = "closed"
        
        return {
            **self.get_session_summary(),
            "end_reason": reason,
            "final_recommendations": self._generate_final_recommendations()
        }
        
    def _update_query(
        self,
        parameter_updates: Dict
    ) -> SalesQuery:
        """Actualizar query con nuevos parámetros."""
        updated_query = self.current_query
        
        # Actualizar preferencias
        if "preferences" in parameter_updates:
            updated_query.preferences = {
                **updated_query.preferences,
                **parameter_updates["preferences"]
            } if updated_query.preferences else parameter_updates["preferences"]
            
        # Actualizar criterios de búsqueda
        if "search_criteria" in parameter_updates:
            updated_query.search_criteria = {
                **updated_query.search_criteria,
                **parameter_updates["search_criteria"]
            } if updated_query.search_criteria else parameter_updates["search_criteria"]
            
        # Actualizar fechas si es necesario
        if "dates" in parameter_updates:
            updated_query.dates.update(parameter_updates["dates"])
            
        return updated_query
        
    def _update_best_options(self, budget: Budget):
        """Actualizar mejores opciones basado en nuevo presupuesto."""
        if not budget.options:
            return
            
        for name, package in budget.options.items():
            if not package:
                continue
                
            # Verificar si ya existe esta opción
            exists = False
            for option in self.best_options:
                if option["package_id"] == package.id:
                    exists = True
                    # Actualizar si el precio es mejor
                    if package.price < option["price"]:
                        option.update({
                            "price": package.price,
                            "iteration": len(self.iterations),
                            "timestamp": datetime.now()
                        })
                    break
                    
            if not exists:
                self.best_options.append({
                    "package_id": package.id,
                    "name": name,
                    "price": package.price,
                    "iteration": len(self.iterations),
                    "timestamp": datetime.now()
                })
                
        # Ordenar por precio
        self.best_options.sort(key=lambda x: x["price"])
        
    def _generate_final_recommendations(self) -> List[Dict]:
        """Generar recomendaciones finales."""
        recommendations = []
        
        # Analizar patrones en el feedback
        feedback_patterns = self._analyze_feedback_patterns()
        
        # Recomendar basado en mejores opciones
        if self.best_options:
            best_option = self.best_options[0]
            recommendations.append({
                "type": "best_value",
                "message": f"Mejor opción encontrada: {best_option['name']}",
                "package_id": best_option["package_id"],
                "iteration": best_option["iteration"]
            })
            
        # Recomendar basado en patrones de feedback
        for pattern in feedback_patterns:
            recommendations.append({
                "type": "feedback_pattern",
                "message": pattern["message"],
                "importance": pattern["importance"]
            })
            
        return recommendations
        
    def _analyze_feedback_patterns(self) -> List[Dict]:
        """Analizar patrones en el feedback del vendedor."""
        patterns = []
        
        # Recolectar todo el feedback
        all_feedback = [
            it.feedback for it in self.iterations
            if it.feedback
        ]
        
        if not all_feedback:
            return patterns
            
        # Analizar patrones de precio
        price_concerns = sum(
            1 for f in all_feedback
            if any(
                key in str(f).lower()
                for key in ["precio", "costo", "presupuesto"]
            )
        )
        
        if price_concerns > len(all_feedback) / 2:
            patterns.append({
                "type": "price_sensitivity",
                "message": "Alta sensibilidad al precio detectada",
                "importance": "high"
            })
            
        # Analizar patrones de preferencias
        preference_changes = sum(
            1 for i in range(1, len(self.iterations))
            if self.iterations[i].query.preferences != self.iterations[i-1].query.preferences
        )
        
        if preference_changes > len(self.iterations) / 2:
            patterns.append({
                "type": "preference_volatility",
                "message": "Preferencias cambiantes detectadas",
                "importance": "medium"
            })
            
        return patterns


class SessionManager:
    """
    Gestor global de sesiones de venta.
    
    Mantiene y coordina múltiples sesiones activas.
    """
    
    def __init__(self, sales_assistant: 'SalesAssistant'):
        self.assistant = sales_assistant
        self.active_sessions: Dict[str, SalesSession] = {}
        self.logger = logging.getLogger(__name__)
        
    async def create_session(
        self,
        initial_query: SalesQuery
    ) -> SalesSession:
        """Crear nueva sesión de venta."""
        session_id = self._generate_session_id()
        
        session = SalesSession(
            sales_assistant=self.assistant,
            session_id=session_id,
            initial_query=initial_query
        )
        
        self.active_sessions[session_id] = session
        await session.start_session()
        
        return session
        
    def get_session(
        self,
        session_id: str
    ) -> Optional[SalesSession]:
        """Obtener sesión por ID."""
        return self.active_sessions.get(session_id)
        
    def list_active_sessions(self) -> List[Dict]:
        """Listar sesiones activas."""
        return [
            {
                "session_id": session_id,
                "client": session.initial_query.client_name,
                "destination": session.initial_query.destination,
                "iterations": len(session.iterations),
                "status": session.status
            }
            for session_id, session in self.active_sessions.items()
            if session.status == "active"
        ]
        
    def end_session(
        self,
        session_id: str,
        reason: str = "completed"
    ) -> Dict:
        """Finalizar una sesión."""
        session = self.active_sessions.get(session_id)
        if not session:
            return {
                "status": "error",
                "message": f"Sesión {session_id} no encontrada"
            }
            
        summary = session.end_session(reason)
        
        # Mantener sesión en memoria por un tiempo
        # TODO: Implementar limpieza periódica
        
        return summary
        
    def _generate_session_id(self) -> str:
        """Generar ID único para la sesión."""
        from uuid import uuid4
        return f"session-{uuid4().hex[:8]}"
