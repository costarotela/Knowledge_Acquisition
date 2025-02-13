"""
Procesador de video mejorado con análisis visual y semántico.
"""

import cv2
import numpy as np
from typing import List, Dict, Optional
import torch
from transformers import AutoFeatureExtractor, AutoModelForObjectDetection
from PIL import Image
import logging
from pathlib import Path
import os

from ..models.video_models import VideoFrame, VideoFragment, VideoMetadata
from .concept_extractor import ConceptExtractor

logger = logging.getLogger(__name__)

class EnhancedVideoProcessor:
    """
    Procesador de video mejorado que combina análisis visual y semántico.
    """
    
    def __init__(self, model_name: str = "facebook/detr-resnet-50"):
        """
        Inicializa el procesador de video.
        
        Args:
            model_name: Nombre del modelo de detección de objetos
        """
        self.concept_extractor = ConceptExtractor()
        
        # Cargar modelo de detección de objetos
        logger.info("Cargando modelo de detección de objetos...")
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.model = AutoModelForObjectDetection.from_pretrained(model_name)
        
        # Configurar directorio para frames
        self.frames_dir = Path("frames")
        self.frames_dir.mkdir(exist_ok=True)
        
    def _extract_frames(self, video_path: str, interval: int = 30) -> List[VideoFrame]:
        """
        Extrae frames del video a intervalos regulares.
        
        Args:
            video_path: Ruta al archivo de video
            interval: Intervalo entre frames (en frames)
            
        Returns:
            Lista de frames extraídos
        """
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"No se pudo abrir el video: {video_path}")
            return frames
            
        try:
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % interval == 0:
                    # Guardar frame
                    frame_path = self.frames_dir / f"frame_{frame_count:06d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    
                    # Crear objeto VideoFrame
                    timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                    frames.append(VideoFrame(
                        timestamp=timestamp,
                        image_path=str(frame_path),
                        objects=[],
                        text="",
                        relevance_score=0.0
                    ))
                    
                frame_count += 1
                
        finally:
            cap.release()
            
        return frames
        
    def _detect_objects(self, frame_path: str) -> List[Dict]:
        """
        Detecta objetos en un frame usando el modelo DETR.
        
        Args:
            frame_path: Ruta al archivo de imagen
            
        Returns:
            Lista de objetos detectados con scores
        """
        try:
            image = Image.open(frame_path)
            inputs = self.feature_extractor(images=image, return_tensors="pt")
            outputs = self.model(**inputs)
            
            # Convertir outputs a formato más amigable
            target_sizes = torch.tensor([image.size[::-1]])
            results = self.feature_extractor.post_process_object_detection(
                outputs,
                target_sizes=target_sizes,
                threshold=0.7
            )[0]
            
            detections = []
            for score, label, box in zip(
                results["scores"],
                results["labels"],
                results["boxes"]
            ):
                detections.append({
                    "label": self.model.config.id2label[label.item()],
                    "confidence": score.item(),
                    "box": box.tolist()
                })
                
            return detections
            
        except Exception as e:
            logger.error(f"Error detectando objetos en {frame_path}: {e}")
            return []
            
    def _analyze_scene(self, frames: List[VideoFrame], window_size: int = 5) -> List[bool]:
        """
        Detecta cambios de escena usando diferencias entre frames.
        
        Args:
            frames: Lista de frames
            window_size: Tamaño de la ventana para detectar cambios
            
        Returns:
            Lista de booleanos indicando cambios de escena
        """
        scene_changes = [False] * len(frames)
        
        if len(frames) < window_size:
            return scene_changes
            
        try:
            for i in range(window_size, len(frames)):
                # Cargar frames
                current = cv2.imread(frames[i].image_path)
                previous = cv2.imread(frames[i-1].image_path)
                
                if current is None or previous is None:
                    continue
                    
                # Calcular diferencia
                diff = cv2.absdiff(current, previous)
                diff_score = np.mean(diff)
                
                # Si la diferencia es mayor al umbral, marcar como cambio de escena
                if diff_score > 30:  # Umbral ajustable
                    scene_changes[i] = True
                    
        except Exception as e:
            logger.error(f"Error analizando escenas: {e}")
            
        return scene_changes
        
    def _create_fragment(
        self,
        frames: List[VideoFrame],
        start_idx: int,
        end_idx: int,
        transcript: str
    ) -> VideoFragment:
        """
        Crea un fragmento de video con análisis visual y semántico.
        
        Args:
            frames: Lista de frames
            start_idx: Índice inicial
            end_idx: Índice final
            transcript: Transcripción del fragmento
            
        Returns:
            Fragmento de video
        """
        # Extraer frames del fragmento
        fragment_frames = frames[start_idx:end_idx+1]
        
        # Obtener timestamps
        start_time = fragment_frames[0].timestamp if fragment_frames else 0
        end_time = fragment_frames[-1].timestamp if fragment_frames else 0
        
        # Analizar contenido semántico
        domains = self.concept_extractor.categorize(transcript)
        knowledge_graph = self.concept_extractor.extract_knowledge_graph(transcript, domains)
        
        # Calcular score de importancia basado en conceptos y objetos detectados
        concept_score = max([d.confidence for d in domains]) if domains else 0.0
        object_score = max([f.relevance_score for f in fragment_frames]) if fragment_frames else 0.0
        importance_score = (concept_score + object_score) / 2
        
        return VideoFragment(
            text=transcript,
            start_time=start_time,
            end_time=end_time,
            knowledge_domains=domains,
            knowledge_graph=knowledge_graph,
            semantic_type="scene" if any(f.objects for f in fragment_frames) else "general",
            importance_score=importance_score
        )
        
    def process_video(
        self,
        video_path: str,
        transcript: str,
        chunk_size: int = 500
    ) -> List[VideoFragment]:
        """
        Procesa un video combinando análisis visual y semántico.
        
        Args:
            video_path: Ruta al archivo de video
            transcript: Transcripción del video
            chunk_size: Tamaño de los fragmentos de texto
            
        Returns:
            Lista de fragmentos de video
        """
        try:
            # 1. Extraer frames
            logger.info("Extrayendo frames...")
            frames = self._extract_frames(video_path)
            
            # 2. Detectar objetos en frames
            logger.info("Detectando objetos...")
            for frame in frames:
                objects = self._detect_objects(frame.image_path)
                frame.objects = [obj["label"] for obj in objects]
                frame.relevance_score = max([obj["confidence"] for obj in objects]) if objects else 0.0
            
            # 3. Analizar cambios de escena
            logger.info("Analizando escenas...")
            scene_changes = self._analyze_scene(frames)
            
            # 4. Dividir transcripción en chunks
            words = transcript.split()
            chunks = []
            current_chunk = []
            current_size = 0
            
            for word in words:
                word_size = len(word) + 1
                if current_size + word_size > chunk_size and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_size = word_size
                else:
                    current_chunk.append(word)
                    current_size += word_size
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            # 5. Crear fragmentos
            logger.info("Creando fragmentos...")
            fragments = []
            frames_per_chunk = len(frames) // len(chunks)
            
            for i, chunk in enumerate(chunks):
                start_idx = i * frames_per_chunk
                end_idx = start_idx + frames_per_chunk - 1
                
                if i == len(chunks) - 1:
                    end_idx = len(frames) - 1
                
                fragment = self._create_fragment(
                    frames=frames,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    transcript=chunk
                )
                fragments.append(fragment)
            
            return fragments
            
        except Exception as e:
            logger.error(f"Error procesando video: {e}")
            return []
