"""
Modelo RAG (Retrieval-Augmented Generation) para nutrición.
Consolida la funcionalidad de los módulos:
- agentic_rag.py
- agentix_rag.py  
- knowledge_rag.py
- rag_system.py
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class VideoKnowledge(BaseModel):
    """Conocimiento estructurado extraído de un video."""
    title: str
    channel: str
    url: str
    segments: List[Dict[str, Any]]
    summary: str
    main_topics: List[str]
    metadata: Dict[str, Any]
    processed_at: datetime

class RAGResponse(BaseModel):
    """Respuesta estructurada del sistema RAG."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    reasoning: str
    follow_up: List[str]

class AgenticNutritionRAG:
    """Modelo RAG especializado en nutrición."""
    
    def __init__(self, 
                 openai_api_key: str,
                 model_name: str = "gpt-3.5-turbo",
                 temperature: float = 0.7,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        """Inicializa el modelo RAG.
        
        Args:
            openai_api_key: API key de OpenAI
            model_name: Nombre del modelo a usar
            temperature: Temperatura para generación
            chunk_size: Tamaño de chunks para splitting
            chunk_overlap: Superposición entre chunks
        """
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model_name,
            temperature=temperature
        )
        
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.qa_prompt = PromptTemplate(
            template="""Eres un experto en nutrición deportiva. Usa el siguiente contexto para responder la pregunta.
            Si no estás seguro de la respuesta, di que no lo sabes.
            
            Contexto: {context}
            
            Pregunta: {question}
            
            Respuesta detallada:""",
            input_variables=["context", "question"]
        )
        
    async def process_video(self, 
                          title: str,
                          channel: str, 
                          url: str,
                          transcript: str) -> VideoKnowledge:
        """Procesa un video y extrae conocimiento estructurado."""
        # Dividir transcripción en chunks
        chunks = self.text_splitter.split_text(transcript)
        
        # Extraer temas principales
        topics_prompt = f"""
        Analiza la siguiente transcripción y extrae los temas principales sobre nutrición:
        {transcript[:2000]}...
        
        Lista de temas (máximo 5):
        """
        topics_response = await self.llm.apredict(topics_prompt)
        main_topics = [t.strip() for t in topics_response.split("\n") if t.strip()]
        
        # Generar resumen
        summary_prompt = f"""
        Resume los puntos clave sobre nutrición de esta transcripción en 3-4 párrafos:
        {transcript[:3000]}...
        """
        summary = await self.llm.apredict(summary_prompt)
        
        # Procesar chunks
        segments = []
        for i, chunk in enumerate(chunks):
            # Extraer palabras clave
            keywords_prompt = f"""
            Extrae 5-7 palabras clave sobre nutrición de este texto:
            {chunk}
            """
            keywords = await self.llm.apredict(keywords_prompt)
            
            segments.append({
                "content": chunk,
                "start_time": i * 30, # Estimado
                "end_time": (i + 1) * 30,
                "keywords": keywords.split("\n"),
                "embedding": self.embeddings.embed_query(chunk)
            })
        
        return VideoKnowledge(
            title=title,
            channel=channel,
            url=url,
            segments=segments,
            summary=summary,
            main_topics=main_topics,
            metadata={
                "chunks": len(chunks),
                "total_tokens": sum(len(c.split()) for c in chunks)
            },
            processed_at=datetime.now()
        )
    
    def _score_chunk(self, chunk: str, query: str) -> float:
        """Calcula un score de relevancia para un chunk."""
        # Embedding similarity
        query_embedding = self.embeddings.embed_query(query)
        chunk_embedding = self.embeddings.embed_query(chunk)
        similarity = sum(q * c for q, c in zip(query_embedding, chunk_embedding))
        
        # Keyword matching
        query_keywords = set(query.lower().split())
        chunk_keywords = set(chunk.lower().split())
        keyword_overlap = len(query_keywords & chunk_keywords) / len(query_keywords)
        
        # Combine scores
        return 0.7 * similarity + 0.3 * keyword_overlap
    
    async def get_response(self, 
                          query: str,
                          context: Optional[List[Dict]] = None) -> RAGResponse:
        """Genera una respuesta usando el modelo."""
        # Si no hay contexto, usar toda la base de conocimiento
        if not context:
            context = []  # TODO: Implementar recuperación de base de datos
        
        # Scoring y ranking de chunks
        scored_chunks = []
        for doc in context:
            for segment in doc.get("segments", []):
                score = self._score_chunk(segment["content"], query)
                scored_chunks.append((score, segment))
        
        # Ordenar por score y tomar los mejores
        scored_chunks.sort(reverse=True)
        best_chunks = [c[1] for c in scored_chunks[:3]]
        
        # Construir contexto para respuesta
        context_text = "\n\n".join(c["content"] for c in best_chunks)
        
        # Generar respuesta
        qa_chain = ConversationalRetrievalChain(
            llm=self.llm,
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": self.qa_prompt}
        )
        
        response = await qa_chain.arun(
            question=query,
            chat_history=self.memory.chat_memory.messages
        )
        
        # Generar preguntas de seguimiento
        followup_prompt = f"""
        Basado en la pregunta "{query}" y la respuesta dada, 
        sugiere 2-3 preguntas de seguimiento relevantes:
        """
        followup = await self.llm.apredict(followup_prompt)
        followup_questions = [q.strip() for q in followup.split("\n") if q.strip()]
        
        # Calcular confianza
        confidence = sum(c[0] for c in scored_chunks[:3]) / 3
        
        return RAGResponse(
            answer=response,
            sources=[{
                "content": c["content"],
                "url": c.get("url", ""),
                "title": c.get("title", "")
            } for c in best_chunks],
            confidence=confidence,
            reasoning="Respuesta basada en coincidencia de palabras clave y similitud semántica",
            follow_up=followup_questions
        )
