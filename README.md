# Sistema de Adquisición de Conocimiento Nutricional

Sistema avanzado de procesamiento y consulta de conocimiento nutricional que utiliza técnicas de RAG (Retrieval-Augmented Generation) para proporcionar respuestas precisas sobre nutrición deportiva.

## Características Principales

- **Sistema RAG Avanzado**: Implementación sofisticada de Retrieval-Augmented Generation
- **Procesamiento de Videos**: Extracción y análisis de conocimiento de videos de YouTube
- **Búsqueda Inteligente**: Sistema de búsqueda en dos fases con puntuación multifactorial
- **Interfaz Web Moderna**: Implementada con Streamlit para una experiencia fluida
- **Base Vectorial**: Almacenamiento y búsqueda vectorial eficiente con Supabase
- **Multilingüe**: Soporte nativo para español e inglés

## Tecnologías

- **Frontend**: Streamlit
- **Backend**: Python, FastAPI
- **Base de Datos**: Supabase (PostgreSQL + Extensiones Vectoriales)
- **ML/AI**: LangChain, OpenAI GPT-3.5
- **Procesamiento**: YouTube API, Sentence Transformers

## Requisitos

- Python 3.8+
- Supabase Account
- OpenAI API Key
- YouTube API Key

## Instalación

1. Clonar el repositorio:
```bash
git clone <repositorio>
cd Knowledge_Acquisition
```

2. Crear y activar entorno Conda:
```bash
conda create -n knowledge_acquisition python=3.8
conda activate knowledge_acquisition
```

3. Instalar dependencias:
```bash
conda install --file requirements.txt
# Para paquetes que no estén en conda:
pip install -r requirements-pip.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus claves API
```

## Configuración

1. Variables de Entorno Requeridas:
```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
YOUTUBE_API_KEY=AIza...
```

2. Configuración de Supabase:
- Crear proyecto en Supabase
- Habilitar extensiones vectoriales
- Ejecutar migraciones SQL (ver /docs/migrations/)

## Uso

1. Iniciar la aplicación:
```bash
streamlit run app.py
```

2. Acceder a la interfaz web:
- Abrir navegador en `http://localhost:8501`
- Ingresar con credenciales (si está configurado)

## Funcionalidades

### Procesamiento de Videos
1. Ingresar URL de YouTube
2. El sistema procesará automáticamente:
   - Extracción de transcripción
   - Análisis de contenido
   - Generación de embeddings
   - Almacenamiento estructurado

### Consultas
1. Realizar pregunta en lenguaje natural
2. El sistema:
   - Analiza la consulta
   - Busca contexto relevante
   - Genera respuesta precisa
   - Proporciona fuentes

## Estructura del Proyecto

```
Knowledge_Acquisition/
├── src/
│   ├── agent/           # Núcleo del sistema
│   ├── auth/            # Autenticación
│   └── youtube/         # Procesamiento de videos
├── app.py              # Aplicación principal
├── requirements.txt    # Dependencias
└── docs/              # Documentación
    ├── DESIGN.md      # Diseño detallado
    ├── API.md         # Documentación API
    └── migrations/    # Scripts SQL
```

## Documentación

- [Diseño del Sistema](docs/DESIGN.md)
- [API Reference](docs/API.md)
- [Guía de Contribución](docs/CONTRIBUTING.md)

## Desarrollo

### Tests
```bash
pytest tests/
```

### Linting
```bash
flake8 src/
black src/
```

### Migraciones
```bash
python scripts/migrate.py
```

## Contribuir

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver [LICENSE](LICENSE) para más detalles.
