# Knowledge Acquisition Agent

Un agente inteligente especializado en adquisición y síntesis de conocimiento, utilizando GPT-4 y técnicas avanzadas de procesamiento de lenguaje natural.

## Características

- 🔍 **Búsqueda Inteligente**: Búsqueda y extracción de información relevante de múltiples fuentes
- ✅ **Validación de Información**: Verificación automática de la calidad y confiabilidad de la información
- 🧠 **Síntesis de Conocimiento**: Generación de resúmenes coherentes y estructurados
- 📊 **Evaluación Automática**: Evaluación de la calidad y completitud del conocimiento adquirido

## Arquitectura

El sistema está compuesto por varios agentes especializados:

1. **KnowledgeScout**: Busca y extrae información relevante
2. **FactValidator**: Valida la calidad y confiabilidad de la información
3. **KnowledgeSynthesizer**: Sintetiza y estructura el conocimiento
4. **MetaEvaluator**: Evalúa la calidad del conocimiento adquirido

## Instalación

### Requisitos

- Python 3.11+
- Conda (recomendado)

### Configuración del Entorno

1. Clonar el repositorio:
```bash
git clone https://github.com/costarotela/Knowledge_Acquisition.git
cd Knowledge_Acquisition
```

2. Crear y activar el entorno conda:
```bash
conda env create -f environment.yml
conda activate knowledge-acquisition
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

## Uso

### Ejemplo Básico

```python
from src.agent.orchestrator import KnowledgeOrchestrator, AcquisitionTask, TaskType, TaskPriority

# Inicializar orquestador
config = {
    "openai_api_key": "tu_api_key",
    "model_name": "gpt-4-turbo-preview"
}
orchestrator = KnowledgeOrchestrator(config)

# Crear tarea de investigación
task = AcquisitionTask(
    query="https://ejemplo.com/articulo",
    task_type=TaskType.RESEARCH,
    priority=TaskPriority.HIGH
)

# Ejecutar tarea
result = await orchestrator.execute(task)

# Procesar resultados
if result.success:
    print("Conocimiento extraído:")
    print(f"- Conceptos: {result.data.get('concepts')}")
    print(f"- Resumen: {result.data.get('summary')}")
```

### Ejemplos Avanzados

Ver la carpeta `examples/` para más ejemplos de uso.

## Estructura del Proyecto

```
Knowledge_Acquisition/
├── src/
│   ├── agent/
│   │   ├── specialized/
│   │   │   ├── knowledge_scout.py
│   │   │   ├── fact_validator.py
│   │   │   ├── knowledge_synthesizer.py
│   │   │   └── meta_evaluator.py
│   │   └── orchestrator.py
│   ├── auth/
│   └── scrapers/
├── examples/
├── tests/
└── docs/
```

## Desarrollo

### Entornos de Desarrollo

1. **knowledge-acquisition** (Principal):
   - Para desarrollo principal y producción
   - Contiene todas las dependencias
   - Incluye CUDA/PyTorch y procesamiento multimedia

2. **knowledge-acq-test** (Testing):
   - SOLO para pruebas y correcciones rápidas
   - Dependencias mínimas
   - Sin CUDA/PyTorch

### Convenciones de Código

- Seguir PEP 8
- Documentar todas las funciones y clases
- Usar type hints
- Mantener cobertura de tests > 80%

## Contribuir

1. Fork el repositorio
2. Crear una rama (`git checkout -b feature/nombre`)
3. Commit los cambios (`git commit -am 'Add: característica'`)
4. Push a la rama (`git push origin feature/nombre`)
5. Crear un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.
