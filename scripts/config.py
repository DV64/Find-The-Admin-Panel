import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from scripts.logger import get_logger

adv_logger = get_logger('logs')

@dataclass
class Config:
    
    VERSION: str = "7.1"
    DEVELOPER: str = "DV64"
    GITHUB: str = "https://github.com/dv64"
    TOOL_NAME: str = "Find The Admin Panel"
    RELEASE_DATE: str = "2026-02-26"
    
    CACHE_TTL: int = 3600
    CACHE_SIZE: int = 1000
    CACHE_PERSISTENT: bool = True
    CACHE_DIR: str = ".cache"
    
    MAX_CONCURRENT_TASKS: int = 100
    CONNECTION_TIMEOUT: int = 5
    READ_TIMEOUT: int = 15
    BATCH_SIZE: int = 50
    VERIFY_SSL: bool = False
    
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    RETRY_JITTER: float = 0.5
    MAX_CONCURRENT_RETRIES: int = 3
    TIMEOUT_BACKOFF_FACTOR: float = 1.5
    AUTO_ADJUST_CONCURRENCY: bool = True
    MAX_TIMEOUT_THRESHOLD: int = 5
    
    USE_PROXIES: bool = False
    PROXY_LIST_FILE: str = "config/proxies.txt"
    PROXY_ROTATION_STRATEGY: str = "round_robin"
    PROXY_MAX_FAILURES: int = 3
    PROXY_HEALTH_CHECK_INTERVAL: int = 300
    
    USE_HEADLESS_BROWSER: bool = False
    HEADLESS_BROWSER_TYPE: str = "chromium"
    HEADLESS_TIMEOUT: int = 30
    CAPTURE_SCREENSHOTS: bool = False
    SCREENSHOTS_DIR: str = "screenshots"
    
    CAPTCHA_DETECTION: bool = True
    
    USE_RATE_LIMITING: bool = True
    RATE_LIMIT: int = 50
    RATE_LIMIT_BURST: int = 10
    ADAPTIVE_RATE_LIMITING: bool = True
    
    USE_PATH_FUZZING: bool = False
    FUZZING_DEPTH: int = 1
    FUZZING_EXTENSIONS: bool = True
    FUZZING_BACKUPS: bool = True
    FUZZING_CASE_VARIATIONS: bool = False
    
    USE_ADVANCED_DETECTION: bool = True
    DETECT_WEBSOCKET: bool = True
    DETECT_GRAPHQL: bool = True
    DETECT_REST_API: bool = True
    DETECT_SOAP: bool = True
    
    EXPORT_FORMATS: List[str] = field(default_factory=lambda: ["txt", "json", "csv", "html"])
    DETECTION_MODES: List[str] = field(default_factory=lambda: ["simple", "aggressive", "stealth"])
    DETECTION_MODE: str = "aggressive"
    SCAN_FREQUENCY: str = "once"
    MULTI_SITE_SCAN: bool = False
    
    LOGS_DIR: str = "logs"
    CUSTOM_PATHS_FILE: str = "paths/general_paths.json"
    DEFAULT_WORDLIST: str = "paths/general_paths.json"
    MAX_PATHS: int = 10000
    SAVE_RESULTS: bool = True
    RESULTS_DIR: str = "results"
    
    USE_HTTP3: bool = False
    AUTO_UPDATE_WORDLIST: bool = False
    WORDLIST_UPDATE_INTERVAL: int = 7
    WORDLIST_UPDATE_SOURCE: str = ""
    MULTILINGUAL_SUPPORT: bool = True
    BENCHMARK_MODE: bool = False
    
    USER_AGENTS: List[str] = field(default_factory=list)
    PROXIES: List[str] = field(default_factory=list)
    HEADERS_EXTRA: Dict[str, str] = field(default_factory=dict)
    
    SSL_VERIFICATION: Dict[str, str] = field(default_factory=lambda: {"MODE": "optional", "CUSTOM_CA_FILE": ""})
    
    NOTIFICATIONS: Dict = field(default_factory=dict)
    
    MODE_CONFIGS: Dict[str, Dict] = field(default_factory=dict)
    
    def __post_init__(self):
        self.load_config()
        self._validate_and_set_defaults()
        self._setup_detection_modes()
    
    def _validate_and_set_defaults(self):
        if not self.USER_AGENTS:
            default_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.60 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.60 Safari/537.36'
            ]
            self.USER_AGENTS = default_agents
            adv_logger.log_warning("USER_AGENTS not found in config.json or was empty. Using default user agents.")
            
        if not self.DEFAULT_WORDLIST:
            self.DEFAULT_WORDLIST = "paths/general_paths.json"
            adv_logger.log_info(f"Using default wordlist path: {self.DEFAULT_WORDLIST}")
        
        directories = [
            self.LOGS_DIR,
            self.RESULTS_DIR,
            os.path.dirname(self.DEFAULT_WORDLIST) if self.DEFAULT_WORDLIST else None,
            self.CACHE_DIR if self.CACHE_PERSISTENT else None,
            self.SCREENSHOTS_DIR if self.CAPTURE_SCREENSHOTS else None
        ]
        
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)
                
    def _setup_detection_modes(self):
        default_modes = {
            "simple": {
                "MAX_CONCURRENT_TASKS": 50,
                "CONNECTION_TIMEOUT": 3,
                "READ_TIMEOUT": 10,
                "DELAY_BETWEEN_REQUESTS": 0.0,
                "REQUEST_RANDOMIZATION": False,
                "CONFIDENCE_THRESHOLD": 0.5,
                "MAX_RETRIES": 1,
                "USE_RANDOM_USER_AGENTS": False,
                "VERIFY_FOUND_URLS": False,
                "MAX_PATHS": 1000,
                "DESCRIPTION": "Quick scan with minimal requests"
            },
            "aggressive": {
                "MAX_CONCURRENT_TASKS": 100,
                "CONNECTION_TIMEOUT": 5,
                "READ_TIMEOUT": 15,
                "DELAY_BETWEEN_REQUESTS": 0.0,
                "REQUEST_RANDOMIZATION": False,
                "CONFIDENCE_THRESHOLD": 0.6,
                "MAX_RETRIES": 3,
                "USE_RANDOM_USER_AGENTS": True,
                "VERIFY_FOUND_URLS": True,
                "MAX_PATHS": 10000,
                "DESCRIPTION": "Thorough scan with maximum coverage"
            },
            "stealth": {
                "MAX_CONCURRENT_TASKS": 10,
                "CONNECTION_TIMEOUT": 8,
                "READ_TIMEOUT": 20,
                "DELAY_BETWEEN_REQUESTS": 1.5,
                "REQUEST_RANDOMIZATION": True,
                "CONFIDENCE_THRESHOLD": 0.7,
                "MAX_RETRIES": 2,
                "USE_RANDOM_USER_AGENTS": True,
                "VERIFY_FOUND_URLS": True,
                "MAX_PATHS": 500,
                "DESCRIPTION": "Slow, careful scan to avoid detection"
            }
        }
        
        if not self.MODE_CONFIGS:
            self.MODE_CONFIGS = default_modes
        else:
            for mode, config in default_modes.items():
                if mode not in self.MODE_CONFIGS:
                    self.MODE_CONFIGS[mode] = config
                else:
                    for key, value in config.items():
                        if key not in self.MODE_CONFIGS[mode]:
                            self.MODE_CONFIGS[mode][key] = value
        
        if self.DETECTION_MODE in self.MODE_CONFIGS:
            mode_config = self.MODE_CONFIGS[self.DETECTION_MODE]
            self.MAX_CONCURRENT_TASKS = mode_config.get("MAX_CONCURRENT_TASKS", self.MAX_CONCURRENT_TASKS)
            self.CONNECTION_TIMEOUT = mode_config.get("CONNECTION_TIMEOUT", self.CONNECTION_TIMEOUT)
            self.READ_TIMEOUT = mode_config.get("READ_TIMEOUT", self.READ_TIMEOUT)
            
            adv_logger.log_info(f"Applied {self.DETECTION_MODE} mode configuration with {self.MAX_CONCURRENT_TASKS} concurrent tasks")
    
    def save_config(self, filepath: str = "config/config.json"):
        config_dict = {
            key: value for key, value in self.__dict__.items() 
            if not key.startswith('_') and not callable(value)
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=4)
            
    def load_config(self, filepath: str = "config/config.json"):
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    config_data = json.load(f)
                
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                adv_logger.log_info(f"Configuration loaded from {filepath}")
            else:
                adv_logger.log_warning(f"Configuration file {filepath} not found, using defaults")
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
        except json.JSONDecodeError as e:
            adv_logger.log_error(f"Error parsing configuration file {filepath}: {str(e)}")
        except Exception as e:
            adv_logger.log_error(f"Error loading configuration: {str(e)}")
            
    def get_current_mode_config(self) -> Dict:
        return self.MODE_CONFIGS.get(self.DETECTION_MODE, {})
    
    def set_detection_mode(self, mode: str):
        if mode in self.MODE_CONFIGS:
            self.DETECTION_MODE = mode
            self._setup_detection_modes()
            adv_logger.log_info(f"Detection mode changed to: {mode}")
        else:
            adv_logger.log_warning(f"Unknown detection mode: {mode}")
    
    def get_rate_limit_config(self) -> Dict:
        return {
            "enabled": self.USE_RATE_LIMITING,
            "rate": self.RATE_LIMIT,
            "burst": self.RATE_LIMIT_BURST,
            "adaptive": self.ADAPTIVE_RATE_LIMITING
        }
    
    def get_proxy_config(self) -> Dict:
        return {
            "enabled": self.USE_PROXIES,
            "list_file": self.PROXY_LIST_FILE,
            "rotation": self.PROXY_ROTATION_STRATEGY,
            "max_failures": self.PROXY_MAX_FAILURES,
            "health_check_interval": self.PROXY_HEALTH_CHECK_INTERVAL
        }
    
    def get_fuzzing_config(self) -> Dict:
        return {
            "enabled": self.USE_PATH_FUZZING,
            "depth": self.FUZZING_DEPTH,
            "extensions": self.FUZZING_EXTENSIONS,
            "backups": self.FUZZING_BACKUPS,
            "case_variations": self.FUZZING_CASE_VARIATIONS
        }

