from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import numpy as np
from pydantic import BaseModel
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from dotenv import load_dotenv

load_dotenv()

class VectorDocument(BaseModel):
    """Modelo para documentos vectorizados."""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

class VectorStore:
    """Clase para manejar el almacenamiento y búsqueda de vectores."""
    
    def __init__(self, index_name: str = "knowledge_base"):
        """Inicializa el almacenamiento vectorial."""
        self.index_name = index_name
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        # Inicializar o cargar el índice FAISS
        self.vector_store = self._load_or_create_store()
    
    def _load_or_create_store(self) -> FAISS:
        """Carga o crea un nuevo almacén vectorial."""
        index_path = f"indexes/{self.index_name}"
        if os.path.exists(index_path):
            return FAISS.load_local(
                index_path,
                self.embeddings
            )
        return FAISS.from_documents(
            [],
            self.embeddings
        )
    
    async def add_documents(self, documents: List[VectorDocument]) -> None:
        """Agrega documentos al almacén vectorial."""
        # Convertir a formato de Langchain
        langchain_docs = []
        for doc in documents:
            metadata = doc.metadata.copy()
            metadata["timestamp"] = datetime.now().isoformat()
            
            langchain_docs.append(
                Document(
                    page_content=doc.content,
                    metadata=metadata
                )
            )
        
        # Agregar al almacén vectorial
        self.vector_store.add_documents(langchain_docs)
        
        # Guardar el índice
        os.makedirs("indexes", exist_ok=True)
        self.vector_store.save_local(f"indexes/{self.index_name}")
    
    async def search(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos similares a la consulta.
        
        Args:
            query: Texto de búsqueda
            k: Número de resultados a retornar
            threshold: Umbral de similitud (0-1)
        
        Returns:
            Lista de documentos similares con sus scores
        """
        # Realizar búsqueda
        docs_and_scores = self.vector_store.similarity_search_with_score(
            query,
            k=k
        )
        
        # Filtrar y formatear resultados
        results = []
        for doc, score in docs_and_scores:
            if score >= threshold:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    async def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> None:
        """Elimina documentos que coincidan con el filtro de metadatos."""
        self.vector_store.delete(metadata_filter)
        # Guardar cambios
        self.vector_store.save_local(f"indexes/{self.index_name}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del almacén vectorial."""
        return {
            "total_documents": len(self.vector_store.docstore._dict),
            "index_name": self.index_name,
            "embedding_dimension": self.vector_store.index.d
        }
