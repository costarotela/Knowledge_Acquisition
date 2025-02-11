import asyncio
import time
from typing import Optional, Dict
from collections import defaultdict

class RateLimiter:
    """Rate limiter for controlling request frequency per domain."""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.rate = 1.0 / requests_per_second
        self.last_request_time: Dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()
    
    async def acquire(self, domain: Optional[str] = None) -> None:
        """Wait if necessary to maintain the rate limit."""
        async with self._lock:
            now = time.time()
            if domain in self.last_request_time:
                elapsed = now - self.last_request_time[domain]
                if elapsed < self.rate:
                    await asyncio.sleep(self.rate - elapsed)
            self.last_request_time[domain] = time.time()
    
    def reset(self, domain: Optional[str] = None) -> None:
        """Reset the rate limiter for a specific domain or all domains."""
        if domain:
            self.last_request_time.pop(domain, None)
        else:
            self.last_request_time.clear()
