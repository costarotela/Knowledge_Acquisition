"""
Knowledge Explorer module for visualizing and exploring the knowledge base.
"""

import streamlit as st
from typing import Dict, List
import networkx as nx
import plotly.graph_objects as go

class KnowledgeGraph:
    """Visualizador de grafo de conocimiento."""
    
    def __init__(self):
        self.graph = nx.Graph()
    
    def add_node(self, node_id: str, data: Dict):
        """Agregar nodo al grafo."""
        self.graph.add_node(node_id, **data)
    
    def add_edge(self, source: str, target: str, data: Dict):
        """Agregar conexión entre nodos."""
        self.graph.add_edge(source, target, **data)
    
    def visualize(self) -> go.Figure:
        """Crear visualización del grafo."""
        pos = nx.spring_layout(self.graph)
        
        # Crear figura
        fig = go.Figure()
        
        # Agregar nodos
        node_x = [pos[node][0] for node in self.graph.nodes()]
        node_y = [pos[node][1] for node in self.graph.nodes()]
        
        fig.add_trace(go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=list(self.graph.nodes()),
            textposition="bottom center",
            name="Nodes"
        ))
        
        # Agregar conexiones
        edge_x = []
        edge_y = []
        for edge in self.graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
        fig.add_trace(go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=0.5, color="#888"),
            name="Edges"
        ))
        
        # Configurar layout
        fig.update_layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        
        return fig

def main():
    """Página principal del Knowledge Explorer."""
    st.title("Knowledge Explorer")
    
    # Crear grafo de ejemplo
    graph = KnowledgeGraph()
    
    # Agregar algunos nodos y conexiones de ejemplo
    graph.add_node("Python", {"type": "language"})
    graph.add_node("Machine Learning", {"type": "field"})
    graph.add_node("Data Science", {"type": "field"})
    
    graph.add_edge("Python", "Machine Learning", {"type": "used_in"})
    graph.add_edge("Python", "Data Science", {"type": "used_in"})
    graph.add_edge("Machine Learning", "Data Science", {"type": "related_to"})
    
    # Mostrar visualización
    st.plotly_chart(graph.visualize(), use_container_width=True)
    
    # Controles
    st.sidebar.title("Explorer Controls")
    
    # Filtros
    st.sidebar.subheader("Filters")
    node_types = st.sidebar.multiselect(
        "Node Types",
        ["language", "field", "tool", "concept"]
    )
    
    # Búsqueda
    st.sidebar.subheader("Search")
    search_query = st.sidebar.text_input("Search nodes")
    
    # Estadísticas
    st.sidebar.subheader("Statistics")
    st.sidebar.metric("Total Nodes", len(graph.graph.nodes()))
    st.sidebar.metric("Total Connections", len(graph.graph.edges()))

if __name__ == "__main__":
    main()