# Knowledge Acquisition System 🧠

Sistema integral de adquisición, procesamiento y síntesis de conocimiento usando agentes especializados y RAG avanzado.

## 🎯 Visión General

El Knowledge Acquisition System es una plataforma avanzada diseñada para extraer, procesar y sintetizar conocimiento de múltiples fuentes usando agentes especializados, procesamiento multimodal y Agentic RAG.

## 🏗️ Arquitectura

```
Knowledge_Acquisition/
├── core_system/                # Núcleo del Sistema
│   ├── agent_orchestrator/     # Coordinación de Agentes
│   ├── knowledge_base/         # Base de Conocimiento
│   │   ├── vector_db/         # Base Vectorial
│   │   ├── graph_db/          # Base de Grafos
│   │   └── raw_data/          # Datos Raw
│   ├── multimodal_processor/   # Procesador Multimodal
│   └── monitoring/            # Sistema de Monitoreo
│
├── agents/                     # Agentes Especializados
│   ├── youtube_agent/         # Agente YouTube
│   ├── github_agent/          # Agente GitHub
│   ├── web_research_agent/    # Agente Web
│   ├── academic_agent/        # Agente Académico
│   ├── social_media_agent/    # Agente de Redes Sociales
│   └── custom_rag_agent/      # Agente RAG
│
├── admin_interface/           # Interface Administrativa
│   ├── knowledge_explorer/    # Explorador de Conocimiento
│   ├── performance_monitor/   # Monitor de Rendimiento
│   └── validation_tools/      # Herramientas de Validación
│
├── api/                       # API Layer
├── models/                    # Modelos ML
├── docs/                      # Documentación
└── tests/                     # Tests
```

## 🚀 Características Principales

### 1. Sistema Core
- **Agent Orchestrator**: Coordinación centralizada de agentes
- **Knowledge Base**: Almacenamiento unificado con bases vectoriales y de grafos
- **Multimodal Processor**: Procesamiento de video, audio, texto e imágenes
- **Monitoring**: Sistema completo de monitoreo y logging

### 2. Agentes Especializados
- **YouTube Agent**: Análisis avanzado de contenido de YouTube
- **GitHub Agent**: Análisis de repositorios y código
- **Web Research Agent**: Investigación web con Brave Search
- **Academic Agent**: Búsqueda y análisis de papers académicos
- **Social Media Agent**: Análisis de tendencias y contenido en redes sociales
- **Custom RAG Agent**: RAG avanzado con generación de hipótesis

### 3. Interface Administrativa
- **Knowledge Explorer**: Visualización 3D del conocimiento
- **Performance Monitor**: Métricas en tiempo real
- **Validation Tools**: Herramientas de validación y control

## Arquitectura del Sistema

### Agentes Especializados

Los agentes especializados siguen el patrón Agentic RAG (Retrieval-Augmented Generation) que incluye:

1. **Procesamiento**: Extracción y análisis de datos de la fuente.
2. **Razonamiento**: Generación de hipótesis, evaluación y síntesis.
3. **Gestión de Conocimiento**: Almacenamiento, validación y consulta.

#### GitHub Agent
- `github_agent.py`: Agente principal que coordina los módulos
- `processing.py`: Análisis de repositorios y código
- `reasoning.py`: Evaluación de calidad y patrones
- `knowledge_manager.py`: Gestión de conocimiento del repositorio
- `schemas.py`: Definiciones de datos y modelos

#### YouTube Agent
- `youtube_agent.py`: Agente principal para análisis de videos
- `processing.py`: Extracción de transcripciones y metadatos
- `reasoning.py`: Análisis de contenido y credibilidad
- `knowledge_manager.py`: Gestión de conocimiento multimedia
- `schemas.py`: Modelos de datos para videos

## Investigadores Especializados

### Características

- **Investigador Web**
  - Búsqueda en múltiples motores
  - Extracción de contenido limpio
  - Validación de fuentes
  - Sistema de caché y rate limiting

- **Investigador Académico**
  - Integración con Google Scholar
  - Búsqueda en arXiv
  - API de Semantic Scholar
  - Validación de papers y citas

