"""
Webhook system for external integrations.
"""
from typing import Dict, Any, List, Optional, Union, Callable
import asyncio
import aiohttp
from pydantic import BaseModel, HttpUrl
import json
import logging
from datetime import datetime
import hmac
import hashlib
import base64

logger = logging.getLogger(__name__)

class WebhookEndpoint(BaseModel):
    """Webhook endpoint configuration."""
    url: HttpUrl
    secret: Optional[str] = None
    headers: Dict[str, str] = {}
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    events: List[str] = ["*"]
    active: bool = True

class WebhookPayload(BaseModel):
    """Webhook payload model."""
    event: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class WebhookManager:
    """Manager for webhook operations."""
    
    def __init__(self):
        """Initialize webhook manager."""
        self.endpoints: Dict[str, WebhookEndpoint] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
    
    def register_endpoint(
        self,
        name: str,
        endpoint: WebhookEndpoint
    ):
        """Register new webhook endpoint."""
        self.endpoints[name] = endpoint
        logger.info(f"Registered webhook endpoint: {name}")
    
    def remove_endpoint(self, name: str):
        """Remove webhook endpoint."""
        if name in self.endpoints:
            del self.endpoints[name]
            logger.info(f"Removed webhook endpoint: {name}")
    
    def register_handler(
        self,
        event: str,
        handler: Callable
    ):
        """Register event handler."""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
        logger.info(f"Registered handler for event: {event}")
    
    def _sign_payload(
        self,
        payload: str,
        secret: str
    ) -> str:
        """Sign payload with secret."""
        return base64.b64encode(
            hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
    
    async def _send_webhook(
        self,
        endpoint: WebhookEndpoint,
        payload: WebhookPayload,
        attempt: int = 1
    ):
        """Send webhook request."""
        try:
            # Prepare payload
            json_payload = payload.json()
            
            # Add signature if secret is configured
            headers = endpoint.headers.copy()
            if endpoint.secret:
                signature = self._sign_payload(json_payload, endpoint.secret)
                headers["X-Webhook-Signature"] = signature
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    str(endpoint.url),
                    headers=headers,
                    json=json.loads(json_payload),
                    timeout=endpoint.timeout
                ) as response:
                    response.raise_for_status()
                    logger.info(
                        f"Webhook sent successfully: {endpoint.url} "
                        f"(event: {payload.event})"
                    )
                    
        except Exception as e:
            logger.error(
                f"Error sending webhook to {endpoint.url}: {str(e)}"
            )
            
            if attempt < endpoint.max_retries:
                await asyncio.sleep(endpoint.retry_delay)
                await self._send_webhook(endpoint, payload, attempt + 1)
            else:
                raise
    
    async def dispatch_event(
        self,
        event: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Dispatch event to registered endpoints."""
        payload = WebhookPayload(
            event=event,
            timestamp=datetime.now(),
            data=data,
            metadata=metadata
        )
        
        # Call event handlers
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    await handler(payload)
                except Exception as e:
                    logger.error(
                        f"Error in event handler for {event}: {str(e)}"
                    )
        
        # Send webhooks
        tasks = []
        for endpoint in self.endpoints.values():
            if not endpoint.active:
                continue
                
            if "*" in endpoint.events or event in endpoint.events:
                tasks.append(
                    self._send_webhook(endpoint, payload)
                )
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

class WebhookServer:
    """Server for receiving webhooks."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000
    ):
        """Initialize webhook server."""
        self.host = host
        self.port = port
        self.routes = {}
        self.middleware = []
    
    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: List[str] = ["POST"]
    ):
        """Add route handler."""
        self.routes[path] = {
            "handler": handler,
            "methods": methods
        }
    
    def add_middleware(self, middleware: Callable):
        """Add middleware function."""
        self.middleware.append(middleware)
    
    async def _handle_request(
        self,
        request: aiohttp.web.Request
    ) -> aiohttp.web.Response:
        """Handle incoming webhook request."""
        # Apply middleware
        for mw in self.middleware:
            try:
                await mw(request)
            except Exception as e:
                return aiohttp.web.Response(
                    status=400,
                    text=str(e)
                )
        
        # Get route handler
        route = self.routes.get(request.path)
        if not route:
            return aiohttp.web.Response(status=404)
        
        if request.method not in route["methods"]:
            return aiohttp.web.Response(status=405)
        
        try:
            # Parse payload
            payload = await request.json()
            
            # Call handler
            result = await route["handler"](payload)
            
            return aiohttp.web.json_response(
                result if result is not None else {"status": "ok"}
            )
            
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return aiohttp.web.Response(
                status=500,
                text=str(e)
            )
    
    async def start(self):
        """Start webhook server."""
        app = aiohttp.web.Application()
        app.router.add_route("*", "/{tail:.*}", self._handle_request)
        
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        
        site = aiohttp.web.TCPSite(
            runner,
            self.host,
            self.port
        )
        await site.start()
        
        logger.info(f"Webhook server running on {self.host}:{self.port}")
        
        return runner, site

class WebhookClient:
    """Client for making webhook requests."""
    
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None
    ):
        """Initialize webhook client."""
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
    
    async def send(
        self,
        endpoint: str,
        data: Dict[str, Any],
        method: str = "POST"
    ) -> Dict[str, Any]:
        """Send webhook request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=self.headers,
                json=data
            ) as response:
                response.raise_for_status()
                return await response.json()
