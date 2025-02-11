"""
Tests para el procesador de videos de YouTube.
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, patch, call

from googleapiclient.errors import HttpError
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests
)

from src.agent.models.youtube_processor import YouTubeProcessor
from src.agent.core.context import AgentContext

# Constantes para pruebas
TEST_API_KEY = "test_api_key"
TEST_VIDEO_ID = "test_video_id"
TEST_VIDEO_TITLE = "Test Video Title"
TEST_CHANNEL = "Test Channel"
TEST_TRANSCRIPT = "Este es un texto de transcripción de prueba."

@pytest.fixture
def mock_transcript_api():
    """Mock para la API de transcripción."""
    with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_api:
        yield mock_api

@pytest.fixture
def mock_youtube_api():
    """Mock para la API de YouTube."""
    with patch('googleapiclient.discovery.build') as mock_build:
        yield mock_build

@pytest_asyncio.fixture
async def processor(mock_youtube_api, mock_transcript_api):
    """Fixture para el procesador de YouTube."""
    # Configurar mock para retornar transcripción exitosa por defecto
    mock_transcript_list = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [{"text": TEST_TRANSCRIPT}]
    mock_transcript_list.find_transcript.return_value = mock_transcript
    mock_transcript_api.list_transcripts.return_value = mock_transcript_list
    
    # Configurar mock para retornar información de video exitosa por defecto
    mock_youtube = mock_youtube_api.return_value
    mock_videos = MagicMock()
    mock_list = MagicMock()
    mock_response = {
        'items': [{
            'snippet': {'title': TEST_VIDEO_TITLE, 'channelTitle': TEST_CHANNEL},
            'statistics': {'viewCount': '1000', 'likeCount': '100'}
        }]
    }
    mock_list.execute.return_value = mock_response
    mock_videos.list.return_value = mock_list
    mock_youtube.videos.return_value = mock_videos
    
    # Crear procesador con los mocks
    processor = YouTubeProcessor(TEST_API_KEY, youtube_client=mock_youtube, transcript_api=mock_transcript_api)
    await processor.initialize()
    yield processor
    await processor.shutdown()

@pytest.mark.asyncio
async def test_initialization(mock_youtube_api):
    """Test inicialización del procesador."""
    processor = YouTubeProcessor(TEST_API_KEY)
    assert not processor.is_initialized()
    
    await processor.initialize()
    assert processor.is_initialized()
    assert processor.youtube is not None
    
    await processor.shutdown()
    assert not processor.is_initialized()
    assert processor.youtube is None

@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://youtube.com/watch?v=dQw4w9WgXcQ"
])
def test_extract_video_id_valid(processor, url):
    """Test extracción de ID de video desde URLs válidas."""
    video_id = processor.extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"

@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch",
    "https://youtu.be/",
    "https://example.com/video",
    "not_a_url"
])
def test_extract_video_id_invalid(processor, url):
    """Test manejo de URLs inválidas."""
    with pytest.raises(ValueError):
        processor.extract_video_id(url)

@pytest.mark.asyncio
async def test_get_transcript(processor, mock_transcript_api):
    """Test obtención de transcripción."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Configurar mock para retornar transcripción exitosa
    mock_transcript_list = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [{"text": TEST_TRANSCRIPT}]
    mock_transcript_list.find_transcript.return_value = mock_transcript
    mock_transcript_api.list_transcripts.return_value = mock_transcript_list
    
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == TEST_TRANSCRIPT
    assert result["error"] is None

@pytest.mark.asyncio
async def test_get_transcript_disabled(processor, mock_transcript_api):
    """Test manejo de transcripciones deshabilitadas."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Configurar mock para lanzar TranscriptsDisabled
    mock_transcript_api.list_transcripts.side_effect = TranscriptsDisabled("test_video_id")
    
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == ""
    assert result["error"] == "Transcripts are disabled for this video"

@pytest.mark.asyncio
async def test_get_transcript_not_found(processor, mock_transcript_api):
    """Test manejo de transcripción no encontrada."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Configurar mock para lanzar NoTranscriptFound
    mock_transcript_api.list_transcripts.side_effect = NoTranscriptFound(
        "test_video_id",
        ["en"],
        {"en": None}
    )
    
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == ""
    assert result["error"] == "No transcript found for this video"

@pytest.mark.asyncio
async def test_video_unavailable(processor, mock_transcript_api):
    """Test manejo de video no disponible."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Configurar mock para lanzar VideoUnavailable
    mock_transcript_api.list_transcripts.side_effect = VideoUnavailable("test_video_id")
    
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == ""
    assert result["error"] == "Video is unavailable"

@pytest.mark.asyncio
async def test_too_many_requests(processor, mock_transcript_api):
    """Test manejo de demasiadas peticiones."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Configurar mock para lanzar TooManyRequests
    mock_transcript_api.list_transcripts.side_effect = TooManyRequests("test_video_id")
    
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == ""
    assert result["error"] == "Too many requests"

