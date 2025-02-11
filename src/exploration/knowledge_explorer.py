"""
Módulo para exploración y visualización del conocimiento.
Consolida la funcionalidad de:
- explore_concepts.py
- explore_knowledge.py
- knowledge_acquisition.py
- knowledge_viz.py
"""

from typing import Dict, List, Any, Optional
import logging
import json
from datetime import datetime

import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from wordcloud import WordCloud

from ..agent.models.rag_model import VideoKnowledge

logger = logging.getLogger(__name__)

class KnowledgeExplorer:
    """Explorador de conocimiento nutricional."""
    
    def __init__(self, knowledge_base_path: str):
        """
        Inicializa el explorador.
        
        Args:
            knowledge_base_path: Ruta al archivo JSON de la base de conocimiento
        """
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_base = self._load_knowledge_base()
        self.graph = self._build_knowledge_graph()
        
    def _load_knowledge_base(self) -> List[VideoKnowledge]:
        """Carga la base de conocimiento desde JSON."""
        try:
            with open(self.knowledge_base_path) as f:
                data = json.load(f)
            return [VideoKnowledge(**item) for item in data]
        except Exception as e:
            logger.error(f"Error cargando base de conocimiento: {e}")
            return []
            
    def _build_knowledge_graph(self) -> nx.Graph:
        """Construye grafo de conocimiento."""
        G = nx.Graph()
        
        # Agregar nodos y aristas
        for video in self.knowledge_base:
            # Agregar video como nodo
            G.add_node(video.title, 
                      type="video",
                      url=video.url,
                      channel=video.channel)
            
            # Agregar temas como nodos
            for topic in video.main_topics:
                G.add_node(topic, type="topic")
                G.add_edge(video.title, topic)
                
            # Agregar palabras clave como nodos
            for segment in video.segments:
                for keyword in segment["keywords"]:
                    G.add_node(keyword, type="keyword")
                    G.add_edge(video.title, keyword)
                    
        return G
        
    def analyze_topics(self) -> pd.DataFrame:
        """Analiza distribución de temas."""
        topics = []
        for video in self.knowledge_base:
            topics.extend(video.main_topics)
            
        df = pd.DataFrame(topics, columns=["topic"])
        topic_counts = df["topic"].value_counts()
        
        return pd.DataFrame({
            "topic": topic_counts.index,
            "count": topic_counts.values
        })
        
    def generate_wordcloud(self, 
                          width: int = 800, 
                          height: int = 400) -> WordCloud:
        """Genera nube de palabras."""
        # Concatenar todas las palabras clave
        text = ""
        for video in self.knowledge_base:
            for segment in video.segments:
                text += " ".join(segment["keywords"]) + " "
                
        # Crear y ajustar wordcloud
        wordcloud = WordCloud(
            width=width,
            height=height,
            background_color="white",
            colormap="viridis"
        )
        
        return wordcloud.generate(text)
        
    def plot_topic_distribution(self,
                              figsize: tuple = (10, 6)) -> None:
        """Grafica distribución de temas."""
        topic_df = self.analyze_topics()
        
        plt.figure(figsize=figsize)
        sns.barplot(data=topic_df,
                   x="count",
                   y="topic",
                   palette="viridis")
        plt.title("Distribución de Temas")
        plt.xlabel("Número de Videos")
        plt.ylabel("Tema")
        plt.tight_layout()
        
    def plot_knowledge_graph(self,
                           figsize: tuple = (12, 8)) -> None:
        """Visualiza grafo de conocimiento."""
        plt.figure(figsize=figsize)
        
        # Definir colores por tipo
        color_map = {
            "video": "#2ecc71",
            "topic": "#e74c3c",
            "keyword": "#3498db"
        }
        
        # Asignar colores a nodos
        node_colors = [color_map[self.graph.nodes[node]["type"]] 
                      for node in self.graph.nodes()]
        
        # Dibujar grafo
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph,
               pos=pos,
               node_color=node_colors,
               with_labels=True,
               node_size=1000,
               font_size=8)
               
        plt.title("Grafo de Conocimiento")
        plt.tight_layout()
        
    def find_related_content(self, 
                           query: str,
                           n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Encuentra contenido relacionado a una consulta.
        
        Args:
            query: Consulta de búsqueda
            n_results: Número de resultados a retornar
            
        Returns:
            Lista de videos relacionados con sus metadatos
        """
        # TODO: Implementar búsqueda semántica
        results = []
        query_terms = set(query.lower().split())
        
        for video in self.knowledge_base:
            # Calcular relevancia
            relevance = 0
            
            # Coincidencia en título
            title_terms = set(video.title.lower().split())
            relevance += len(query_terms & title_terms) * 2
            
            # Coincidencia en temas
            topic_terms = set(" ".join(video.main_topics).lower().split())
            relevance += len(query_terms & topic_terms) * 1.5
            
            # Coincidencia en palabras clave
            keywords = set()
            for segment in video.segments:
                keywords.update(k.lower() for k in segment["keywords"])
            relevance += len(query_terms & keywords)
            
            if relevance > 0:
                results.append({
                    "title": video.title,
                    "url": video.url,
                    "channel": video.channel,
                    "relevance": relevance,
                    "topics": video.main_topics,
                    "summary": video.summary
                })
                
        # Ordenar por relevancia
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:n_results]
        
    def export_statistics(self) -> Dict[str, Any]:
        """Exporta estadísticas de la base de conocimiento."""
        stats = {
            "total_videos": len(self.knowledge_base),
            "total_segments": sum(len(v.segments) for v in self.knowledge_base),
            "unique_topics": len(set(t for v in self.knowledge_base 
                                   for t in v.main_topics)),
            "unique_channels": len(set(v.channel for v in self.knowledge_base)),
            "avg_segments_per_video": sum(len(v.segments) for v in self.knowledge_base) / 
                                    len(self.knowledge_base) if self.knowledge_base else 0,
            "total_keywords": len(set(k for v in self.knowledge_base 
                                    for s in v.segments 
                                    for k in s["keywords"])),
            "last_updated": datetime.now().isoformat()
        }
        
        return stats
