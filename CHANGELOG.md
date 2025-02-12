# Changelog

## [0.3.0] - 2025-02-12

### Added
- Sistema de procesadores unificado para múltiples fuentes de información:
  - VideoProcessor: Procesamiento de videos de YouTube
  - DocumentProcessor: Manejo de archivos PDF, Excel, Word y texto
  - WebProcessor: Extracción de Wikipedia, GitHub y páginas web
- Configuración centralizada para todos los procesadores
- Integración con el modelo RAG principal
- Soporte para múltiples fuentes de conocimiento

### Changed
- Refactorización del sistema de agentes para usar procesadores especializados
- Mejora en la estructura del proyecto para mayor claridad
- Actualización de la configuración global

### Deprecated
- Sistema antiguo de procesamiento de videos
- Módulos redundantes de extracción de información

## [0.2.0] - 2025-02-12

### Added
- Sistema de autenticación y autorización basado en JWT
- Roles de usuario (OWNER, RESEARCHER, VIEWER)
- Permisos específicos para diferentes operaciones
- Protección de endpoints sensibles
- Decorador `@requires_auth` para funciones protegidas
- Configuración de permisos por rol
- Modelos de autenticación (User, TokenPayload)

### Changed
- Actualización de agentes especializados para usar autenticación:
  - KnowledgeScout: Requiere permiso EXECUTE_SEARCH
  - FactValidator: Requiere permiso VALIDATE_INFO
  - MetaEvaluator: Requiere permiso EVALUATE
- Mejora en la generación de resultados de búsqueda
- Optimización del proceso de validación
- Refinamiento del sistema de evaluación

### Fixed
- Error en la validación de resultados del KnowledgeScout
- Problema con atributos faltantes en SynthesizedKnowledge
- Manejo mejorado de errores en la validación

## [0.1.0] - 2025-02-11

### Added
- Implementación inicial del sistema de adquisición de conocimiento
- Agentes especializados:
  - KnowledgeScout para búsqueda
  - FactValidator para validación
  - KnowledgeSynthesizer para síntesis
  - MetaEvaluator para evaluación
- Sistema de prompts para interacción con OpenAI
- Estructuras de datos base (SearchResult, ValidationResult, etc.)
- Configuración inicial del proyecto

### Changed
- Migración de langchain a OpenAI API directa
- Mejora en la estructura del proyecto
- Optimización de prompts
