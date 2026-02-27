
import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from scripts.constants import (
    DEFAULT_RATE_LIMIT, DEFAULT_BURST_SIZE,
    RATE_LIMIT_MIN, RATE_LIMIT_MAX,
    HTTP_TOO_MANY_REQUESTS
)


@dataclass
class RateLimitStats:
    total_requests: int = 0
    throttled_requests: int = 0
    rate_limit_hits: int = 0
    current_rate: float = 0.0
    last_429_time: float = 0.0


class TokenBucket:
    
    def __init__(self, rate: float, capacity: int):
        self.rate = max(RATE_LIMIT_MIN, min(rate, RATE_LIMIT_MAX))
        self.capacity = max(1, capacity)
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_token(self, timeout: float = 30.0) -> bool:
        start_time = time.monotonic()
        
        while True:
            if await self.acquire():
                return True
            
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                return False
            
            wait_time = min(1.0 / self.rate, timeout - elapsed)
            await asyncio.sleep(wait_time)
    
    def update_rate(self, new_rate: float):
        self.rate = max(RATE_LIMIT_MIN, min(new_rate, RATE_LIMIT_MAX))


class AdaptiveRateLimiter:
    
    def __init__(
        self,
        initial_rate: float = DEFAULT_RATE_LIMIT,
        burst_size: int = DEFAULT_BURST_SIZE,
        min_rate: float = 1.0,
        max_rate: float = 100.0,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.1
    ):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        
        self.bucket = TokenBucket(initial_rate, burst_size)
        self.stats = RateLimitStats(current_rate=initial_rate)
        
        self.host_buckets: Dict[str, TokenBucket] = {}
        self.host_stats: Dict[str, RateLimitStats] = {}
        
        self._lock = asyncio.Lock()
        
        self._consecutive_successes = 0
        self._success_threshold = 50
    
    async def acquire(self, host: Optional[str] = None) -> bool:
        self.stats.total_requests += 1
        
        if not await self.bucket.acquire():
            self.stats.throttled_requests += 1
            return False
        
        if host:
            async with self._lock:
                if host not in self.host_buckets:
                    self.host_buckets[host] = TokenBucket(
                        self.current_rate / 2,
                        max(1, DEFAULT_BURST_SIZE // 2)
                    )
                    self.host_stats[host] = RateLimitStats()
            
            if not await self.host_buckets[host].acquire():
                self.stats.throttled_requests += 1
                return False
            
            self.host_stats[host].total_requests += 1
        
        return True
    
    async def wait(self, host: Optional[str] = None, timeout: float = 30.0) -> bool:
        return await self.bucket.wait_for_token(timeout)
    
    def on_response(self, status_code: int, host: Optional[str] = None):
        if status_code == HTTP_TOO_MANY_REQUESTS:
            self._handle_rate_limit_hit(host)
        elif 200 <= status_code < 400:
            self._handle_success(host)
    
    def _handle_rate_limit_hit(self, host: Optional[str] = None):
        self.stats.rate_limit_hits += 1
        self.stats.last_429_time = time.time()
        self._consecutive_successes = 0
        
        new_rate = max(
            self.min_rate,
            self.current_rate * self.backoff_factor
        )
        self.current_rate = new_rate
        self.bucket.update_rate(new_rate)
        self.stats.current_rate = new_rate
        
        if host and host in self.host_buckets:
            self.host_stats[host].rate_limit_hits += 1
            self.host_stats[host].last_429_time = time.time()
            host_rate = max(self.min_rate, new_rate / 2)
            self.host_buckets[host].update_rate(host_rate)
            self.host_stats[host].current_rate = host_rate
    
    def _handle_success(self, host: Optional[str] = None):
        self._consecutive_successes += 1
        
        if self._consecutive_successes >= self._success_threshold:
            self._consecutive_successes = 0
            
            new_rate = min(
                self.max_rate,
                self.current_rate * self.recovery_factor
            )
            self.current_rate = new_rate
            self.bucket.update_rate(new_rate)
            self.stats.current_rate = new_rate
    
    def get_stats(self) -> Dict:
        return {
            "global": {
                "total_requests": self.stats.total_requests,
                "throttled_requests": self.stats.throttled_requests,
                "rate_limit_hits": self.stats.rate_limit_hits,
                "current_rate": self.stats.current_rate,
                "last_429_time": self.stats.last_429_time
            },
            "per_host": {
                host: {
                    "total_requests": stats.total_requests,
                    "rate_limit_hits": stats.rate_limit_hits,
                    "current_rate": stats.current_rate
                }
                for host, stats in self.host_stats.items()
            }
        }
    
    def reset(self):
        self.current_rate = DEFAULT_RATE_LIMIT
        self.bucket = TokenBucket(self.current_rate, DEFAULT_BURST_SIZE)
        self.stats = RateLimitStats(current_rate=self.current_rate)
        self.host_buckets.clear()
        self.host_stats.clear()
        self._consecutive_successes = 0


_rate_limiter: Optional[AdaptiveRateLimiter] = None


def get_rate_limiter(
    rate: float = DEFAULT_RATE_LIMIT,
    burst: int = DEFAULT_BURST_SIZE
) -> AdaptiveRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AdaptiveRateLimiter(rate, burst)
    return _rate_limiter


def reset_rate_limiter():
    global _rate_limiter
    if _rate_limiter:
        _rate_limiter.reset()
