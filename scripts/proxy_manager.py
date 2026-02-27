
import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import aiohttp
from aiohttp import ClientSession, TCPConnector

from scripts.logger import get_logger
from scripts.input_validator import get_validator

adv_logger = get_logger('logs')


@dataclass
class ProxyStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_used: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    is_healthy: bool = True
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_response_time(self) -> float:
        if self.successful_requests == 0:
            return float('inf')
        return self.total_response_time / self.successful_requests


@dataclass
class Proxy:
    url: str
    type: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    stats: ProxyStats = field(default_factory=ProxyStats)
    
    def __post_init__(self):
        if not self.host or not self.port:
            parsed = urlparse(self.url)
            self.host = parsed.hostname or self.host
            self.port = parsed.port or self.port
            self.username = parsed.username or self.username
            self.password = parsed.password or self.password
    
    def get_aiohttp_proxy(self) -> str:
        if self.type in ('http', 'https'):
            return self.url
        return self.url
    
    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, other):
        if isinstance(other, Proxy):
            return self.url == other.url
        return False


class ProxyManager:
    
    def __init__(
        self,
        proxies: List[str] = None,
        max_failures: int = 3,
        health_check_interval: float = 300.0,
        rotation_strategy: str = 'round_robin'  # round_robin, random, performance
    ):
        self.max_failures = max_failures
        self.health_check_interval = health_check_interval
        self.rotation_strategy = rotation_strategy
        
        self._proxies: List[Proxy] = []
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
        self.validator = get_validator()
        
        if proxies:
            self.add_proxies(proxies)
    
    def add_proxies(self, proxy_urls: List[str]):
        for url in proxy_urls:
            self.add_proxy(url)
    
    def add_proxy(self, proxy_url: str) -> bool:
        is_valid, result = self.validator.validate_proxy_url(proxy_url)
        if not is_valid:
            adv_logger.log_warning(f"Invalid proxy URL: {result}")
            return False
        
        try:
            parsed = urlparse(proxy_url)
            proxy_type = parsed.scheme.lower()
            
            if proxy_type not in ('http', 'https', 'socks4', 'socks5'):
                adv_logger.log_warning(f"Unsupported proxy type: {proxy_type}")
                return False
            
            proxy = Proxy(
                url=proxy_url,
                type=proxy_type,
                host=parsed.hostname,
                port=parsed.port or (80 if proxy_type == 'http' else 1080),
                username=parsed.username,
                password=parsed.password
            )
            
            if proxy not in self._proxies:
                self._proxies.append(proxy)
                adv_logger.log_info(f"Added proxy: {proxy.host}:{proxy.port} ({proxy.type})")
                return True
            
            return False
            
        except Exception as e:
            adv_logger.log_error(f"Error adding proxy {proxy_url}: {str(e)}")
            return False
    
    def load_from_file(self, filepath: str) -> int:
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if self.add_proxy(line):
                            count += 1
            
            adv_logger.log_info(f"Loaded {count} proxies from {filepath}")
            
        except FileNotFoundError:
            adv_logger.log_warning(f"Proxy file not found: {filepath}")
        except Exception as e:
            adv_logger.log_error(f"Error loading proxies from {filepath}: {str(e)}")
        
        return count
    
    async def get_proxy(self) -> Optional[Proxy]:
        async with self._lock:
            healthy_proxies = [p for p in self._proxies if p.stats.is_healthy]
            
            if not healthy_proxies:
                now = time.time()
                for proxy in self._proxies:
                    if now - proxy.stats.last_failure > self.health_check_interval:
                        proxy.stats.is_healthy = True
                        proxy.stats.consecutive_failures = 0
                        healthy_proxies.append(proxy)
            
            if not healthy_proxies:
                return None
            
            if self.rotation_strategy == 'random':
                proxy = random.choice(healthy_proxies)
            elif self.rotation_strategy == 'performance':
                proxy = min(
                    healthy_proxies,
                    key=lambda p: (
                        -p.stats.success_rate,
                        p.stats.avg_response_time
                    )
                )
            else:
                self._current_index = (self._current_index + 1) % len(healthy_proxies)
                proxy = healthy_proxies[self._current_index]
            
            proxy.stats.last_used = time.time()
            return proxy
    
    def record_success(self, proxy: Proxy, response_time: float):
        proxy.stats.total_requests += 1
        proxy.stats.successful_requests += 1
        proxy.stats.total_response_time += response_time
        proxy.stats.last_success = time.time()
        proxy.stats.consecutive_failures = 0
        proxy.stats.is_healthy = True
    
    def record_failure(self, proxy: Proxy):
        proxy.stats.total_requests += 1
        proxy.stats.failed_requests += 1
        proxy.stats.last_failure = time.time()
        proxy.stats.consecutive_failures += 1
        
        if proxy.stats.consecutive_failures >= self.max_failures:
            proxy.stats.is_healthy = False
            adv_logger.log_warning(
                f"Proxy {proxy.host}:{proxy.port} marked unhealthy after "
                f"{proxy.stats.consecutive_failures} consecutive failures"
            )
    
    async def check_proxy_health(self, proxy: Proxy, timeout: float = 10.0) -> bool:
        test_url = "https://www.google.com"
        
        try:
            start_time = time.time()
            
            connector = TCPConnector(ssl=False, limit=1)
            async with ClientSession(connector=connector) as session:
                async with session.get(
                    test_url,
                    proxy=proxy.get_aiohttp_proxy(),
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status < 400:
                        self.record_success(proxy, response_time)
                        return True
                    else:
                        self.record_failure(proxy)
                        return False
                        
        except Exception as e:
            self.record_failure(proxy)
            adv_logger.log_debug(f"Proxy health check failed for {proxy.host}:{proxy.port}: {str(e)}")
            return False
    
    async def check_all_proxies(self):
        tasks = [self.check_proxy_health(proxy) for proxy in self._proxies]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start_health_monitoring(self):
        async def monitor():
            while True:
                await asyncio.sleep(self.health_check_interval)
                await self.check_all_proxies()
        
        self._health_check_task = asyncio.create_task(monitor())
    
    def stop_health_monitoring(self):
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
    
    def get_stats(self) -> Dict:
        return {
            "total_proxies": len(self._proxies),
            "healthy_proxies": sum(1 for p in self._proxies if p.stats.is_healthy),
            "proxies": [
                {
                    "url": p.url,
                    "type": p.type,
                    "healthy": p.stats.is_healthy,
                    "success_rate": p.stats.success_rate,
                    "avg_response_time": p.stats.avg_response_time,
                    "total_requests": p.stats.total_requests,
                    "consecutive_failures": p.stats.consecutive_failures
                }
                for p in self._proxies
            ]
        }
    
    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0
    
    @property
    def healthy_count(self) -> int:
        return sum(1 for p in self._proxies if p.stats.is_healthy)


_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def reset_proxy_manager():
    global _proxy_manager
    if _proxy_manager:
        _proxy_manager.stop_health_monitoring()
    _proxy_manager = None
