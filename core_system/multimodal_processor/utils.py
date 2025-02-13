"""
Utility functions for multimodal processing and alignment.
"""

import torch
import numpy as np
from typing import List, Dict, Union, Optional, Tuple
from PIL import Image
import librosa
import io
import base64
from pathlib import Path


def normalize_embedding(embedding: torch.Tensor) -> torch.Tensor:
    """Normalize embedding to unit length."""
    return torch.nn.functional.normalize(embedding, p=2, dim=-1)


def pad_sequences(
    sequences: List[torch.Tensor],
    max_length: Optional[int] = None,
    padding_value: float = 0.0
) -> torch.Tensor:
    """Pad sequences to the same length."""
    if max_length is None:
        max_length = max(seq.size(0) for seq in sequences)
    
    padded_seqs = []
    for seq in sequences:
        if seq.size(0) < max_length:
            padding = torch.full(
                (max_length - seq.size(0), *seq.size()[1:]),
                padding_value
            )
            padded_seq = torch.cat([seq, padding], dim=0)
        else:
            padded_seq = seq[:max_length]
        padded_seqs.append(padded_seq)
    
    return torch.stack(padded_seqs)


def create_attention_mask(
    lengths: List[int],
    max_length: Optional[int] = None
) -> torch.Tensor:
    """Create attention mask for variable length sequences."""
    if max_length is None:
        max_length = max(lengths)
    
    batch_size = len(lengths)
    mask = torch.zeros((batch_size, max_length), dtype=torch.bool)
    
    for i, length in enumerate(lengths):
        mask[i, length:] = True
    
    return mask


def process_audio(
    audio_data: Union[str, bytes, np.ndarray],
    target_sr: int = 16000,
    max_duration: Optional[float] = None
) -> Tuple[np.ndarray, int]:
    """
    Process audio data from various formats.
    
    Args:
        audio_data: Audio data as file path, bytes, base64 string, or numpy array
        target_sr: Target sample rate
        max_duration: Maximum duration in seconds
    
    Returns:
        Tuple of (processed audio array, sample rate)
    """
    # Handle different input types
    if isinstance(audio_data, str):
        if audio_data.startswith('data:audio'):
            # Handle base64 audio
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
            with io.BytesIO(audio_bytes) as buf:
                audio, sr = librosa.load(buf, sr=target_sr)
        else:
            # Handle file path
            audio, sr = librosa.load(audio_data, sr=target_sr)
    elif isinstance(audio_data, bytes):
        with io.BytesIO(audio_data) as buf:
            audio, sr = librosa.load(buf, sr=target_sr)
    elif isinstance(audio_data, np.ndarray):
        audio = audio_data
        sr = target_sr
    else:
        raise ValueError(f"Unsupported audio data type: {type(audio_data)}")
    
    # Apply duration limit if specified
    if max_duration is not None:
        max_samples = int(max_duration * target_sr)
        audio = audio[:max_samples]
    
    return audio, sr


def process_image(
    image_data: Union[str, bytes, Image.Image],
    target_size: Tuple[int, int] = (224, 224)
) -> Image.Image:
    """
    Process image data from various formats.
    
    Args:
        image_data: Image data as file path, bytes, base64 string, or PIL Image
        target_size: Target image size (height, width)
    
    Returns:
        Processed PIL Image
    """
    if isinstance(image_data, str):
        if image_data.startswith('data:image'):
            # Handle base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1])
            image = Image.open(io.BytesIO(image_bytes))
        else:
            # Handle file path
            image = Image.open(image_data)
    elif isinstance(image_data, bytes):
        image = Image.open(io.BytesIO(image_data))
    elif isinstance(image_data, Image.Image):
        image = image_data
    else:
        raise ValueError(f"Unsupported image data type: {type(image_data)}")
    
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if needed
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    
    return image


def save_embeddings(
    embeddings: torch.Tensor,
    filepath: Union[str, Path],
    metadata: Optional[Dict] = None
) -> None:
    """
    Save embeddings and optional metadata to file.
    
    Args:
        embeddings: Tensor of embeddings
        filepath: Path to save file
        metadata: Optional dictionary of metadata
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to numpy if needed
    if isinstance(embeddings, torch.Tensor):
        embeddings = embeddings.cpu().numpy()
    
    # Save with metadata if provided
    if metadata:
        np.savez(filepath, embeddings=embeddings, **metadata)
    else:
        np.save(filepath, embeddings)


def load_embeddings(
    filepath: Union[str, Path]
) -> Tuple[np.ndarray, Optional[Dict]]:
    """
    Load embeddings and metadata from file.
    
    Args:
        filepath: Path to embedding file
    
    Returns:
        Tuple of (embeddings array, metadata dict if present)
    """
    filepath = Path(filepath)
    
    if filepath.suffix == '.npz':
        # Load with metadata
        data = np.load(filepath)
        embeddings = data['embeddings']
        metadata = {k: v for k, v in data.items() if k != 'embeddings'}
        return embeddings, metadata
    else:
        # Load embeddings only
        return np.load(filepath), None
