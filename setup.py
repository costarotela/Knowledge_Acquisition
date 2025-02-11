"""
Configuración del paquete Knowledge_Acquisition.
"""

from setuptools import setup, find_namespace_packages

# Requerimientos base
REQUIRED = [
    "pydantic>=2.0.0",
    "numpy>=1.24.0",
    "transformers>=4.30.0",
    "torch>=2.0.0",
    "opencv-python>=4.8.0",
    "Pillow>=10.0.0",
    "aiohttp>=3.8.0",
    "beautifulsoup4>=4.9.3",
    "pytube>=12.1.0",
    "python-dotenv>=0.19.0",
    "langchain>=0.1.0",  # Para text splitting y embeddings
    "tiktoken>=0.5.1",   # Para tokenización
    "numpy>=1.21.0",     # Para operaciones con vectores
]

# Requerimientos extra por funcionalidad
EXTRAS = {
    # Para procesamiento de video
    "video": [
        "torchvision>=0.15.0",
        "torchaudio>=2.0.0",
    ],
    
    # Para YouTube
    "youtube": [
        "youtube-transcript-api>=0.6.0",
    ],
    
    # Para procesamiento de texto y NLP
    "nlp": [
        "spacy>=3.0.0",
        "nltk>=3.8.0",
        "sentence-transformers>=2.2.0",
    ],
    
    # Para RAG y LLM
    "rag": [
        "langchain-community>=0.1.0",
        "openai>=1.0.0",
        "faiss-cpu>=1.7.0",
    ],
    
    # Para web scraping
    "scraping": [
        "aiofiles>=0.8.0",
    ],
    
    # Para desarrollo y testing
    "dev": [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.18.0",
        "black>=22.0.0",
        "flake8>=6.0.0",
        "pytest-cov>=3.0.0",
        "isort>=5.10.0",
        "mypy>=0.950",
    ],
    
    # Para embeddings
    "embeddings": [
        "openai>=1.0.0",  # Para embeddings de OpenAI
        "supabase>=2.0.0",  # Para almacenamiento vectorial
    ]
}

# Todos los extras combinados
EXTRAS["all"] = list(set(sum(EXTRAS.values(), [])))

setup(
    name="knowledge_acquisition",
    version="0.1.0",
    description="Sistema de adquisición de conocimiento desde videos",
    author="Pablo",
    packages=find_namespace_packages(include=["src.*"]),
    package_dir={"": "."},
    python_requires=">=3.9",
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    entry_points={
        "console_scripts": [
            "process_video=src.cli:process_video",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