@pytest.mark.asyncio
async def test_http_error(processor, mock_youtube_api):
    """Test manejo de errores HTTP."""
    # Simular error HTTP
    mock_youtube = mock_youtube_api.return_value
    mock_videos = mock_youtube.videos.return_value
    mock_list = mock_videos.list.return_value
    mock_list.execute.side_effect = HttpError(resp=MagicMock(status=404), content=b"Not Found")
    
    result = await processor._get_video_info("test_video_id")
    assert result["title"] == ""
    assert result["channel"] == ""
    assert result["views"] == "0"
    assert result["likes"] == "0"
    assert "error" in result

@pytest.mark.asyncio
async def test_get_video_info(processor, mock_youtube_api):
    """Test obtención de información del video."""
    info = await processor._get_video_info("test_video_id")
    assert info["title"] == TEST_VIDEO_TITLE
    assert info["channel"] == TEST_CHANNEL
    assert info["views"] == "1000"
    assert info["likes"] == "100"
    assert info["error"] is None

@pytest.mark.asyncio
async def test_process_video(processor):
    """Test procesamiento completo de un video."""
    context = AgentContext(session_id="test_session", language="en")
    result = await processor.process("https://www.youtube.com/watch?v=test_video_id", context)
    
    assert result["title"] == TEST_VIDEO_TITLE
    assert result["channel"] == TEST_CHANNEL
    assert result["transcript"] == TEST_TRANSCRIPT
    assert result["views"] == "1000"
    assert result["likes"] == "100"
    assert result["error"] is None

@pytest.mark.asyncio
async def test_process_video_error(processor, mock_transcript_api):
    """Test manejo de errores en el procesamiento."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Simular error en la obtención de transcripción
    mock_transcript_api.list_transcripts.side_effect = TranscriptsDisabled(TEST_VIDEO_ID)
    
    result = await processor.process("https://www.youtube.com/watch?v=test_video_id", context)
    
    assert result["title"] == TEST_VIDEO_TITLE
    assert result["channel"] == TEST_CHANNEL
    assert result["transcript"] == ""
    assert result["error"] == "Transcripts are disabled for this video"

@pytest.mark.asyncio
async def test_concurrent_processing(processor):
    """Test procesamiento concurrente de videos."""
    context = AgentContext(session_id="test_session", language="en")
    
    # Procesar múltiples videos concurrentemente
    urls = [
        "https://www.youtube.com/watch?v=test_video_id1",
        "https://www.youtube.com/watch?v=test_video_id2",
        "https://www.youtube.com/watch?v=test_video_id3"
    ]
    
    tasks = [processor.process(url, context) for url in urls]
    results = await asyncio.gather(*tasks)
    
    # Verificar que todos los resultados son válidos
    for result in results:
        assert result["title"] == TEST_VIDEO_TITLE
        assert result["channel"] == TEST_CHANNEL
        assert result["transcript"] == TEST_TRANSCRIPT
        assert result["views"] == "1000"
        assert result["likes"] == "100"
        assert result["error"] is None

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_url", [
    "https://www.youtube.com/watch",
    "https://youtu.be/",
    "https://example.com/video",
    "not_a_url"
])
async def test_invalid_urls(processor, invalid_url):
    """Test manejo de URLs inválidas en el procesamiento."""
    context = AgentContext(session_id="test_session", language="en")
    
    with pytest.raises(ValueError):
        await processor.process(invalid_url, context)

@pytest.mark.asyncio
async def test_shutdown(mock_youtube_api):
    """Test que el shutdown limpia correctamente los recursos."""
    processor = YouTubeProcessor(TEST_API_KEY)
    await processor.initialize()
    assert processor.is_initialized()
    
    await processor.shutdown()
    assert not processor.is_initialized()
    assert processor.youtube is None

@pytest.mark.asyncio
async def test_is_initialized_states(mock_youtube_api):
    """Test del método is_initialized en diferentes estados."""
    processor = YouTubeProcessor(TEST_API_KEY)
    assert not processor.is_initialized()
    
    await processor.initialize()
    assert processor.is_initialized()
    
    await processor.shutdown()
    assert not processor.is_initialized()

@pytest.mark.asyncio
async def test_get_transcript_different_languages(processor, mock_transcript_api):
    """Test de obtención de transcripción en diferentes idiomas."""
    # Configurar mock para simular transcripción en español
    mock_transcript_list = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [{"text": "Texto en español"}]
    mock_transcript_list.find_transcript.return_value = mock_transcript
    mock_transcript_api.list_transcripts.return_value = mock_transcript_list
    
    # Crear contexto en español
    context = AgentContext(session_id="test_session")
    context.language = "es"
    
    # Obtener transcripción
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == "Texto en español"
    assert result["error"] is None
    
    # Verificar que se buscó la transcripción en español
    mock_transcript_list.find_transcript.assert_called_with(["es"])
    
    # Simular que no hay transcripción en español pero sí en inglés
    mock_transcript_list.find_transcript.side_effect = [
        NoTranscriptFound("test_video_id", ["es"], []),  # Falla al buscar en español
        mock_transcript       # Éxito al buscar en inglés
    ]
    mock_transcript.fetch.return_value = [{"text": "English text"}]
    
    result = await processor._get_transcript("test_video_id", context)
    assert result["transcript"] == "English text"
    assert result["error"] is None
    
    # Verificar que se intentó primero en español y luego en inglés
    assert mock_transcript_list.find_transcript.call_args_list[-2:] == [
        call(["es"]),
        call(["en"])
    ]
