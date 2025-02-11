# Guía de Contribución

## Introducción

¡Gracias por tu interés en contribuir al Sistema de Adquisición de Conocimiento Nutricional! Este documento proporciona las pautas y mejores prácticas para contribuir al proyecto.

## Código de Conducta

Este proyecto se adhiere al [Contributor Covenant](https://www.contributor-covenant.org/). Al participar, se espera que mantengas este código.

## Cómo Contribuir

### 1. Configuración del Entorno

1. Fork el repositorio
2. Clonar tu fork:
```bash
git clone https://github.com/TU_USERNAME/Knowledge_Acquisition.git
```

3. Configurar el repositorio upstream:
```bash
git remote add upstream https://github.com/ORIGINAL_OWNER/Knowledge_Acquisition.git
```

4. Crear entorno Conda:
```bash
conda create -n knowledge_acquisition python=3.8
conda activate knowledge_acquisition

# Instalar dependencias
conda install --file requirements.txt
conda install --file requirements-dev.txt

# Para paquetes que no estén en conda
pip install -r requirements-pip.txt
pip install -r requirements-dev-pip.txt
```

### 2. Desarrollo

#### Estructura de Ramas

- `main`: Rama principal, producción
- `develop`: Rama de desarrollo
- `feature/*`: Nuevas características
- `bugfix/*`: Correcciones de bugs
- `docs/*`: Actualizaciones de documentación

#### Flujo de Trabajo

1. Crear rama desde `develop`:
```bash
git checkout develop
git pull upstream develop
git checkout -b feature/nueva-caracteristica
```

2. Desarrollar con buenas prácticas:
- Seguir guía de estilo PEP 8
- Añadir tests unitarios
- Documentar código nuevo
- Mantener commits atómicos

3. Ejecutar tests:
```bash
pytest tests/
```

4. Verificar estilo:
```bash
flake8 src/
black src/ --check
```

### 3. Pull Requests

1. Actualizar tu rama:
```bash
git fetch upstream
git rebase upstream/develop
```

2. Crear Pull Request:
- Título descriptivo
- Descripción detallada
- Referencias a issues
- Screenshots si aplica

3. Esperar review
4. Atender feedback
5. Merge (por mantenedores)

## Estándares de Código

### Python

- Python 3.8+
- PEP 8
- Tipos estáticos
- Docstrings Google style

```python
def funcion_ejemplo(param1: str, param2: int) -> Dict[str, Any]:
    """Descripción breve.
    
    Args:
        param1: Descripción del parámetro
        param2: Descripción del parámetro
        
    Returns:
        Dict con resultados
        
    Raises:
        ValueError: Descripción del error
    """
```

### Tests

- pytest
- Coverage > 80%
- Fixtures reutilizables
- Mocking apropiado

```python
def test_funcion_ejemplo(mock_dependencia):
    # Arrange
    entrada = "test"
    
    # Act
    resultado = funcion_ejemplo(entrada)
    
    # Assert
    assert resultado["campo"] == "valor"
```

### Documentación

- Markdown
- Diagramas con Mermaid
- Ejemplos de código
- Referencias API

## Reportar Issues

### Bugs

```markdown
### Descripción
Descripción clara y concisa

### Pasos para Reproducir
1. Paso 1
2. Paso 2
3. ...

### Comportamiento Esperado
Qué debería suceder

### Comportamiento Actual
Qué está sucediendo

### Contexto Adicional
- OS: Linux
- Python: 3.8.5
- Dependencias relevantes
```

### Features

```markdown
### Descripción
Qué necesidad resuelve

### Casos de Uso
- Caso 1
- Caso 2

### Implementación Sugerida
Ideas iniciales

### Alternativas Consideradas
Otras opciones y por qué no
```

## Versionado

Seguimos [Semantic Versioning](https://semver.org/):

- MAJOR: Cambios incompatibles
- MINOR: Funcionalidad nueva compatible
- PATCH: Correcciones compatibles

## Changelog

Mantener CHANGELOG.md actualizado:

```markdown
## [1.1.0] - 2024-02-11

### Añadido
- Nueva característica X
- Soporte para Y

### Cambiado
- Mejora en Z
- Actualización de W

### Corregido
- Bug en A
- Error en B
```

## Licencia

Al contribuir, aceptas que tu código se distribuya bajo la misma licencia del proyecto (MIT).
