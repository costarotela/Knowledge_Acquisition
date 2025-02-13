"""Módulo para el contexto del agente."""

from dataclasses import dataclass

@dataclass
class AgentContext:
    """Contexto del agente."""
    
    session_id: str
    language: str = "en"
