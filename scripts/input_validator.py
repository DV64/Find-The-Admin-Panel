
import re
import os
from urllib.parse import urlparse, unquote
from typing import Tuple, Optional, List
from scripts.constants import (
    URL_PATTERN, EMAIL_PATTERN, IP_ADDRESS_PATTERN,
    MAX_URL_LENGTH, MAX_PATH_LENGTH, MAX_FILENAME_LENGTH,
    FORBIDDEN_PATH_CHARS, PROXY_TYPES
)


class InputValidator:
    
    def __init__(self):
        self.url_pattern = URL_PATTERN
        self.email_pattern = EMAIL_PATTERN
        self.ip_pattern = IP_ADDRESS_PATTERN
        
        self.control_chars = set(chr(i) for i in range(32)) - {'\t', '\n', '\r'}
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        if not url:
            return False, "URL cannot be empty"
        
        url = url.strip()
        
        if len(url) > MAX_URL_LENGTH:
            return False, f"URL exceeds maximum length of {MAX_URL_LENGTH} characters"
        
        url = self._filter_control_chars(url)
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            
            if not parsed.netloc:
                return False, "Invalid URL: missing domain"
            
            if self._has_suspicious_patterns(url):
                return False, "URL contains suspicious patterns"
            
            normalized_url = f"{parsed.scheme}://{parsed.netloc}"
            if parsed.path:
                normalized_url += parsed.path.rstrip('/')
            
            return True, normalized_url
            
        except Exception as e:
            return False, f"URL parsing error: {str(e)}"
    
    def validate_path(self, path: str) -> Tuple[bool, str]:
        if not path:
            return False, "Path cannot be empty"
        
        if len(path) > MAX_PATH_LENGTH:
            return False, f"Path exceeds maximum length of {MAX_PATH_LENGTH} characters"
        
        path = self._filter_control_chars(path)
        
        for forbidden in FORBIDDEN_PATH_CHARS:
            if forbidden in path:
                return False, f"Path contains forbidden pattern: {repr(forbidden)}"
        
        try:
            decoded_path = unquote(path)
            for forbidden in FORBIDDEN_PATH_CHARS:
                if forbidden in decoded_path:
                    return False, f"Path contains forbidden pattern after decoding"
        except Exception:
            pass
        
        path = path.replace('\\', '/')
        
        path = path.lstrip('/')
        
        return True, path
    
    def validate_paths_list(self, paths: List[str]) -> List[str]:
        valid_paths = []
        for path in paths:
            is_valid, result = self.validate_path(path)
            if is_valid:
                valid_paths.append(result)
        return valid_paths
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        if not email:
            return False, "Email cannot be empty"
        
        email = email.strip().lower()
        
        if len(email) > 254:
            return False, "Email address too long"
        
        if self.email_pattern.match(email):
            return True, email
        
        return False, "Invalid email format"
    
    def validate_ip_address(self, ip: str) -> Tuple[bool, str]:
        if not ip:
            return False, "IP address cannot be empty"
        
        ip = ip.strip()
        
        if self.ip_pattern.match(ip):
            return True, ip
        
        return False, "Invalid IP address format"
    
    def validate_proxy_url(self, proxy_url: str) -> Tuple[bool, str]:
        if not proxy_url:
            return False, "Proxy URL cannot be empty"
        
        proxy_url = proxy_url.strip()
        
        valid_schemes = ['http://', 'https://', 'socks4://', 'socks5://']
        has_valid_scheme = any(proxy_url.lower().startswith(scheme) for scheme in valid_schemes)
        
        if not has_valid_scheme:
            return False, f"Proxy URL must start with one of: {', '.join(valid_schemes)}"
        
        try:
            parsed = urlparse(proxy_url)
            
            if not parsed.netloc:
                return False, "Invalid proxy URL: missing host"
            
            host = parsed.hostname
            port = parsed.port
            
            if not host:
                return False, "Invalid proxy URL: missing host"
            
            if not self.ip_pattern.match(host):
                if not re.match(r'^[a-zA-Z0-9.-]+$', host):
                    return False, "Invalid proxy hostname"
            
            return True, proxy_url
            
        except Exception as e:
            return False, f"Proxy URL parsing error: {str(e)}"
    
    def sanitize_filename(self, filename: str) -> str:
        if not filename:
            return "untitled"
        
        filename = self._filter_control_chars(filename)
        
        filename = filename.replace('/', '_').replace('\\', '_')
        
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        filename = filename.strip('. ')
        
        if len(filename) > MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            max_name_length = MAX_FILENAME_LENGTH - len(ext)
            filename = name[:max_name_length] + ext
        
        return filename or "untitled"
    
    def validate_integer(self, value: str, min_val: int = None, max_val: int = None) -> Tuple[bool, int]:
        try:
            parsed = int(value)
            
            if min_val is not None and parsed < min_val:
                return False, 0
            
            if max_val is not None and parsed > max_val:
                return False, 0
            
            return True, parsed
            
        except (ValueError, TypeError):
            return False, 0
    
    def _filter_control_chars(self, text: str) -> str:
        return ''.join(char for char in text if char not in self.control_chars)
    
    def _has_suspicious_patterns(self, url: str) -> bool:
        suspicious_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'<script',
            r'</script>',
            r'onerror=',
            r'onload=',
            r'onclick=',
        ]
        
        url_lower = url.lower()
        return any(re.search(pattern, url_lower) for pattern in suspicious_patterns)


_validator = None


def get_validator() -> InputValidator:
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


def validate_url(url: str) -> Tuple[bool, str]:
    return get_validator().validate_url(url)


def validate_path(path: str) -> Tuple[bool, str]:
    return get_validator().validate_path(path)


def validate_paths_list(paths: List[str]) -> List[str]:
    return get_validator().validate_paths_list(paths)


def sanitize_filename(filename: str) -> str:
    return get_validator().sanitize_filename(filename)
