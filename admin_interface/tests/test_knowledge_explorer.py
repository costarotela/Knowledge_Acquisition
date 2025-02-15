"""
Tests for the Knowledge Explorer module.
"""

import pytest
import networkx as nx
from ..pages.knowledge_explorer import KnowledgeGraph

def test_knowledge_graph_creation():
    """Test basic graph creation."""
    graph = KnowledgeGraph()
    assert isinstance(graph.graph, nx.Graph)
    assert len(graph.graph.nodes()) == 0
    assert len(graph.graph.edges()) == 0

def test_add_node():
    """Test adding nodes to the graph."""
    graph = KnowledgeGraph()
    
    # Agregar nodo con datos
    graph.add_node("test_node", {"type": "test"})
    
    assert "test_node" in graph.graph.nodes()
    assert graph.graph.nodes["test_node"]["type"] == "test"

def test_add_edge():
    """Test adding edges to the graph."""
    graph = KnowledgeGraph()
    
    # Agregar nodos
    graph.add_node("node1", {"type": "test"})
    graph.add_node("node2", {"type": "test"})
    
    # Agregar conexión
    graph.add_edge("node1", "node2", {"type": "test_connection"})
    
    assert ("node1", "node2") in graph.graph.edges()
    assert graph.graph.edges[("node1", "node2")]["type"] == "test_connection"

def test_visualize():
    """Test graph visualization."""
    graph = KnowledgeGraph()
    
    # Crear grafo de prueba
    graph.add_node("Python", {"type": "language"})
    graph.add_node("ML", {"type": "field"})
    graph.add_edge("Python", "ML", {"type": "used_in"})
    
    # Verificar que se crea la visualización
    fig = graph.visualize()
    assert fig is not None
    assert len(fig.data) == 2  # Nodos y conexiones
