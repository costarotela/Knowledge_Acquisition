"""
Neo4j implementation of the graph store.
Provides graph-based storage and querying capabilities.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import json
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError

from .base import GraphStore
from ..models import KnowledgeEntity, Relation


class Neo4jStore(GraphStore):
    """Neo4j-based graph store implementation."""
    
    def __init__(
        self,
        uri: str = "neo4j://localhost:7687",
        username: str = "neo4j",
        password: str = "password"
    ):
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri, auth=(username, password)
        )
    
    async def close(self):
        """Close the Neo4j connection."""
        await self.driver.close()
    
    async def add_entity(self, entity: KnowledgeEntity) -> bool:
        """Add entity node to Neo4j."""
        async with self.driver.session() as session:
            try:
                # Create entity node
                query = """
                CREATE (e:Entity {
                    id: $id,
                    content_type: $content_type,
                    confidence: $confidence,
                    created_at: datetime($created_at),
                    updated_at: datetime($updated_at),
                    version: $version,
                    tags: $tags,
                    metadata: $metadata
                })
                """
                
                params = {
                    "id": str(entity.id),
                    "content_type": entity.content_type.value,
                    "confidence": entity.confidence,
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat(),
                    "version": entity.version,
                    "tags": entity.tags,
                    "metadata": json.dumps(entity.metadata.dict())
                }
                
                await session.run(query, params)
                return True
            except Neo4jError as e:
                print(f"Error adding entity to Neo4j: {e}")
                return False
    
    async def add_relation(self, source_id: UUID, relation: Relation) -> bool:
        """Add relation between entities."""
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (source:Entity {id: $source_id})
                MATCH (target:Entity {id: $target_id})
                CREATE (source)-[r:RELATES {
                    type: $relation_type,
                    confidence: $confidence,
                    metadata: $metadata
                }]->(target)
                """
                
                params = {
                    "source_id": str(source_id),
                    "target_id": str(relation.target_id),
                    "relation_type": relation.relation_type.value,
                    "confidence": relation.confidence,
                    "metadata": json.dumps(relation.metadata)
                }
                
                await session.run(query, params)
                return True
            except Neo4jError as e:
                print(f"Error adding relation to Neo4j: {e}")
                return False
    
    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        """Retrieve entity from Neo4j."""
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (e:Entity {id: $id})
                RETURN e
                """
                
                result = await session.run(query, {"id": str(entity_id)})
                record = await result.single()
                
                if not record:
                    return None
                
                node = record["e"]
                return KnowledgeEntity(
                    id=UUID(node["id"]),
                    content_type=node["content_type"],
                    confidence=node["confidence"],
                    created_at=node["created_at"],
                    updated_at=node["updated_at"],
                    version=node["version"],
                    tags=node["tags"],
                    metadata=json.loads(node["metadata"])
                )
            except Neo4jError as e:
                print(f"Error retrieving entity from Neo4j: {e}")
                return None
    
    async def get_relations(
        self,
        entity_id: UUID,
        relation_types: Optional[List[str]] = None
    ) -> List[Relation]:
        """Get all relations for an entity."""
        async with self.driver.session() as session:
            try:
                # Build query based on whether relation_types is provided
                if relation_types:
                    query = """
                    MATCH (source:Entity {id: $id})-[r:RELATES]->(target:Entity)
                    WHERE r.type IN $relation_types
                    RETURN r, target.id as target_id
                    """
                    params = {"id": str(entity_id), "relation_types": relation_types}
                else:
                    query = """
                    MATCH (source:Entity {id: $id})-[r:RELATES]->(target:Entity)
                    RETURN r, target.id as target_id
                    """
                    params = {"id": str(entity_id)}
                
                result = await session.run(query, params)
                relations = []
                
                async for record in result:
                    rel = record["r"]
                    relations.append(Relation(
                        relation_type=rel["type"],
                        target_id=UUID(record["target_id"]),
                        confidence=rel["confidence"],
                        metadata=json.loads(rel["metadata"])
                    ))
                
                return relations
            except Neo4jError as e:
                print(f"Error retrieving relations from Neo4j: {e}")
                return []
    
    async def search_path(
        self,
        start_id: UUID,
        end_id: UUID,
        max_depth: int = 3
    ) -> List[List[Relation]]:
        """Find paths between two entities."""
        async with self.driver.session() as session:
            try:
                query = """
                MATCH path = (start:Entity {id: $start_id})
                -[:RELATES*1..{max_depth}]->
                (end:Entity {id: $end_id})
                RETURN path
                """
                
                result = await session.run(query, {
                    "start_id": str(start_id),
                    "end_id": str(end_id),
                    "max_depth": max_depth
                })
                
                paths = []
                async for record in result:
                    path = record["path"]
                    relations = []
                    
                    for rel in path.relationships:
                        relations.append(Relation(
                            relation_type=rel["type"],
                            target_id=UUID(rel.end_node["id"]),
                            confidence=rel["confidence"],
                            metadata=json.loads(rel["metadata"])
                        ))
                    
                    paths.append(relations)
                
                return paths
            except Neo4jError as e:
                print(f"Error searching paths in Neo4j: {e}")
                return []
    
    async def update_entity(self, entity: KnowledgeEntity) -> bool:
        """Update entity in Neo4j."""
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (e:Entity {id: $id})
                SET e.content_type = $content_type,
                    e.confidence = $confidence,
                    e.updated_at = datetime($updated_at),
                    e.version = $version,
                    e.tags = $tags,
                    e.metadata = $metadata
                """
                
                params = {
                    "id": str(entity.id),
                    "content_type": entity.content_type.value,
                    "confidence": entity.confidence,
                    "updated_at": entity.updated_at.isoformat(),
                    "version": entity.version,
                    "tags": entity.tags,
                    "metadata": json.dumps(entity.metadata.dict())
                }
                
                await session.run(query, params)
                return True
            except Neo4jError as e:
                print(f"Error updating entity in Neo4j: {e}")
                return False
    
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete entity and its relations from Neo4j."""
        async with self.driver.session() as session:
            try:
                # Delete all relations first
                query1 = """
                MATCH (e:Entity {id: $id})-[r]-()
                DELETE r
                """
                await session.run(query1, {"id": str(entity_id)})
                
                # Then delete the entity
                query2 = """
                MATCH (e:Entity {id: $id})
                DELETE e
                """
                await session.run(query2, {"id": str(entity_id)})
                
                return True
            except Neo4jError as e:
                print(f"Error deleting entity from Neo4j: {e}")
                return False