- **Investigador Interno**
  - Exploración de grafos de conocimiento
  - Análisis de patrones
  - Generación de insights
  - Validación multimodal

### Uso de los Investigadores

```python
from core_system.learning.researchers import (
    WebResearcher,
    AcademicResearcher,
    InternalResearcher
)
from core_system.learning.researchers.base import ResearchQuery

# Crear investigadores
web_researcher = WebResearcher(
    config={
        "language": "es",
        "min_article_length": 100
    }
)

academic_researcher = AcademicResearcher(
    config={
        "min_citations": 1,
        "max_paper_age_years": 5
    }
)

internal_researcher = InternalResearcher(
    store=hybrid_store,
    alignment=cross_modal_alignment,
    config={
        "min_similarity": 0.7,
        "max_hops": 3
    }
)

# Crear consulta de investigación
query = ResearchQuery(
    query="Tema a investigar",
    modalities=[ContentType.TEXT],
    context={},
    max_results=10
)

# Realizar investigación
async with web_researcher:
    web_results = await web_researcher.research(query)

async with academic_researcher:
    academic_results = await academic_researcher.research(query)

async with internal_researcher:
    internal_results = await internal_researcher.research(query)
```

### Configuración Avanzada

Los investigadores pueden configurarse mediante variables de entorno:

```bash
# Investigador Web
export WEB_SEARCH_API_KEY="tu_api_key"
export WEB_MAX_CONCURRENT=5
export WEB_CACHE_MAX_AGE=86400

# Investigador Académico
export SEMANTIC_SCHOLAR_API_KEY="tu_api_key"
export ACADEMIC_MIN_CITATIONS=1
export ACADEMIC_MAX_AGE_YEARS=5

# Investigador Interno
export INTERNAL_MIN_SIMILARITY=0.7
export INTERNAL_MAX_HOPS=3
export INTERNAL_BATCH_SIZE=100
```

## Agentes Especializados

El sistema cuenta con varios agentes especializados, cada uno diseñado para una tarea específica de adquisición de conocimiento:

