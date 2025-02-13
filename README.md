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
- **Custom RAG Agent**: RAG avanzado con generación de hipótesis

### 3. Interface Administrativa
- **Knowledge Explorer**: Visualización 3D del conocimiento
- **Performance Monitor**: Métricas en tiempo real
- **Validation Tools**: Herramientas de validación y control

## 🛠️ Instalación

### Entorno Principal (Desarrollo/Producción)
```bash
# Crear entorno principal
conda create -n knowledge-acquisition python=3.11
conda activate knowledge-acquisition

# Instalar dependencias
pip install -r requirements.txt
```

### Entorno de Testing
```bash
# Crear entorno de test
conda create -n knowledge-acq-test python=3.11
conda activate knowledge-acq-test

# Instalar dependencias mínimas
pip install -r requirements-test.txt
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

## 🧪 Testing

```bash
# Activar entorno de test
conda activate knowledge-acq-test

# Ejecutar suite completa
pytest tests/

# Tests específicos
pytest tests/test_core_system/
pytest tests/test_agents/
```

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/NuevaFuncionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/NuevaFuncionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.
