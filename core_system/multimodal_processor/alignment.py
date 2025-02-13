"""
Cross-Modal Alignment System.
Provides unified embeddings across different modalities using CLIP and Whisper.
"""

import torch
import torch.nn as nn
from typing import List, Dict, Union, Optional
import numpy as np
from transformers import (
    CLIPProcessor, 
    CLIPModel, 
    WhisperProcessor, 
    WhisperModel,
    AutoTokenizer
)
from PIL import Image
import librosa


class ModalityEncoder(nn.Module):
    """Base class for modality-specific encoders."""
    
    def __init__(self, embedding_dim: int = 512):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.projection = nn.Linear(self.get_base_dim(), embedding_dim)
    
    def get_base_dim(self) -> int:
        """Return base dimension of the encoder."""
        raise NotImplementedError
    
    def encode(self, input_data: any) -> torch.Tensor:
        """Encode input data to embedding space."""
        raise NotImplementedError


class CLIPEncoder(ModalityEncoder):
    """CLIP-based encoder for text and images."""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        super().__init__(embedding_dim=512)  # CLIP's default dimension
    
    def get_base_dim(self) -> int:
        return self.model.config.hidden_size
    
    def encode_text(self, text: Union[str, List[str]]) -> torch.Tensor:
        """Encode text using CLIP."""
        inputs = self.processor(
            text=text,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        text_features = self.model.get_text_features(**inputs)
        return self.projection(text_features)
    
    def encode_image(self, image: Union[Image.Image, List[Image.Image]]) -> torch.Tensor:
        """Encode image using CLIP."""
        inputs = self.processor(
            images=image,
            return_tensors="pt"
        )
        image_features = self.model.get_image_features(**inputs)
        return self.projection(image_features)


class WhisperEncoder(ModalityEncoder):
    """Whisper-based encoder for audio."""
    
    def __init__(self, model_name: str = "openai/whisper-base"):
        self.model = WhisperModel.from_pretrained(model_name)
        self.processor = WhisperProcessor.from_pretrained(model_name)
        super().__init__(embedding_dim=512)  # Match CLIP's dimension
    
    def get_base_dim(self) -> int:
        return self.model.config.hidden_size
    
    def encode_audio(self, audio: np.ndarray, sample_rate: int = 16000) -> torch.Tensor:
        """Encode audio using Whisper."""
        inputs = self.processor(
            audio,
            sampling_rate=sample_rate,
            return_tensors="pt"
        )
        audio_features = self.model.get_encoder()(**inputs).last_hidden_state.mean(dim=1)
        return self.projection(audio_features)


class CrossModalAttention(nn.Module):
    """Cross-modal attention mechanism for alignment."""
    
    def __init__(self, embedding_dim: int = 512, num_heads: int = 8):
        super().__init__()
        self.attention = nn.MultiheadAttention(
            embed_dim=embedding_dim,
            num_heads=num_heads,
            batch_first=True
        )
        self.norm = nn.LayerNorm(embedding_dim)
    
    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Apply cross-modal attention."""
        attended, _ = self.attention(query, key, value, key_padding_mask=mask)
        return self.norm(attended + query)  # Add residual connection


class CrossModalAlignment:
    """Main class for cross-modal alignment."""
    
    def __init__(
        self,
        clip_model: str = "openai/clip-vit-base-patch32",
        whisper_model: str = "openai/whisper-base",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.device = device
        
        # Initialize encoders
        self.clip_encoder = CLIPEncoder(clip_model).to(device)
        self.whisper_encoder = WhisperEncoder(whisper_model).to(device)
        
        # Initialize cross-attention
        self.cross_attention = CrossModalAttention().to(device)
        
        # Set evaluation mode
        self.clip_encoder.eval()
        self.whisper_encoder.eval()
        self.cross_attention.eval()
    
    @torch.no_grad()
    def align(
        self,
        text: Optional[Union[str, List[str]]] = None,
        image: Optional[Union[Image.Image, List[Image.Image]]] = None,
        audio: Optional[np.ndarray] = None,
        sample_rate: int = 16000
    ) -> torch.Tensor:
        """
        Generate aligned embeddings for multiple modalities.
        At least one modality must be provided.
        """
        embeddings = []
        
        # Encode available modalities
        if text is not None:
            text_emb = self.clip_encoder.encode_text(text)
            embeddings.append(text_emb)
        
        if image is not None:
            image_emb = self.clip_encoder.encode_image(image)
            embeddings.append(image_emb)
        
        if audio is not None:
            audio_emb = self.whisper_encoder.encode_audio(audio, sample_rate)
            embeddings.append(audio_emb)
        
        if not embeddings:
            raise ValueError("At least one modality must be provided")
        
        # Stack embeddings
        embeddings = torch.stack(embeddings)
        
        # Apply cross-attention if we have multiple modalities
        if len(embeddings) > 1:
            # Use first embedding as query, rest as key/value
            query = embeddings[0].unsqueeze(0)
            key = value = embeddings.unsqueeze(0)
            
            # Apply cross-attention
            aligned = self.cross_attention(query, key, value)
            return aligned.squeeze(0)
        
        # If single modality, return as is
        return embeddings.squeeze(0)
    
    def compute_similarity(
        self,
        emb1: torch.Tensor,
        emb2: torch.Tensor
    ) -> float:
        """Compute cosine similarity between embeddings."""
        return torch.nn.functional.cosine_similarity(
            emb1.unsqueeze(0),
            emb2.unsqueeze(0)
        ).item()
    
    @staticmethod
    def load_audio(file_path: str, target_sr: int = 16000) -> np.ndarray:
        """Load and preprocess audio file."""
        audio, sr = librosa.load(file_path, sr=target_sr)
        return audio
    
    @staticmethod
    def load_image(file_path: str) -> Image.Image:
        """Load and preprocess image file."""
        return Image.open(file_path).convert('RGB')
