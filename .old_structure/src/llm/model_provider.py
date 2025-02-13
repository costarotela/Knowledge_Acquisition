"""
Proveedor de modelos de lenguaje que soporta múltiples backends.
"""
from typing import Dict, Any, Optional, List
import os
from enum import Enum
from abc import ABC, abstractmethod

from langchain.chat_models import ChatOpenAI, ChatGroq
from langchain.llms import DeepInfra, HuggingFaceHub
from langchain.schema import BaseLanguageModel
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

class ModelType(Enum):
    """Tipos de modelos soportados."""
    OPENAI = "openai"
    DEEPINFRA = "deepinfra"
    HUGGINGFACE = "huggingface"
    GROQ = "groq"
    LOCAL = "local"  # Para futura implementación con llama.cpp

class ModelProvider:
    """Proveedor de modelos de lenguaje."""
    
    # Mapeo de nombres amigables a identificadores de modelo
    MODEL_MAPPINGS = {
        # OpenAI
        "gpt-4": "gpt-4",
        "gpt-4-turbo": "gpt-4-turbo-preview",
        "gpt-3.5": "gpt-3.5-turbo",
        
        # DeepInfra
        "mixtral": "deepinfra/mixtral-8x7b-instruct",
        "llama2-70b": "deepinfra/llama-2-70b-chat",
        "mistral": "deepinfra/mistral-7b-instruct",
        
        # Hugging Face
        "zephyr": "HuggingFaceH4/zephyr-7b-beta",
        "mistral-hf": "mistralai/Mistral-7B-Instruct-v0.1",
        "llama2-hf": "meta-llama/Llama-2-70b-chat-hf",
        
        # Groq
        "mixtral-groq": "mixtral-8x7b-32768",
        "llama2-70b-groq": "llama2-70b-4096",
        "gemma-7b": "gemma-7b-it"
    }

    def __init__(
        self,
        model_type: ModelType,
        model_name: str,
        temperature: float = 0.7,
        streaming: bool = False,
        **kwargs
    ):
        """
        Inicializa el proveedor de modelos.
        
        Args:
            model_type: Tipo de modelo a usar
            model_name: Nombre del modelo (usar nombres amigables definidos en MODEL_MAPPINGS)
            temperature: Temperatura para generación
            streaming: Si se debe usar streaming de tokens
            **kwargs: Argumentos adicionales específicos del modelo
        """
        self.model_type = model_type
        self.model_name = self._get_model_id(model_name)
        self.temperature = temperature
        self.streaming = streaming
        
        # Configurar callbacks para streaming si es necesario
        callbacks = None
        if streaming:
            callbacks = CallbackManager([StreamingStdOutCallbackHandler()])
        
        # Inicializar el modelo según el tipo
        if model_type == ModelType.OPENAI:
            api_key = kwargs.get('api_key') or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            
            self.model = ChatOpenAI(
                model_name=self.model_name,
                temperature=temperature,
                streaming=streaming,
                callbacks=callbacks,
                openai_api_key=api_key
            )
            
        elif model_type == ModelType.DEEPINFRA:
            api_key = kwargs.get('api_key') or os.getenv("DEEPINFRA_API_KEY")
            if not api_key:
                raise ValueError("DeepInfra API key is required")
            
            self.model = DeepInfra(
                model_id=self.model_name,
                deepinfra_api_token=api_key,
                temperature=temperature,
                callbacks=callbacks
            )
            
        elif model_type == ModelType.HUGGINGFACE:
            api_key = kwargs.get('api_key') or os.getenv("HUGGINGFACE_API_KEY")
            if not api_key:
                raise ValueError("HuggingFace API key is required")
            
            self.model = HuggingFaceHub(
                repo_id=self.model_name,
                huggingfacehub_api_token=api_key,
                temperature=temperature,
                callbacks=callbacks
            )
            
        elif model_type == ModelType.GROQ:
            api_key = kwargs.get('api_key') or os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("Groq API key is required")
            
            self.model = ChatGroq(
                model_name=self.model_name,
                groq_api_key=api_key,
                temperature=temperature,
                streaming=streaming,
                callbacks=callbacks
            )
            
        elif model_type == ModelType.LOCAL:
            raise NotImplementedError("Local models not yet supported")
            
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def _get_model_id(self, friendly_name: str) -> str:
        """Obtiene el ID real del modelo a partir del nombre amigable."""
        if friendly_name in self.MODEL_MAPPINGS:
            return self.MODEL_MAPPINGS[friendly_name]
        return friendly_name
    
    @property
    def llm(self) -> BaseLanguageModel:
        """Retorna el modelo de lenguaje subyacente."""
        return self.model

# Ejemplo de uso:
"""
# Usar GPT-4
provider = ModelProvider(
    model_type=ModelType.OPENAI,
    model_name="gpt-4",
    temperature=0.7
)

# Usar Mixtral en Groq (más rápido y económico)
provider = ModelProvider(
    model_type=ModelType.GROQ,
    model_name="mixtral-groq",
    temperature=0.7
)

# Usar Mistral-7B
provider = ModelProvider(
    model_type=ModelType.HUGGINGFACE,
    model_name="mistral-hf",
    temperature=0.7
)
"""
