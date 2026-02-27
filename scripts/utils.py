import os
import re
import sys
import signal
import asyncio
import urllib.parse
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import hashlib
import random
import string
import socket
import platform

from scripts.logger import get_logger

adv_logger = get_logger('logs')

def validate_url(url: str) -> Tuple[bool, str]:
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    if not re.match(r'^https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}', url):
        return False, url
    
    if not url.endswith('/'):
        url += '/'
    
    return True, url

def validate_path(path: str) -> str:
    if path.startswith('/'):
        path = path[1:]
    
    path = urllib.parse.quote(path, safe='/')
    
    return path

def join_url(base_url: str, path: str) -> str:
    if not base_url.endswith('/'):
        base_url += '/'
    
    if path.startswith('/'):
        path = path[1:]
    
    return urllib.parse.urljoin(base_url, path)

def count_lines_in_file(filepath: str) -> int:
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception as e:
        adv_logger.log_error(f"Error counting lines in file {filepath}: {str(e)}")
        return 0

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_random_string(length: int = 8) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_file_size(filepath: str) -> int:
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        adv_logger.log_error(f"Error getting file size for {filepath}: {str(e)}")
        return 0

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_system_info() -> Dict[str, str]:
    try:
        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': socket.gethostname(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
    except Exception as e:
        adv_logger.log_error(f"Error getting system info: {str(e)}")
        return {}

def setup_signal_handler(scanner) -> None:
    last_press_time = None
    press_count = 0
    
    def signal_handler(sig, frame):
        nonlocal last_press_time, press_count
        current_time = datetime.now()
        
        if last_press_time is None or (current_time - last_press_time).total_seconds() > 2:
            press_count = 1
            last_press_time = current_time
            
            if scanner and scanner.is_running():
                print("\n\nStopping scan. Press Ctrl+C again within 2 seconds to exit immediately.")
                adv_logger.log_warning("Scan interrupted by user (Ctrl+C)")
                scanner.stop_scan()
            else:
                print("\n\nExiting...")
                adv_logger.log_info("Application exited by user (Ctrl+C)")
                sys.exit(0)
        else:
            press_count += 1
            adv_logger.log_info("Application force exited by user (double Ctrl+C)")
            print("\n\nForce exiting...")
            sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

async def run_with_timeout(coro, timeout):
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        return None

def group_by_status_code(results: List[Dict]) -> Dict[int, List[Dict]]:
    grouped = {}
    
    for result in results:
        status_code = result.get('status_code', 0)
        if status_code not in grouped:
            grouped[status_code] = []
        grouped[status_code].append(result)
    
    return grouped

def find_results_by_confidence(results: List[Dict], min_confidence: float = 0.7) -> List[Dict]:

    return [r for r in results if r.get('confidence', 0) >= min_confidence] 
