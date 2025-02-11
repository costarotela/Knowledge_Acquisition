"""
Tests para las clases base del agente.
"""
import pytest
import pytest_asyncio
from src.agent.core.base import AgentComponent, AgentInterface, AgentProcessor, AgentModel, AgentContext
from src.agent.core.config import AGENT_CONFIG

class MockComponent(AgentComponent):
    """Componente mock para testing."""
    
    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self.initialized = False
        self.shutdown_called = False
    
    async def initialize(self) -> None:
        if self.should_fail:
            raise Exception("Mock initialization error")
        self.initialized = True
        self._is_initialized = True
    
    async def shutdown(self) -> None:
        if self.should_fail:
            raise Exception("Mock shutdown error")
        self.shutdown_called = True
        self._is_initialized = False
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

class MockInterface(AgentInterface):
    """Interfaz mock para testing."""
    
    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self._initialized = False
        self._started = False
        self._stopped = False
    
    async def initialize(self) -> None:
        if self.should_fail:
            raise Exception("Mock initialization error")
        self._initialized = True
    
    async def shutdown(self) -> None:
        if self.should_fail:
            raise Exception("Mock shutdown error")
        self._initialized = False
    
    def is_initialized(self):
        return self._initialized
    
    async def start(self) -> None:
        if self.should_fail:
            raise Exception("Mock start error")
        self._started = True
        self._stopped = False
    
    async def stop(self) -> None:
        if self.should_fail:
            raise Exception("Mock stop error")
        self._started = False
        self._stopped = True
    
    @property
    def started(self):
        return self._started
    
    @property
    def stopped(self):
        return self._stopped
    
    async def send_response(self, response: str) -> None:
        """Mock para enviar respuesta."""
        pass
    
    async def __aenter__(self):
        await self.initialize()
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        await self.shutdown()

class MockProcessor(AgentProcessor):
    """Procesador mock para testing."""
    
    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self.processed_data = None
    
    async def initialize(self) -> None:
        if self.should_fail:
            raise Exception("Mock initialization error")
        self._is_initialized = True
    
    async def shutdown(self) -> None:
        if self.should_fail:
            raise Exception("Mock shutdown error")
        self._is_initialized = False
    
    async def process(self, input_data: str, context: AgentContext) -> dict:
        if self.should_fail:
            raise Exception("Mock process error")
        self.processed_data = input_data
        return {"result": f"Processed: {input_data}"}
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

class MockModel(AgentModel):
    """Modelo mock para testing."""
    
    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self.prediction = None
    
    async def initialize(self) -> None:
        if self.should_fail:
            raise Exception("Mock initialization error")
        self._is_initialized = True
    
    async def shutdown(self) -> None:
        if self.should_fail:
            raise Exception("Mock shutdown error")
        self._is_initialized = False
    
    async def predict(self, input_data: str, context: AgentContext) -> dict:
        if self.should_fail:
            raise Exception("Mock prediction error")
        self.prediction = input_data
        return {"prediction": f"Predicted: {input_data}"}
    
    async def train(self, training_data: dict) -> None:
        if self.should_fail:
            raise Exception("Mock training error")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

@pytest_asyncio.fixture
async def component():
    """Fixture para el componente mock."""
    async with MockComponent("test_component") as comp:
        yield comp

@pytest_asyncio.fixture
async def interface():
    """Fixture para la interfaz mock."""
    async with MockInterface("test_interface") as iface:
        yield iface

@pytest_asyncio.fixture
async def processor():
    """Fixture para el procesador mock."""
    async with MockProcessor("test_processor") as proc:
        yield proc

@pytest_asyncio.fixture
async def model():
    """Fixture para el modelo mock."""
    async with MockModel("test_model") as mod:
        yield mod

@pytest.mark.asyncio
async def test_agent_component(component):
    """Test AgentComponent functionality."""
    # Test successful initialization
    assert component.is_initialized()
    assert component.initialized
    
    await component.shutdown()
    assert not component.is_initialized()
    assert component.shutdown_called
    
    # Test failed initialization
    component = MockComponent("test_component", should_fail=True)
    with pytest.raises(Exception) as exc_info:
        await component.initialize()
    assert str(exc_info.value) == "Mock initialization error"
    
    # Test failed shutdown
    component = MockComponent("test_component", should_fail=True)
    with pytest.raises(Exception) as exc_info:
        await component.shutdown()
    assert str(exc_info.value) == "Mock shutdown error"

@pytest.mark.asyncio
async def test_agent_interface(interface):
    """Test AgentInterface functionality."""
    # Test successful operations
    assert interface.is_initialized()
    
    assert interface.started
    
    assert not interface.stopped
    
    await interface.shutdown()
    assert not interface.is_initialized()
    
    # Test failures
    interface = MockInterface("test_interface", should_fail=True)
    with pytest.raises(Exception):
        await interface.initialize()
    
    with pytest.raises(Exception):
        await interface.start()
    
    with pytest.raises(Exception):
        await interface.stop()
    
    with pytest.raises(Exception):
        await interface.shutdown()

@pytest.mark.asyncio
async def test_agent_processor(processor):
    """Test AgentProcessor functionality."""
    # Test successful processing
    assert processor.is_initialized()
    
    context = AgentContext(session_id="test_session")
    result = await processor.process("test_input", context)
    assert result["result"] == "Processed: test_input"
    assert processor.processed_data == "test_input"
    
    await processor.shutdown()
    assert not processor.is_initialized()
    
    # Test failures
    processor = MockProcessor("test_processor", should_fail=True)
    with pytest.raises(Exception):
        await processor.initialize()
    
    with pytest.raises(Exception):
        await processor.process("test_input", context)
    
    with pytest.raises(Exception):
        await processor.shutdown()

@pytest.mark.asyncio
async def test_agent_model(model):
    """Test AgentModel functionality."""
    # Test successful operations
    assert model.is_initialized()
    
    context = AgentContext(session_id="test_session")
    result = await model.predict("test_input", context)
    assert result["prediction"] == "Predicted: test_input"
    assert model.prediction == "test_input"
    
    await model.train({"data": "test_data"})
    await model.shutdown()
    assert not model.is_initialized()
    
    # Test failures
    model = MockModel("test_model", should_fail=True)
    with pytest.raises(Exception):
        await model.initialize()
    
    with pytest.raises(Exception):
        await model.predict("test_input", context)
    
    with pytest.raises(Exception):
        await model.train({"data": "test_data"})
    
    with pytest.raises(Exception):
        await model.shutdown()

@pytest.mark.asyncio
async def test_agent_context():
    """Test AgentContext functionality."""
    # Test default values
    context = AgentContext(session_id="test_session")
    assert context.session_id == "test_session"
    assert context.language == AGENT_CONFIG["language"]
    assert context.user_id is None
    assert context.metadata is None
    
    # Test custom values
    context = AgentContext(
        session_id="test_session",
        user_id="test_user",
        language="en",
        metadata={"key": "value"}
    )
    assert context.session_id == "test_session"
    assert context.user_id == "test_user"
    assert context.language == "en"
    assert context.metadata == {"key": "value"}
