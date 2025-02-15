"""Tests for browser manager."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
from pathlib import Path

from agents.specialized.travel_agent.core.browser_manager import BrowserManager, ExtractionResult, InteractionType
from langchain_openai import ChatOpenAI

@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()
    return browser

@pytest.fixture
def mock_agent():
    agent = AsyncMock()
    agent.extract_content = AsyncMock()
    agent.scroll_to_bottom = AsyncMock()
    agent.extract_table = AsyncMock()
    agent.extract_list = AsyncMock()
    agent.execute_action = AsyncMock()
    return agent

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.predict = AsyncMock()
    return llm

@pytest.fixture
def browser_manager(mock_browser, mock_agent, mock_llm, tmp_path):
    with patch('langchain_openai.ChatOpenAI', autospec=True) as mock_chat_openai:
        mock_chat_openai.return_value = mock_llm
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            manager = BrowserManager(
                llm_model="gpt-4",
                cache_dir=str(tmp_path / "cache"),
                cache_ttl=3600,
                headless=True
            )
            manager.browser = mock_browser
            manager.agent = mock_agent
            return manager

@pytest.mark.asyncio
async def test_extract_dynamic_content(browser_manager, mock_browser, mock_agent):
    """Test extracción de contenido dinámico."""
    # Configurar mocks
    context = mock_browser.new_context.return_value
    page = context.new_page.return_value
    mock_agent.extract_content.return_value = "Test Value"

    # Ejecutar test
    result = await browser_manager.extract_dynamic_content(
        url="https://test.com",
        selectors={"test": ".test-selector"},
        scroll=True,
        wait_for=".loading"
    )

    # Verificar resultado
    assert isinstance(result, ExtractionResult)
    assert result.success
    assert "test" in result.data
    assert result.data["test"] == "Test Value"
    assert not result.errors

    # Verificar llamadas
    assert page.goto.called
    assert page.wait_for_selector.called
    assert mock_agent.scroll_to_bottom.called
    assert mock_agent.extract_content.called

@pytest.mark.asyncio
async def test_extract_table_data(browser_manager, mock_browser, mock_agent):
    """Test extracción de datos de tabla."""
    # Configurar mocks
    context = mock_browser.new_context.return_value
    page = context.new_page.return_value
    mock_agent.extract_table.return_value = [
        {"col1": "val1", "col2": "val2"},
        {"col1": "val3", "col2": "val4"}
    ]

    # Ejecutar test
    result = await browser_manager.extract_table_data(
        url="https://test.com",
        table_selector="table.test",
        column_map={
            "col1": "td.col1",
            "col2": "td.col2"
        }
    )

    # Verificar resultado
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["col1"] == "val1"
    assert result[1]["col2"] == "val4"

    # Verificar llamadas
    assert page.goto.called
    assert mock_agent.extract_table.called

@pytest.mark.asyncio
async def test_extract_list_data(browser_manager, mock_browser, mock_agent):
    """Test extracción de datos de lista."""
    # Configurar mocks
    context = mock_browser.new_context.return_value
    page = context.new_page.return_value
    mock_agent.extract_list.return_value = [
        {"title": "Item 1", "price": "$100"},
        {"title": "Item 2", "price": "$200"}
    ]

    # Ejecutar test
    result = await browser_manager.extract_list_data(
        url="https://test.com",
        list_selector=".item-list",
        item_selectors={
            "title": ".item-title",
            "price": ".item-price"
        }
    )

    # Verificar resultado
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Item 1"
    assert result[1]["price"] == "$200"

    # Verificar llamadas
    assert page.goto.called
    assert mock_agent.extract_list.called

@pytest.mark.asyncio
async def test_interact_with_page(browser_manager, mock_browser, mock_agent):
    """Test interacciones con página."""
    # Configurar mocks
    context = mock_browser.new_context.return_value
    page = context.new_page.return_value
    mock_agent.execute_action.return_value = True

    # Ejecutar test
    result = await browser_manager.interact_with_page(
        url="https://test.com",
        interactions=[
            {
                "action": InteractionType.TYPE,
                "selector": "#search",
                "target": "test"
            },
            {
                "action": InteractionType.CLICK,
                "selector": "#submit"
            }
        ]
    )

    # Verificar resultado
    assert result is True
    assert mock_agent.execute_action.call_count == 0  # No se llama a execute_action para acciones básicas
    assert page.type.call_count == 1
    assert page.click.call_count == 1

@pytest.mark.asyncio
async def test_cache_functionality(browser_manager, mock_browser, mock_agent):
    """Test funcionalidad de caché."""
    # Preparar datos de prueba
    test_data = {"test": "value"}
    url = "https://test.com"

    # Guardar en caché
    browser_manager._save_to_cache(url, test_data)

    # Obtener de caché
    cached_data = browser_manager._get_from_cache(url)

    # Verificar
    assert cached_data == test_data

    # Verificar limpieza de caché
    browser_manager._cleanup_cache()

@pytest.mark.asyncio
async def test_error_handling(browser_manager, mock_browser, mock_agent):
    """Test manejo de errores."""
    # Configurar error en mock
    context = mock_browser.new_context.return_value
    page = context.new_page.return_value
    page.goto.side_effect = Exception("Test error")
    mock_agent.extract_content.return_value = None

    # Ejecutar test
    result = await browser_manager.extract_dynamic_content(
        url="https://test.com",
        selectors={"test": ".test"}
    )

    # Verificar manejo de error
    assert isinstance(result, ExtractionResult)
    assert not result.success
    assert "Test error" in result.errors[0]

@pytest.mark.asyncio
async def test_browser_cleanup(browser_manager, mock_browser):
    """Test limpieza de recursos."""
    await browser_manager.close()
    assert mock_browser.close.called
