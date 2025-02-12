# Knowledge Acquisition Agent 🤖

Sistema avanzado de adquisición y procesamiento de conocimiento usando múltiples modelos de lenguaje.

## 🗺️ Mapa del Proyecto

```
src/
├── llm/                    # Gestión de Modelos de Lenguaje
│   ├── model_provider.py   # Proveedores de LLM (OpenAI, Groq, etc.)
│   ├── llm_router.py       # Enrutamiento inteligente de modelos
│   └── utils.py           # Utilidades para LLM
├── config.py              # Configuración centralizada
└── ...                    # Otros módulos
```

## 🎯 Funcionalidades Principales

### 1. Sistema Multi-Modelo (LLM)
- **Proveedores Soportados**:
  - OpenAI (GPT-4, GPT-3.5)
  - Groq (Mixtral, LLaMA 2, Gemma)
  - DeepInfra
  - HuggingFace
  - Soporte futuro para modelos locales

- **Enrutamiento Inteligente**:
  - Selección automática del mejor modelo según la tarea
  - Optimización de costos y rendimiento
  - Sistema de fallback automático

- **Tipos de Tareas**:
  - `CODE`: Generación y análisis de código
  - `CHAT`: Conversación general
  - `CLASSIFICATION`: Clasificación de texto
  - `SUMMARY`: Generación de resúmenes
  - `EXTRACTION`: Extracción de información
  - `EMBEDDING`: Generación de embeddings

### 2. Configuración Flexible
- **Variables de Entorno** (.env):
  ```bash
  # LLM Configuration
  LLM_TYPE=openai|groq|deepinfra|huggingface|local
  LLM_NAME=gpt-4-turbo|mixtral-groq|...
  LLM_TEMPERATURE=0.7
  LLM_STREAMING=False

  # API Keys
  OPENAI_API_KEY=sk-...
  GROQ_API_KEY=gsk-...
  ```

- **Configuración de Rutas**:
  ```python
  # En config.py
  LLM_CONFIG = {
      "routes": {
          "CODE": "gpt4",          # Precisión
          "CHAT": "mixtral",       # Velocidad/Costo
          "CLASSIFICATION": "gpt35" # Suficiente
      }
  }
  ```

## 🚀 Guía de Uso

### 1. Configuración Básica
```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/Knowledge_Acquisition.git

# 2. Crear entorno conda
conda create -n knowledge-acquisition python=3.11
conda activate knowledge-acquisition

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys
```

### 2. Uso del Sistema Multi-Modelo

```python
from src.llm.utils import get_llm_for_task
from src.llm.llm_router import TaskType

# Obtener el mejor modelo para cada tarea
code_llm = get_llm_for_task(TaskType.CODE)      # Usa GPT-4
chat_llm = get_llm_for_task(TaskType.CHAT)      # Usa Mixtral
summary_llm = get_llm_for_task(TaskType.SUMMARY) # Usa el modelo configurado
```

### 3. Configuración Avanzada

```python
from src.llm.llm_router import LLMRouter, TaskType
from src.llm.model_provider import ModelType

# Crear router personalizado
router = LLMRouter()

# Agregar proveedores
router.add_provider(
    name="gpt4",
    model_type=ModelType.OPENAI,
    model_name="gpt-4-turbo"
)

router.add_provider(
    name="mixtral",
    model_type=ModelType.GROQ,
    model_name="mixtral-groq"
)

# Configurar rutas
router.set_route(TaskType.CODE, "gpt4")
router.set_route(TaskType.CHAT, "mixtral")
router.set_fallback("mixtral")
```

## 📋 TODO y Próximos Pasos

1. **Modelos Locales**
   - [ ] Integración con llama.cpp
   - [ ] Soporte para modelos cuantitativos
   - [ ] Gestión de recursos locales

2. **Optimización**
   - [ ] Sistema de caché para respuestas
   - [ ] Balanceo de carga entre modelos
   - [ ] Monitoreo de costos y uso

3. **Nuevas Funcionalidades**
   - [ ] Más proveedores de LLM
   - [ ] Nuevos tipos de tareas
   - [ ] Evaluación automática de respuestas

## 📚 Documentación Adicional

- [Guía de Desarrollo](docs/development.md)
- [Configuración de Modelos](docs/models.md)
- [API Reference](docs/api.md)

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.
