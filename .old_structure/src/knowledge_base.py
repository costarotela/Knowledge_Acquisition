from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from pathlib import Path
import sqlite3
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self, db_path: str = "knowledge_base.db", embeddings_model: str = "all-MiniLM-L6-v2"):
        """
        Inicializa la base de conocimientos.
        
        Args:
            db_path: Ruta al archivo SQLite
            embeddings_model: Modelo de embeddings a usar
        """
        self.db_path = db_path
        self.encoder = SentenceTransformer(embeddings_model)
        self._init_database()
    
    def _init_database(self):
        """Inicializa la estructura de la base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT,
                    concept TEXT,
                    content TEXT,
                    evidence_score REAL,
                    novelty_score REAL,
                    references TEXT,
                    embedding BLOB,
                    category TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    knowledge_id INTEGER,
                    citation TEXT,
                    FOREIGN KEY(knowledge_id) REFERENCES knowledge_items(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    target_id INTEGER,
                    relationship_type TEXT,
                    confidence_score REAL,
                    FOREIGN KEY(source_id) REFERENCES knowledge_items(id),
                    FOREIGN KEY(target_id) REFERENCES knowledge_items(id)
                )
            """)
    
    def add_knowledge(self, 
                     source_url: str,
                     concepts: List[str],
                     content: str,
                     evidence_score: float,
                     novelty_score: float,
                     references: List[str],
                     category: str) -> None:
        """
        Añade nuevo conocimiento a la base de datos.
        
        Args:
            source_url: URL de origen del conocimiento
            concepts: Lista de conceptos clave
            content: Contenido del conocimiento
            evidence_score: Puntuación de evidencia científica
            novelty_score: Puntuación de novedad
            references: Lista de referencias
            category: Categoría del conocimiento
        """
        # Generar embedding para el contenido
        embedding = self.encoder.encode(content)
        
        with sqlite3.connect(self.db_path) as conn:
            for concept in concepts:
                cursor = conn.execute(
                    """
                    INSERT INTO knowledge_items 
                    (source_url, concept, content, evidence_score, novelty_score, 
                     references, embedding, category) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (source_url, concept, content, evidence_score, novelty_score,
                     json.dumps(references), embedding.tobytes(), category)
                )
                
                knowledge_id = cursor.lastrowid
                
                # Añadir referencias
                for ref in references:
                    conn.execute(
                        "INSERT INTO citations (knowledge_id, citation) VALUES (?, ?)",
                        (knowledge_id, ref)
                    )
        
        # Buscar y establecer relaciones con conocimiento existente
        self._establish_relationships(knowledge_id, content, concepts)
    
    def _establish_relationships(self, 
                               knowledge_id: int, 
                               content: str, 
                               concepts: List[str]) -> None:
        """
        Establece relaciones entre el nuevo conocimiento y el existente.
        """
        # Obtener embeddings del nuevo contenido
        new_embedding = self.encoder.encode(content)
        
        with sqlite3.connect(self.db_path) as conn:
            # Obtener todos los items existentes
            cursor = conn.execute("SELECT id, embedding FROM knowledge_items WHERE id != ?", (knowledge_id,))
            
            for row in cursor:
                existing_id = row[0]
                existing_embedding = np.frombuffer(row[1])
                
                # Calcular similitud coseno
                similarity = np.dot(new_embedding, existing_embedding) / \
                           (np.linalg.norm(new_embedding) * np.linalg.norm(existing_embedding))
                
                # Si la similitud es alta, crear una relación
                if similarity > 0.7:
                    conn.execute(
                        """
                        INSERT INTO relationships 
                        (source_id, target_id, relationship_type, confidence_score)
                        VALUES (?, ?, ?, ?)
                        """,
                        (knowledge_id, existing_id, "related", float(similarity))
                    )
    
    def query_knowledge(self, 
                       query: str, 
                       category: Optional[str] = None,
                       min_evidence_score: float = 0.0,
                       limit: int = 5) -> List[Dict[str, Any]]:
        """
        Busca conocimiento relevante basado en una consulta.
        
        Args:
            query: Consulta de búsqueda
            category: Filtrar por categoría
            min_evidence_score: Puntuación mínima de evidencia
            limit: Número máximo de resultados
            
        Returns:
            Lista de items de conocimiento relevantes
        """
        # Generar embedding para la consulta
        query_embedding = self.encoder.encode(query)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.create_function("cosine_similarity", 2, self._cosine_similarity_sqlite)
            
            sql = """
                SELECT 
                    id, concept, content, evidence_score, novelty_score,
                    cosine_similarity(embedding, ?) as similarity
                FROM knowledge_items
                WHERE evidence_score >= ?
            """
            params = [query_embedding.tobytes(), min_evidence_score]
            
            if category:
                sql += " AND category = ?"
                params.append(category)
            
            sql += " ORDER BY similarity DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            
            results = []
            for row in cursor:
                item = {
                    "id": row[0],
                    "concept": row[1],
                    "content": row[2],
                    "evidence_score": row[3],
                    "novelty_score": row[4],
                    "similarity": row[5]
                }
                
                # Obtener referencias
                citations = conn.execute(
                    "SELECT citation FROM citations WHERE knowledge_id = ?",
                    (row[0],)
                ).fetchall()
                item["references"] = [c[0] for c in citations]
                
                # Obtener relaciones
                relationships = conn.execute(
                    """
                    SELECT t.concept, r.relationship_type, r.confidence_score
                    FROM relationships r
                    JOIN knowledge_items t ON r.target_id = t.id
                    WHERE r.source_id = ?
                    """,
                    (row[0],)
                ).fetchall()
                item["relationships"] = [
                    {"concept": r[0], "type": r[1], "confidence": r[2]}
                    for r in relationships
                ]
                
                results.append(item)
            
            return results
    
    @staticmethod
    def _cosine_similarity_sqlite(embedding1_bytes, embedding2_bytes):
        """Función auxiliar para calcular similitud coseno en SQLite."""
        v1 = np.frombuffer(embedding1_bytes)
        v2 = np.frombuffer(embedding2_bytes)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen del conocimiento almacenado.
        
        Returns:
            Dict con estadísticas sobre el conocimiento almacenado
        """
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total de items
            stats["total_items"] = conn.execute(
                "SELECT COUNT(*) FROM knowledge_items"
            ).fetchone()[0]
            
            # Promedio de scores
            avg_scores = conn.execute("""
                SELECT 
                    AVG(evidence_score) as avg_evidence,
                    AVG(novelty_score) as avg_novelty
                FROM knowledge_items
            """).fetchone()
            stats["avg_evidence_score"] = avg_scores[0]
            stats["avg_novelty_score"] = avg_scores[1]
            
            # Distribución por categorías
            categories = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM knowledge_items
                GROUP BY category
            """).fetchall()
            stats["category_distribution"] = {
                cat: count for cat, count in categories
            }
            
            # Total de relaciones
            stats["total_relationships"] = conn.execute(
                "SELECT COUNT(*) FROM relationships"
            ).fetchone()[0]
            
            return stats
