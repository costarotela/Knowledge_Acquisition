"""
Neo4j-based knowledge graph implementation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError

from ..base import BaseKnowledgeGraph

logger = logging.getLogger(__name__)

class Neo4jGraph(BaseKnowledgeGraph):
    """Neo4j-based knowledge graph implementation."""
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j"
    ):
        """Initialize Neo4j connection."""
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        
        # Initialize schema and constraints
        self._init_schema()
    
    def _init_schema(self):
        """Initialize Neo4j schema and constraints."""
        with self.driver.session(database=self.database) as session:
            try:
                # Create constraints
                session.run("""
                    CREATE CONSTRAINT concept_id IF NOT EXISTS
                    FOR (c:Concept) REQUIRE c.id IS UNIQUE
                """)
                
                session.run("""
                    CREATE CONSTRAINT relation_id IF NOT EXISTS
                    FOR ()-[r:RELATES_TO]-() REQUIRE r.id IS UNIQUE
                """)
            except Neo4jError as e:
                logger.error(f"Error initializing Neo4j schema: {e}")
    
    async def add_concept(self, concept: str, properties: Dict[str, Any]) -> str:
        """Add a concept node to the graph."""
        with self.driver.session(database=self.database) as session:
            try:
                result = session.run("""
                    MERGE (c:Concept {name: $concept})
                    ON CREATE SET 
                        c.id = randomUUID(),
                        c.created_at = datetime(),
                        c.properties = $properties
                    ON MATCH SET
                        c.properties = $properties,
                        c.updated_at = datetime()
                    RETURN c.id as id
                """, concept=concept, properties=properties)
                
                return result.single()["id"]
            except Neo4jError as e:
                logger.error(f"Error adding concept: {e}")
                raise
    
    async def add_relation(
        self,
        from_concept: str,
        to_concept: str,
        relation_type: str,
        properties: Dict[str, Any]
    ) -> str:
        """Add a relation between concepts."""
        with self.driver.session(database=self.database) as session:
            try:
                result = session.run("""
                    MATCH (from:Concept {name: $from_concept})
                    MATCH (to:Concept {name: $to_concept})
                    MERGE (from)-[r:RELATES_TO {type: $relation_type}]->(to)
                    ON CREATE SET 
                        r.id = randomUUID(),
                        r.created_at = datetime(),
                        r.properties = $properties
                    ON MATCH SET
                        r.properties = $properties,
                        r.updated_at = datetime()
                    RETURN r.id as id
                """, from_concept=from_concept,
                     to_concept=to_concept,
                     relation_type=relation_type,
                     properties=properties)
                
                return result.single()["id"]
            except Neo4jError as e:
                logger.error(f"Error adding relation: {e}")
                raise
    
    async def get_related_concepts(
        self,
        concept: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get concepts related to the given concept."""
        with self.driver.session(database=self.database) as session:
            try:
                query = """
                    MATCH (c:Concept {name: $concept})-[r:RELATES_TO]->(related:Concept)
                    WHERE $relation_type IS NULL OR r.type = $relation_type
                    RETURN related.name as name,
                           related.properties as properties,
                           r.type as relation_type,
                           r.properties as relation_properties
                """
                
                result = session.run(
                    query,
                    concept=concept,
                    relation_type=relation_type
                )
                
                return [dict(record) for record in result]
            except Neo4jError as e:
                logger.error(f"Error getting related concepts: {e}")
                raise
    
    async def search_concepts(self, query: str) -> List[Dict[str, Any]]:
        """Search for concepts in the graph."""
        with self.driver.session(database=self.database) as session:
            try:
                # Using full-text search if available, otherwise fallback to CONTAINS
                result = session.run("""
                    MATCH (c:Concept)
                    WHERE c.name CONTAINS $query
                    RETURN c.name as name,
                           c.properties as properties,
                           c.created_at as created_at
                    ORDER BY c.name
                """, query=query)
                
                return [dict(record) for record in result]
            except Neo4jError as e:
                logger.error(f"Error searching concepts: {e}")
                raise
    
    def close(self):
        """Close the Neo4j connection."""
        self.driver.close()
