"""
Integrator module for connecting multimodal alignment with hybrid storage.
"""

from typing import List, Dict, Optional, Union, Tuple
import torch
import asyncio
from pathlib import Path
import json
import logging
from datetime import datetime

from ..knowledge_base.models import KnowledgeEntity, ContentType
from ..knowledge_base.storage.base import HybridStore
from .alignment import CrossModalAlignment
from .utils import (
    process_audio,
    process_image,
    save_embeddings,
    load_embeddings
)

logger = logging.getLogger(__name__)


class MultimodalIntegrator:
    """
    Integrates multimodal alignment with hybrid storage system.
    Handles caching, batch processing, and storage optimization.
    """
    
    def __init__(
        self,
        store: HybridStore,
        alignment: CrossModalAlignment,
        cache_dir: Union[str, Path] = "./cache/embeddings",
        batch_size: int = 32
    ):
        self.store = store
        self.alignment = alignment
        self.cache_dir = Path(cache_dir)
        self.batch_size = batch_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding cache
        self._embedding_cache: Dict[str, torch.Tensor] = {}
        self._cache_metadata: Dict[str, Dict] = {}
    
    async def process_entity(
        self,
        entity: KnowledgeEntity,
        force_recompute: bool = False
    ) -> KnowledgeEntity:
        """
        Process a knowledge entity through the multimodal alignment system.
        
        Args:
            entity: Knowledge entity to process
            force_recompute: Whether to force recomputation of embeddings
        
        Returns:
            Processed entity with aligned embeddings
        """
        cache_key = f"{entity.id}_{entity.version}"
        
        # Check cache first
        if not force_recompute and await self._check_cache(cache_key):
            entity.embeddings["aligned"] = await self._load_from_cache(cache_key)
            return entity
        
        # Process based on content type
        if entity.content_type == ContentType.TEXT:
            embedding = await self._process_text(entity)
        elif entity.content_type == ContentType.IMAGE:
            embedding = await self._process_image(entity)
        elif entity.content_type == ContentType.AUDIO:
            embedding = await self._process_audio(entity)
        else:
            raise ValueError(f"Unsupported content type: {entity.content_type}")
        
        # Store aligned embedding
        entity.embeddings["aligned"] = embedding
        
        # Cache result
        await self._cache_embedding(cache_key, embedding, {
            "content_type": entity.content_type,
            "processed_at": datetime.utcnow().isoformat(),
            "entity_version": entity.version
        })
        
        return entity
    
    async def batch_process(
        self,
        entities: List[KnowledgeEntity],
        force_recompute: bool = False
    ) -> List[KnowledgeEntity]:
        """Process multiple entities in batches."""
        results = []
        for i in range(0, len(entities), self.batch_size):
            batch = entities[i:i + self.batch_size]
            # Process batch concurrently
            tasks = [
                self.process_entity(entity, force_recompute)
                for entity in batch
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        return results
    
    async def update_store(
        self,
        entities: List[KnowledgeEntity]
    ) -> None:
        """Update hybrid store with processed entities."""
        # Update vector store
        await self.store.vector_store.add_entities(entities)
        
        # Update graph store
        await self.store.graph_store.add_entities(entities)
        
        # Update relations in graph store
        for entity in entities:
            if entity.relations:
                await self.store.graph_store.add_relations(
                    entity.id,
                    entity.relations
                )
    
    async def _process_text(self, entity: KnowledgeEntity) -> torch.Tensor:
        """Process text content."""
        return await asyncio.to_thread(
            self.alignment.align,
            text=entity.content
        )
    
    async def _process_image(self, entity: KnowledgeEntity) -> torch.Tensor:
        """Process image content."""
        image = await asyncio.to_thread(
            process_image,
            entity.content
        )
        return await asyncio.to_thread(
            self.alignment.align,
            image=image
        )
    
    async def _process_audio(self, entity: KnowledgeEntity) -> torch.Tensor:
        """Process audio content."""
        audio, sr = await asyncio.to_thread(
            process_audio,
            entity.content
        )
        return await asyncio.to_thread(
            self.alignment.align,
            audio=audio,
            sample_rate=sr
        )
    
    async def _check_cache(self, key: str) -> bool:
        """Check if embedding exists in cache."""
        # Check memory cache first
        if key in self._embedding_cache:
            return True
        
        # Check disk cache
        cache_file = self.cache_dir / f"{key}.npz"
        return cache_file.exists()
    
    async def _load_from_cache(self, key: str) -> torch.Tensor:
        """Load embedding from cache."""
        # Try memory cache first
        if key in self._embedding_cache:
            return self._embedding_cache[key]
        
        # Load from disk cache
        cache_file = self.cache_dir / f"{key}.npz"
        embedding, metadata = await asyncio.to_thread(
            load_embeddings,
            cache_file
        )
        
        # Update memory cache
        embedding_tensor = torch.from_numpy(embedding)
        self._embedding_cache[key] = embedding_tensor
        self._cache_metadata[key] = metadata
        
        return embedding_tensor
    
    async def _cache_embedding(
        self,
        key: str,
        embedding: torch.Tensor,
        metadata: Dict
    ) -> None:
        """Cache embedding in memory and on disk."""
        # Update memory cache
        self._embedding_cache[key] = embedding
        self._cache_metadata[key] = metadata
        
        # Save to disk cache
        cache_file = self.cache_dir / f"{key}.npz"
        await asyncio.to_thread(
            save_embeddings,
            embedding.cpu(),
            cache_file,
            metadata
        )
    
    def clear_cache(self, older_than: Optional[datetime] = None) -> None:
        """
        Clear embedding cache.
        
        Args:
            older_than: If provided, only clear cache entries older than this date
        """
        # Clear memory cache
        if older_than is None:
            self._embedding_cache.clear()
            self._cache_metadata.clear()
        else:
            keys_to_remove = []
            for key, metadata in self._cache_metadata.items():
                processed_at = datetime.fromisoformat(metadata["processed_at"])
                if processed_at < older_than:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._embedding_cache[key]
                del self._cache_metadata[key]
        
        # Clear disk cache
        if older_than is None:
            for cache_file in self.cache_dir.glob("*.npz"):
                cache_file.unlink()
        else:
            for cache_file in self.cache_dir.glob("*.npz"):
                embedding, metadata = load_embeddings(cache_file)
                processed_at = datetime.fromisoformat(metadata["processed_at"])
                if processed_at < older_than:
                    cache_file.unlink()