### 1. RAG Agent
- Razonamiento avanzado sobre conocimiento
- Generación de nuevo conocimiento
- Evaluación de evidencia
- [Ver documentación detallada](#rag-agent-avanzado)

### 2. GitHub Agent
```python
from agents.specialized.github_agent import GitHubAgent

agent = GitHubAgent(
    config={
        "github_token": "your_token",
        "max_files": 100,
        "analyze_commits": True,
        "analyze_issues": True,
        "analyze_docs": True
    }
)

# Analizar un repositorio
knowledge = await agent.analyze_repository(
    "owner/repo",
    analysis_depth="deep"
)
```

### 3. Web Research Agent
```python
from agents.specialized.web_research_agent import WebResearchAgent

agent = WebResearchAgent(
    config={
        "max_depth": 3,
        "validate_sources": True,
        "use_archive": True
    }
)

# Investigar un tema
results = await agent.research_topic(
    "quantum computing advances 2024",
    min_confidence=0.8
)
```

### 4. YouTube Agent
```python
from agents.specialized.youtube_agent import YouTubeAgent

agent = YouTubeAgent(
    config={
        "api_key": "your_key",
        "transcription_model": "whisper-large",
        "content_filter": "strict"
    }
)

# Analizar un video
analysis = await agent.analyze_video(
    "video_id",
    extract_chapters=True,
    generate_summary=True
)
```

### 5. Academic Agent
```python
from agents.specialized.academic_agent import AcademicAgent

agent = AcademicAgent(
    config={
        "databases": ["arxiv", "pubmed", "google_scholar"],
        "citation_validation": True
    }
)

# Buscar papers académicos
papers = await agent.search_papers(
    query="CRISPR applications",
    min_citations=50,
    max_age_years=2
)
```

### 6. Social Media Agent
```python
from agents.specialized.social_media_agent import SocialMediaAgent

agent = SocialMediaAgent(
    config={
        "platforms": ["twitter", "linkedin", "reddit"],
        "sentiment_analysis": True
    }
)

# Analizar tendencias
trends = await agent.analyze_trends(
    topic="AI ethics",
    timeframe="7d",
    min_engagement=1000
)
```

### Integración de Agentes

Los agentes pueden trabajar de forma independiente o coordinada:

```python
from core_system.agent_orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

# Registrar agentes
orchestrator.register_agent("rag", rag_agent)
orchestrator.register_agent("github", github_agent)
orchestrator.register_agent("academic", academic_agent)

# Ejecutar tarea multi-agente
result = await orchestrator.execute_task(
    task="Investigar avances en quantum computing",
    agents=["academic", "github", "rag"],
    coordination_strategy="parallel"
)
```

Para más detalles sobre cada agente, consulta su documentación específica en la carpeta `docs/agents/`.

## Ejemplos de Uso

### GitHub Agent

```python
from agents.specialized.github_agent import GitHubAgent, ResearchContext

# Inicializar agente
agent = GitHubAgent(vector_store_path="./knowledge/github")

# Definir contexto de investigación
context = ResearchContext(
    query="Analizar patrones de diseño en microservicios",
    objective="Identificar mejores prácticas de arquitectura",
    domain="software_architecture",
    required_depth=4
)

# Analizar repositorio
analysis = await agent.analyze_repository(
    context=context,
    repo_url="https://github.com/example/microservices"
)

# Consultar conocimiento almacenado
results = await agent.query_knowledge(
    query="Patrones de comunicación entre servicios",
    filters={"type": "code_pattern"}
)
```

### YouTube Agent

```python
from agents.specialized.youtube_agent import YouTubeAgent, VideoContext

# Inicializar agente
agent = YouTubeAgent(vector_store_path="./knowledge/youtube")

# Definir contexto de análisis
context = VideoContext(
    query="Explicación de arquitecturas de microservicios",
    objective="Extraer conceptos clave y mejores prácticas",
    domain="software_engineering",
    required_depth=3
)

# Analizar video
analysis = await agent.analyze_video(
    context=context,
    video_id="example_video_id"
)

# Consultar conocimiento almacenado
results = await agent.query_knowledge(
    query="Ventajas de microservicios",
    filters={"type": "key_finding"}
)
```

## Estado Actual del Proyecto (Febrero 2025)

### Componentes Completados

1. **Agentes Especializados con Agentic RAG**
   - GitHub Agent: Análisis de repositorios y código
   - YouTube Agent: Análisis de contenido multimedia
   - Academic Agent: En proceso de refactorización
   - Social Media Agent: En proceso de refactorización

2. **Arquitectura RAG**
   - Módulos de Procesamiento: Extracción y análisis de datos
   - Módulos de Razonamiento: Evaluación y síntesis
   - Gestión de Conocimiento: Almacenamiento y validación
   - Esquemas de Datos: Modelos Pydantic

3. **Infraestructura**
   - Entornos Conda configurados
   - Dependencias actualizadas
   - Sistema de almacenamiento vectorial

### Próximos Pasos

1. **Refactorización Pendiente**
   - Completar Academic Agent
   - Completar Social Media Agent
   - Actualizar tests unitarios

2. **Mejoras Planificadas**
   - Optimización de rendimiento
   - Expansión de capacidades de razonamiento
   - Mejora en la detección de contradicciones

3. **Documentación**
   - Expandir ejemplos de uso
   - Añadir diagramas de arquitectura
   - Documentar patrones de integración

## Sistema de Validación y Síntesis

### Validación de Conocimiento

El sistema de validación asegura la calidad y confiabilidad del conocimiento adquirido mediante:

- **Reglas de Validación**
  - Calidad de contenido
  - Confiabilidad de fuentes
  - Consistencia interna
  - Validación multimodal
  - Calidad lingüística

```python
from core_system.learning.synthesis.validator import KnowledgeValidator

validator = KnowledgeValidator(
    store=hybrid_store,
    alignment=cross_modal_alignment,
    config={
        "min_overall_score": 0.7,
        "validation_timeout": 30
    }
)

# Validar hallazgos
validation_results = await validator.validate(findings)
```

### Síntesis de Conocimiento

El sintetizador combina los hallazgos validados en entidades coherentes:

- **Características**
  - Agrupación por tipo de contenido
  - Detección de relaciones
  - Integración multimodal
  - Gestión de confianza

```python
from core_system.learning.synthesis.synthesizer import KnowledgeSynthesizer

synthesizer = KnowledgeSynthesizer(
    store=hybrid_store,
    alignment=cross_modal_alignment,
    config={
        "min_confidence": 0.7,
        "batch_size": 100
    }
)

# Sintetizar conocimiento
synthesis_result = await synthesizer.synthesize(validation_results)
```

### Configuración

El sistema se puede configurar mediante variables de entorno:

```bash
# Validación
export VALIDATION_MIN_SCORE=0.7
export VALIDATION_TIMEOUT=30
export VALIDATION_MAX_CONCURRENT=10

# Síntesis
export SYNTHESIS_MIN_CONFIDENCE=0.7
export SYNTHESIS_BATCH_SIZE=100
export SYNTHESIS_MAX_CONCURRENT=5
```

### Integración con Investigadores

El sistema de validación y síntesis trabaja en conjunto con los investigadores:

1. Los investigadores recolectan hallazgos
2. El validador aplica reglas de calidad
3. El sintetizador integra los hallazgos validados
4. El conocimiento resultante se almacena en la base

## 🛠️ Instalación

### Entorno Principal (Desarrollo/Producción)
```bash
# Crear entorno principal
conda create -n knowledge-acquisition python=3.10
conda activate knowledge-acquisition

# Instalar dependencias
pip install langchain openai chromadb pydantic
pip install aiohttp GitPython
pip install pytube youtube-transcript-api moviepy nltk langdetect
conda install -c conda-forge pytorch torchvision cudatoolkit
```

### Entorno de Testing
```bash
# Crear entorno de test
conda create -n knowledge-acq-test python=3.10
conda activate knowledge-acq-test

# Instalar dependencias mínimas
pip install langchain openai pydantic pytest
```

## 📋 Uso

### 1. Iniciar Sistema Core
```python
from core_system.agent_orchestrator import SystemOrchestrator

# Inicializar orquestador
orchestrator = SystemOrchestrator()

# Configurar agentes
orchestrator.register_agent('youtube', YouTubeAgent())
orchestrator.register_agent('github', GitHubAgent())
orchestrator.register_agent('web', WebResearchAgent())
orchestrator.register_agent('rag', CustomRAGAgent())

# Iniciar sistema
orchestrator.start()
```

### 2. Procesar Conocimiento
```python
# Procesar video de YouTube
knowledge = orchestrator.process_source(
    source_type='youtube',
    url='https://youtube.com/watch?v=...'
)

# Investigación web
research = orchestrator.process_source(
    source_type='web',
    query='advanced AI systems'
)

# Síntesis de conocimiento
synthesis = orchestrator.rag_agent.synthesize(
    topic='AI Systems',
    sources=[knowledge, research]
)
```

## 📚 Documentación

Documentación detallada disponible en `/docs/`:
- [Estructura del Sistema](docs/architecture/system_structure.md)
- [Guía de Agentes](docs/agents.md)
- [API Reference](docs/API.md)

## 🧪 Tests y Desarrollo

### Estructura de Tests
```
tests/
├── core/                      # Tests del núcleo del sistema
│   ├── test_orchestrator.py   # Tests de orquestación de agentes
│   └── test_knowledge_base.py # Tests de la base de conocimiento
├── agents/                    # Tests de agentes especializados
│   └── test_rag_agent.py     # Tests del agente RAG
├── researchers/              # Tests de investigadores
│   └── test_web_researcher.py # Tests del investigador web
└── integration/              # Tests de integración
    └── test_knowledge_flow.py # Tests de flujo de conocimiento
```

### Entornos de Desarrollo

El proyecto utiliza dos entornos conda:

1. **knowledge-acquisition** (Principal)
   - Entorno completo para desarrollo y producción
   - Incluye todas las dependencias
   - Contiene CUDA/PyTorch y procesamiento multimedia
   ```bash
   conda activate knowledge-acquisition
   ```

2. **knowledge-acq-test** (Testing)
   - Entorno ligero solo para pruebas
   - Dependencias mínimas sin CUDA/PyTorch
   ```bash
   conda activate knowledge-acq-test
   ```

### Ejecución de Tests

1. **Tests Individuales**
   ```bash
   # Test específico
   python -m pytest tests/core/test_orchestrator.py -v
   
   # Test con nombre específico
   python -m pytest tests/core/test_orchestrator.py::test_agent_registration -v
   ```

2. **Grupos de Tests**
   ```bash
   # Todos los tests del core
   python -m pytest tests/core/ -v
   
   # Todos los tests de agentes
   python -m pytest tests/agents/ -v
   ```

3. **Tests de Integración**
   ```bash
   # Tests de flujo completo
   python -m pytest tests/integration/ -v
   ```

4. **Todos los Tests**
   ```bash
   python -m pytest -v
   ```

### Convenciones de Testing

1. **Nombrado de Tests**
   - Usar nombres descriptivos que indiquen qué se está probando
   - Formato: `test_[funcionalidad]_[escenario]`
   - Ejemplo: `test_knowledge_retrieval_with_invalid_query`

2. **Fixtures**
   - Usar fixtures de pytest para configuración común
   - Nombrar fixtures claramente según su propósito
   - Ejemplo: `mock_knowledge_store`, `test_environment`

3. **Mocking**
   - Usar `unittest.mock` para componentes externos
   - Documentar comportamiento esperado del mock
   - Verificar llamadas a mocks cuando sea relevante

### Flujos de Trabajo Comunes

1. **Desarrollo de Nueva Funcionalidad**
   ```bash
   # 1. Activar entorno principal
   conda activate knowledge-acquisition
   
   # 2. Crear tests para la nueva funcionalidad
   # 3. Implementar la funcionalidad
   # 4. Ejecutar tests específicos
   python -m pytest tests/path/to/test.py -v
   
   # 5. Ejecutar suite completa
   python -m pytest -v
   ```

2. **Corrección de Bugs**
   ```bash
   # 1. Activar entorno de testing
   conda activate knowledge-acq-test
   
   # 2. Reproducir el bug con un test
   # 3. Corregir el bug
   # 4. Verificar la corrección
   python -m pytest tests/path/to/test.py -v
   ```

3. **Mantenimiento**
   ```bash
   # Verificar cobertura de tests
   python -m pytest --cov=core_system
   
   # Ejecutar tests con reporte detallado
   python -m pytest -v --html=report.html
   ```

### Documentación de Tests

Cada test debe incluir:
- Docstring explicando qué prueba
- Configuración necesaria (fixtures)
- Casos de prueba cubiertos
- Comportamiento esperado

Ejemplo:
```python
def test_knowledge_retrieval():
    """Test knowledge retrieval and reasoning
    
    Verifica:
    1. Recuperación correcta de conocimiento
    2. Puntuación de relevancia
    3. Filtrado por confianza
    4. Citación de fuentes
    """
```

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/NuevaFuncionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/NuevaFuncionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

## Motor de Razonamiento

### Características

- **Razonamiento Multimodal**
  - Procesamiento integrado de texto, imágenes y audio
  - Alineamiento cross-modal mediante CLIP y Whisper
  - Validación cruzada entre modalidades

- **Generación de Hipótesis**
  - Generación basada en LLM (Mixtral-8x7B)
  - Sistema de confianza y evidencia
  - Validación lógica y factual

- **Síntesis de Conocimiento**
  - Integración de múltiples hipótesis
  - Manejo de incertidumbre
  - Contexto temporal
  - Trazabilidad de evidencia

### Uso del Motor de Razonamiento

```python
from core_system.reasoning.engine import ReasoningEngine
from core_system.knowledge_base.models import KnowledgeEntity

# Inicializar el motor
engine = ReasoningEngine(
    store=hybrid_store,
    alignment=cross_modal_alignment
)

# Realizar razonamiento
result = await engine.reason(
    query="¿Cómo se relacionan los conceptos A y B?",
    context_entities=[entity1, entity2],
    max_hypotheses=5
)

# Acceder a los resultados
print(f"Conclusión: {result.statement}")
print(f"Confianza: {result.confidence}")
for hypothesis in result.source_hypotheses:
    print(f"Hipótesis: {hypothesis.statement}")
    print(f"Evidencia: {hypothesis.evidence}")
```

### Configuración Avanzada

El motor de razonamiento puede configurarse mediante variables de entorno:

```bash
# Configuración del LLM
export REASONING_LLM_MODEL="mistralai/Mixtral-8x7B-Instruct-v0.1"
export REASONING_MAX_CONTEXT=4096
export REASONING_TEMPERATURE=0.7

# Configuración de la validación
export REASONING_MIN_CONFIDENCE=0.7
export REASONING_MAX_HYPOTHESES=5
```

## Sistema de Aprendizaje Autónomo

### Características

- **Detección de Brechas de Conocimiento**
  - Análisis de patrones de consulta
  - Evaluación de cobertura de dominios
  - Validación de consistencia temporal
  - Detección de conocimiento obsoleto

- **Investigación Autónoma**
  - Planificación estratégica de investigación
  - Múltiples fuentes de conocimiento
  - Validación cruzada de hallazgos
  - Sistema de priorización adaptativo

- **Integración de Conocimiento**
  - Validación multimodal
  - Actualización de embeddings
  - Optimización de grafos de conocimiento
  - Métricas de consolidación

### Uso del Sistema de Aprendizaje

```python
from core_system.learning.engine import SelfLearningEngine

# Inicializar el motor
learning_engine = SelfLearningEngine(
    store=hybrid_store,
    reasoning_engine=reasoning_engine,
    alignment=cross_modal_alignment
)

# Iniciar bucle de aprendizaje
await learning_engine.start_learning_loop()

# El sistema automáticamente:
# 1. Detecta brechas de conocimiento
# 2. Investiga para llenar esas brechas
# 3. Integra nuevos hallazgos
# 4. Consolida y optimiza la base de conocimientos
```

### Configuración Avanzada

El sistema de aprendizaje puede configurarse mediante variables de entorno:

```bash
# Configuración de investigación
export LEARNING_MAX_CONCURRENT=5
export LEARNING_MIN_CONFIDENCE=0.7
export LEARNING_MAX_RESEARCH_TIME=3600
export LEARNING_REFRESH_INTERVAL=3600

# Configuración de consolidación
export LEARNING_BATCH_SIZE=64
export LEARNING_LEARNING_RATE=0.001
export LEARNING_EPOCHS=10
```

## Sistema de Base de Conocimientos

### Características Principales

- **Almacenamiento Híbrido**
  - ChromaDB para búsqueda vectorial eficiente
  - Neo4j para relaciones y consultas basadas en grafos
  - Sistema de caché integrado para consultas frecuentes

- **Búsqueda Avanzada**
  - Búsqueda semántica multimodal
  - Filtrado por tipo de contenido, etiquetas y fechas
  - Exploración de relaciones y caminos en el grafo
  - Sistema de ranking y puntuación de relevancia

- **Configuración Flexible**
  - Configuración vía variables de entorno o archivos
  - Ajustes para ChromaDB y Neo4j
  - Parámetros de búsqueda personalizables
  - Control de caché y concurrencia

### Instalación

1. Crear y activar el entorno conda principal:
```bash
conda create -n knowledge-acquisition python=3.10
conda activate knowledge-acquisition
```

2. Instalar dependencias:
```bash
pip install langchain openai chromadb pydantic
pip install aiohttp GitPython
pip install pytube youtube-transcript-api moviepy nltk langdetect
conda install -c conda-forge pytorch torchvision cudatoolkit
```

3. Configurar variables de entorno:
```bash
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
```

### Uso

#### Búsqueda Semántica
```python
from core_system.knowledge_base.search_engine import SearchQuery, AdvancedSearchEngine
from datetime import datetime, timedelta

# Crear consulta
query = SearchQuery(
    text="concepto de inteligencia artificial",
    content_types=["text", "image"],
    tags=["AI", "machine_learning"],
    min_confidence=0.7,
    date_range=(datetime.now() - timedelta(days=30), datetime.now())
)

# Realizar búsqueda
results = await search_engine.semantic_search(query, limit=10)

# Acceder a resultados
for entity in results.direct_matches:
    print(f"Entidad: {entity.id}, Relevancia: {results.relevance_scores[entity.id]}")
```

#### Exploración de Relaciones
```python
# Buscar entidades relacionadas
query = SearchQuery(
    related_to=entity_id,
    relation_depth=2,
    min_confidence=0.8
)

results = await search_engine.semantic_search(query)

# Ver caminos en el grafo
for path in results.graph_paths:
    print("Camino encontrado:", " -> ".join(str(node) for node in path))
```

### Configuración Avanzada

El sistema puede configurarse a través de variables de entorno o el archivo `config.py`:

```python
# Configuración de ChromaDB
CHROMADB_COLLECTION_NAME="knowledge_base"
CHROMADB_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
CHROMADB_PERSIST_DIRECTORY="./data/chromadb"

# Configuración de Neo4j
NEO4J_URI="neo4j://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your-password"

# Configuración de búsqueda
SEARCH_DEFAULT_LIMIT=10
SEARCH_MAX_LIMIT=100
SEARCH_MIN_CONFIDENCE=0.5
SEARCH_CACHE_TTL=300

```

## RAG Agent Avanzado

El RAG Agent ha sido refactorizado para proporcionar capacidades avanzadas de razonamiento y gestión de conocimiento:

#### Componentes Principales

1. **RAG Agent (`rag_agent.py`)**
   - Coordinación de componentes
   - Procesamiento de tareas
   - Generación de respuestas
   - Gestión de estado del agente

2. **Motor de Razonamiento (`reasoning.py`)**
   - Análisis de consultas
   - Generación de cadenas de razonamiento
   - Evaluación de evidencia
   - Generación de conclusiones
   - Manejo de confianza

3. **Gestor de Conocimiento (`knowledge_manager.py`)**
   - Recuperación contextual
   - Almacenamiento unificado
   - Validación de fragmentos
   - Compresión de documentos

4. **Schemas (`schemas.py`)**
   - Definición de tipos de consultas
   - Estructuras de razonamiento
   - Formatos de conocimiento
   - Estado del agente

#### Características

- **Razonamiento Multi-paso**
  ```python
  response = await agent.generate_response(
      "¿Cómo afecta el ejercicio a la función mitocondrial?"
  )
  print(f"Pasos de razonamiento:")
  for step in response.reasoning_chain.steps:
      print(f"{step.step_number}. {step.description}")
      print(f"Conclusión: {step.intermediate_conclusion}")
  ```

- **Generación de Conocimiento**
  ```python
  if response.generated_knowledge:
      print("Nuevo conocimiento generado:")
      print(f"Tipo: {response.generated_knowledge['type']}")
      print(f"Contenido: {response.generated_knowledge['content']}")
      print(f"Confianza: {response.generated_knowledge['confidence']}")
  ```

- **Gestión de Evidencia**
  ```python
  print("Evidencia de soporte:")
  for citation in response.reasoning_chain.citations:
      print(f"- {citation.content_snippet}")
      print(f"  Relevancia: {citation.relevance_score}")
  ```

#### Configuración

```python
from agents.specialized.rag_agent import RAGAgent

agent = RAGAgent(
    config={
        "model_name": "gpt-4",
        "vector_store_path": "./knowledge_store",
        "max_documents": 5,
        "confidence_threshold": 0.8,
        "use_contextual_compression": True
    }
)
```

#### Integración con el Sistema

El RAG Agent se integra con:
- Sistema de orquestación de agentes
- Base de conocimiento unificada
- Sistema de monitoreo
- Otros agentes especializados

Para más detalles, consulta la [documentación completa del RAG Agent](docs/agents/rag_agent.md).
