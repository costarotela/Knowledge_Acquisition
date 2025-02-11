"""
Tests de integración para la interfaz de voz.
"""
import pytest
import pytest_asyncio
import numpy as np
from unittest.mock import MagicMock, patch
from src.agent.interfaces.voice_interface import AudioManager, WhisperProcessor
from src.agent.core.base import AgentContext

@pytest.fixture
def mock_whisper():
    """Mock para el modelo Whisper."""
    with patch('whisper.load_model') as mock_load:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            'text': 'Test transcription'
        }
        mock_load.return_value = mock_model
        yield mock_load

@pytest_asyncio.fixture
async def whisper_processor(mock_whisper):
    """Fixture para el procesador Whisper."""
    processor = WhisperProcessor()
    await processor.initialize()
    yield processor
    await processor.shutdown()

@pytest_asyncio.fixture
async def audio_manager(whisper_processor):
    """Fixture para el gestor de audio."""
    manager = AudioManager(whisper_processor)
    await manager.initialize()
    yield manager
    await manager.shutdown()

@pytest.mark.asyncio
async def test_audio_processing_pipeline(audio_manager):
    """Prueba el pipeline completo de procesamiento de audio."""
    context = AgentContext(
        session_id="test_session",
        user_id="test_user",
        language="es"
    )
    
    # Simular inicio de escucha
    await audio_manager.start_listening(context)
    assert audio_manager.is_listening()
    
    # Simular audio
    test_audio = np.zeros(16000)  # 1 segundo de silencio
    result = await audio_manager.process(test_audio, context)
    
    assert isinstance(result, dict)
    assert "text" in result
    assert result["text"] == "Test transcription"
    assert result["metadata"]["interface"] == audio_manager.name
    
    # Detener escucha
    await audio_manager.stop_listening()
    assert not audio_manager.is_listening()

@pytest.mark.asyncio
async def test_whisper_processor(whisper_processor):
    """Prueba el procesador Whisper."""
    assert whisper_processor.is_initialized()
    
    # Simular audio
    test_audio = np.zeros(16000)  # 1 segundo de silencio
    result = await whisper_processor.transcribe(test_audio)
    
    assert isinstance(result, str)
    assert result == "Test transcription"

@pytest.mark.asyncio
async def test_whisper_processor_error(whisper_processor, mock_whisper):
    """Prueba el manejo de errores del procesador Whisper."""
    mock_whisper.return_value.transcribe.side_effect = Exception("Transcription error")
    
    # Simular audio
    test_audio = np.zeros(16000)
    result = await whisper_processor.transcribe(test_audio)
    
    assert isinstance(result, str)
    assert result == ""

@pytest.mark.asyncio
async def test_audio_manager_error_handling(audio_manager):
    """Prueba el manejo de errores del gestor de audio."""
    context = AgentContext(
        session_id="test_session",
        user_id="test_user",
        language="es"
    )
    
    # Intentar procesar antes de iniciar la escucha
    test_audio = np.zeros(16000)
    result = await audio_manager.process(test_audio, context)
    assert "error" in result
    assert "No se está escuchando audio" in result["error"]
    
    # Intentar procesar audio inválido
    await audio_manager.start_listening(context)
    invalid_audio = np.zeros(100)  # Audio muy corto
    result = await audio_manager.process(invalid_audio, context)
    assert "error" in result
    assert "Audio inválido" in result["error"]
    
    # Intentar procesar audio nulo
    result = await audio_manager.process(None, context)
    assert "error" in result
    assert "Audio inválido" in result["error"]
    
    # Detener escucha
    await audio_manager.stop_listening()
    assert not audio_manager.is_listening()
