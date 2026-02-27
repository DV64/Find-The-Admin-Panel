import os
import aiohttp
import asyncio
import time
import random
import re

import signal
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console
from urllib.parse import urlparse
from aiohttp import ClientSession, TCPConnector, ClientTimeout
import socket

from scripts.logger import get_logger

adv_logger = get_logger('logs')
console = Console()

class Scanner:
    
    def __init__(self, config):
        self.config = config
        self.session = None
        self.running = False
        self.results = []
        self.scan_info = {}
        self.valid_results = []
        
        self.ctrl_c_pressed = 0
        self.last_ctrl_c_time = 0
        self.ctrl_c_timeout = 2
        
        self.success_file = "success.txt"
        
        self.baseline_hash = None
        self.baseline_length = 0
        self.has_catch_all = False
        
        self._setup_signal_handler()
    
    def _setup_signal_handler(self):
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        current_time = time.time()
        
        if self.ctrl_c_pressed > 0 and (current_time - self.last_ctrl_c_time) < self.ctrl_c_timeout:
            console.print("\n\n[bold red]Exiting application (Ctrl+C pressed twice).[/bold red]")
            self._save_current_results()  
            os._exit(0)  
        
        self.ctrl_c_pressed += 1
        self.last_ctrl_c_time = current_time
        
        if self.ctrl_c_pressed == 1:
            console.print("\n\n[bold yellow]Scan interrupted by user. Stopping scan and displaying current results...[/bold yellow]")
            
            self.stop_scan()
            
            self._display_current_results()
            
            console.print("\n[bold yellow]Press Ctrl+C again within 2 seconds to exit the application.[/bold yellow]")
            console.print("[bold yellow]Or press Enter to continue...[/bold yellow]")
    
    def _display_current_results(self):
        if not self.results:
            console.print("[yellow]No results available yet.[/yellow]")
            return
        
        valid_results = [r for r in self.results if isinstance(r, dict)]
        found_count = sum(1 for r in valid_results if r.get("found", False))
        total_count = len(valid_results)
        
        console.print(f"\n[bold cyan]Scan Summary (Interrupted)[/bold cyan]")
        if self.scan_info:
            console.print(f"Target URL: {self.scan_info.get('url', 'Unknown')}")
            console.print(f"Mode: {self.scan_info.get('mode', 'Unknown')}")
        console.print(f"Found: [bold green]{found_count}[/bold green] potential admin panels out of [bold]{total_count}[/bold] checked")
        
        if found_count > 0:
            console.print("\n[bold green]Potential Admin Panels:[/bold green]")
            for result in valid_results:
                if result.get("found", False):
                    try:
                        console.print(f"  - {result['url']} (Confidence: {result['confidence']:.2f}, Status: {result['status_code']})")
                    except (KeyError, TypeError):
                        console.print(f"  - {result.get('url', 'Unknown URL')} (Incomplete result data)")
    
    def _save_current_results(self):
        if not self.results:
            return
            
        found_results = []
        for r in self.results:
            if isinstance(r, dict) and r.get("found", False):
                found_results.append(r)
                
        if not found_results:
            return
            
        try:
            with open(self.success_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Interrupted Scan Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                for result in found_results:
                    f.write(f"URL: {result['url']}\n")
                    f.write(f"Title: {result['title']}\n")
                    f.write(f"Confidence: {result['confidence']:.2f}\n")
                    f.write(f"Status Code: {result['status_code']}\n")
                    f.write("-" * 50 + "\n")
        except Exception as e:
            adv_logger.log_error(f"Error saving results to {self.success_file}: {str(e)}")

    @classmethod
    async def create(cls, config):

        scanner = cls(config)
        await scanner.create_session()
        return scanner
        
    async def create_session(self):
        try:
            connector = TCPConnector(
                ssl=False,  
                limit=self.config.MAX_CONCURRENT_TASKS,
                ttl_dns_cache=300,  
                force_close=False,  
                enable_cleanup_closed=True,
                family=socket.AF_INET,  
                keepalive_timeout=30.0,  
                limit_per_host=8  
            )
            
            timeout = ClientTimeout(
                total=self.config.CONNECTION_TIMEOUT,
                connect=self.config.CONNECTION_TIMEOUT/2,
                sock_read=self.config.READ_TIMEOUT,
                sock_connect=self.config.CONNECTION_TIMEOUT/3
            )
            
            self.session = ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True,
                auto_decompress=True,  
                raise_for_status=False,  
                cookie_jar=aiohttp.CookieJar(unsafe=True)  
            )
            
            adv_logger.log_info("Created HTTP session for scanning with enhanced connection settings")
            return True
        except Exception as e:
            adv_logger.log_error(f"Error creating HTTP session: {str(e)}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        if not self.config.USER_AGENTS:
            adv_logger.log_warning("No user agents configured. Using default.")
            return {"User-Agent": "Mozilla/5.0 (compatible; AdminPanelFinder/1.0)"}
        
        user_agent = random.choice(self.config.USER_AGENTS)
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5,ar;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        if hasattr(self.config, 'HEADERS_EXTRA') and self.config.HEADERS_EXTRA:
            headers.update(self.config.HEADERS_EXTRA)
            
        return headers

    def _extract_title(self, content: str) -> str:
        try:
            title_match = re.search('<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if title_match:
                return title_match.group(1).strip()
        except Exception as e:
            adv_logger.log_debug(f"Error extracting title: {str(e)}")
        return "Unknown"

    def _detect_error_page(self, content: str, title: str, status_code: int) -> bool:

        error_keywords = [
            "404", "not found", "error", "page not found", "doesn't exist",
            "page does not exist", "cannot be found", "no encontrada", 
            "não encontrada", "nie znaleziono", "не найдено", "找不到",
            "存在しません", "صفحة غير موجودة", "access denied", "forbidden",
            "accès refusé", "zugriff verweigert", "seite existiert nicht"
        ]
        
        if title:
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in error_keywords):
                adv_logger.log_debug(f"Error page detected based on title: {title}")
                return True
        
        error_phrases = [
            "page cannot be found", "page you requested could not be found",
            "page you are looking for does not exist", "404 error", 
            "page doesn't exist", "resource cannot be found", 
            "site you were looking for doesn't exist",
            "file or directory not found", "requested url was not found",
            "requested page does not exist", "sorry, the page you are looking for is not available"
        ]
        
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in error_phrases):
            adv_logger.log_debug("Error page detected based on content phrases")
            return True
        
        error_patterns = [
            re.search(r'<div[^>]*class=["\'](?:[^"\']*\s)?(?:error|not-found|404)(?:\s[^"\']*)?["\']', content, re.IGNORECASE),
            re.search(r'<h1[^>]*>.*(?:404|not found|error|not available).*</h1>', content, re.IGNORECASE | re.DOTALL),
            re.search(r'<body[^>]*class=["\'](?:[^"\']*\s)?(?:error|not-found)(?:\s[^"\']*)?["\']', content, re.IGNORECASE)
        ]
        
        if any(error_patterns):
            adv_logger.log_debug("Error page detected based on HTML patterns")
            return True
            
        if status_code == 200 and len(content) < 2000 and re.search(r'not\s+found|doesn[\'"]?t\s+exist', content_lower):
            adv_logger.log_debug("Likely error page masquerading as 200 OK")
            return True
            
        return False

    def _has_login_form(self, content: str) -> bool:
        login_indicators = [
            re.search(r'<form[^>]*>.*?<input[^>]*type=["\']password["\'].*?</form>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<form[^>]*>.*?(?:login|log[_\s]?in|sign[_\s]?in|admin|authenticate|session|account|auth|password).*?</form>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<input[^>]*(?:name|id|placeholder)=["\'](?:username|user|email|login|admin|account|user_?name)["\']', content, re.IGNORECASE),
            re.search(r'<button[^>]*>.*?(?:login|log[_\s]?in|sign[_\s]?in|submit|enter|access).*?</button>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<input[^>]*type=["\']submit["\'][^>]*value=["\'](?:login|log[_\s]?in|sign[_\s]?in|submit|enter|access)["\']', content, re.IGNORECASE),
            re.search(r'<form[^>]*>.*?(?:connexion|s\'identifier|connecter|identifiant|iniciar sesión|acceso|ingresar|entrar|anmelden|einloggen|登录|登入|ログイン).*?</form>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<(?:div|form|section)[^>]*class=["\'](?:[^"\']*\s)?(?:login|signin|auth|account)(?:\s[^"\']*)?["\']', content, re.IGNORECASE),
        ]
        
        return any(login_indicators)

    def _detect_technologies(self, content: str, headers: Dict) -> List[str]:
        techs = []
        
        tech_signatures = {
            "WordPress": ["wp-content", "wp-includes", "wp-admin", "/wp-", "wordpress"],
            "Joomla": ["joomla", "com_content", "com_users", "/administrator/", "Joomla!"],
            "Drupal": ["drupal", "sites/all", "sites/default", "node/add", "Drupal.settings"],
            "Laravel": ["laravel", "csrf-token", "_token", "Laravel", "Illuminate\\"],
            "Django": ["csrfmiddlewaretoken", "django", "djangoproject", "csrftoken"],
            "Angular": ["ng-app", "ng-controller", "angular", "ng-bind", "ng-model"],
            "React": ["react", "react-dom", "reactjs", "_reactListening", "createElement"],
            "Vue.js": ["vue", "vue.js", "vuejs", "v-bind", "v-model", "v-for", "v-if"],
            "Bootstrap": ["bootstrap.css", "bootstrap.min.css", "bootstrap.js", "navbar-toggler", "container-fluid"],
            "jQuery": ["jquery.js", "jquery.min.js", "jQuery(", "$(document)"],
            "PHP": ["php", ".php", "PHP_SESSION_", "PHPSESSID"],
            "ASP.NET": ["asp.net", ".aspx", "viewstate", "__VIEWSTATE", "WebForm_"],
            "Node.js": ["node_modules", "Express", "npm", "package.json"],
            "Express": ["express", "powered by express"],
            "Nginx": ["nginx", "openresty"],
            "Apache": ["apache", "httpd"],
            "IIS": ["IIS", "ASP.NET", "X-Powered-By: ASP.NET"],
            "Flask": ["flask", "werkzeug", "jinja"],
            "Symfony": ["symfony", "sf-toolbar", "Twig"],
            "Magento": ["magento", "Mage.Cookies", "/skin/frontend/"],
            "PrestaShop": ["prestashop", "PrestaShop", "/modules/"],
            "Shopify": ["shopify", "Shopify.theme", "/cdn.shopify.com/"],
            "WooCommerce": ["woocommerce", "is-woocommerce", "/wp-content/plugins/woocommerce/"],
            "OpenCart": ["opencart", "catalog/view/theme"],
            "Cloudflare": ["cloudflare", "__cf", "cf-ray", "cf-cache-status"],
            "Google Analytics": ["google-analytics", "gtag", "GoogleAnalyticsObject", "ga('create'"],
            "SiteMinder": ["siteminder", "SMSESSION"],
            "Okta": ["okta", "OktaAuth", "/okta-signin-widget/"],
            "Auth0": ["auth0", "Auth0Lock", "auth0.min.js"],
            "HTTP/2": ["HTTP/2", "h2", "h2-"],
            "HTTP/3": ["HTTP/3", "h3", "quic", "alt-svc"]
        }
        
        for tech, signatures in tech_signatures.items():
            if any(sig.lower() in content.lower() for sig in signatures if sig):
                techs.append(tech)
        
        if headers:
            for tech, signatures in tech_signatures.items():
                for header_name, header_value in headers.items():
                    if header_value and any(sig.lower() in header_value.lower() for sig in signatures if sig):
                        techs.append(tech)
                        
            if "X-Powered-By" in headers:
                techs.append(headers["X-Powered-By"])
                
                php_match = re.search(r'PHP/([0-9.]+)', headers.get("X-Powered-By", ""))
                if php_match:
                    techs.append(f"PHP {php_match.group(1)}")
                
            if "Server" in headers:
                server = headers["Server"]
                techs.append(server)
                
                nginx_match = re.search(r'nginx/([0-9.]+)', server)
                if nginx_match:
                    techs.append(f"Nginx {nginx_match.group(1)}")
                    
                apache_match = re.search(r'Apache/([0-9.]+)', server)
                if apache_match:
                    techs.append(f"Apache {apache_match.group(1)}")
            
            if "alt-svc" in headers and ("h3" in headers["alt-svc"] or "quic" in headers["alt-svc"]):
                techs.append("HTTP/3")
            
            if "via" in headers and "HTTP/2" in headers["via"]:
                techs.append("HTTP/2")
            
            security_headers = {
                "X-XSS-Protection": "XSS Protection",
                "Content-Security-Policy": "CSP",
                "X-Content-Type-Options": "Content Type Options",
                "X-Frame-Options": "Frame Options",
                "Strict-Transport-Security": "HSTS"
            }
            
            for header, tech_name in security_headers.items():
                if header in headers:
                    techs.append(f"Security: {tech_name}")
                
        generator_match = re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if generator_match:
            techs.append(f"Generator: {generator_match.group(1)}")
        
        return list(set(techs))

    def _detect_admin_layout(self, content: str) -> float:
        score = 0.0
        
        if re.search(r'<(?:div|nav|aside)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:sidebar|side-nav|admin-nav|navigation|main-menu)(?:\s[^"\']*)?["\']', content, re.IGNORECASE):
            score += 0.15
        
        if re.search(r'<(?:div|section)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:card|widget|panel|dashboard-item|stat|metric)(?:\s[^"\']*)?["\']', content, re.IGNORECASE):
            score += 0.10
        
        table_patterns = [
            re.search(r'<table[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:admin|data-table|list-table|users|records)(?:\s[^"\']*)?["\']', content, re.IGNORECASE),
            re.search(r'<th[^>]*>.*?(?:ID|Name|User|Email|Status|Actions|Edit|Delete|Role|Permission).*?</th>', content, re.DOTALL | re.IGNORECASE)
        ]
        if any(table_patterns):
            score += 0.10
        
        action_buttons = [
            re.search(r'<(?:a|button)[^>]*>.*?(?:Add New|Create New|New|Add|Edit|Update|Delete|Remove).*?</(?:a|button)>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<(?:a|button)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:add-new|create-new|btn-add|btn-edit|btn-delete)(?:\s[^"\']*)?["\']', content, re.IGNORECASE)
        ]
        if any(action_buttons):
            score += 0.08
        
        if re.search(r'<(?:div|nav|ul)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:breadcrumb|breadcrumbs)(?:\s[^"\']*)?["\']', content, re.IGNORECASE):
            score += 0.05
        
        admin_footer = [
            re.search(r'<(?:div|footer)[^>]*>.*?(?:Admin|Administration|Dashboard|©|Copyright).*?</(?:div|footer)>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<(?:div|footer)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:admin-footer|dashboard-footer)(?:\s[^"\']*)?["\']', content, re.IGNORECASE)
        ]
        if any(admin_footer):
            score += 0.05
        
        return min(score, 0.40)

    def _check_meta_indicators(self, content: str) -> float:

        score = 0.0
        
        meta_patterns = [
            re.search(r'<meta[^>]*name=["\'](?:application-name|app-name)["\'][^>]*content=["\'][^"\']*(?:admin|dashboard|control)[^"\']*["\']', content, re.IGNORECASE),
            re.search(r'<meta[^>]*content=["\'][^"\']*(?:admin|dashboard|control)[^"\']*["\'][^>]*name=["\'](?:application-name|app-name)["\']', content, re.IGNORECASE),
            re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\'][^"\']*(?:wordpress|joomla|drupal|admin|cms)[^"\']*["\']', content, re.IGNORECASE)
        ]
        if any(meta_patterns):
            score += 0.05
        
        js_patterns = [
            re.search(r'<script[^>]*src=["\'][^"\']*(?:admin|dashboard|control)[^"\']*\.js["\']', content, re.IGNORECASE),
            re.search(r'<script[^>]*src=["\'][^"\']*(?:wp-admin|admin-ajax|adminify)[^"\']*["\']', content, re.IGNORECASE)
        ]
        if any(js_patterns):
            score += 0.05
        
        css_patterns = [
            re.search(r'<link[^>]*href=["\'][^"\']*(?:admin|dashboard|control)[^"\']*\.css["\']', content, re.IGNORECASE),
            re.search(r'<link[^>]*href=["\'][^"\']*(?:wp-admin|admin-styles|adminify)[^"\']*["\']', content, re.IGNORECASE)
        ]
        if any(css_patterns):
            score += 0.05
        
        return min(score, 0.15)  

    def _analyze_content_keywords(self, content: str) -> float:
        score = 0.0
        content_lower = content.lower()
        
        multilingual_admin_keywords = [
            "admin panel", "dashboard", "control panel", "administration", "site admin",
            "user management", "permissions", "settings", "login", "account", "administrator",
            "stats", "statistics", "reports",
            
            "admin", "panel", "manage", "config", "backend",
            
            "login", "user", "control", "access", "system", "management",
            "security", "permission", "setting", "config", "account", "profile",
            "password", "auth", "log", "stat", "report", "dashboard", "admin"
        ]
        
        for keyword in multilingual_admin_keywords:
            if keyword in content_lower:
                score += 0.02
                if score > 0.20:
                    break
        
        admin_features = [
            "user management", "user administration", "content management", "site settings", 
            "configuration", "system settings", "site options",
            
            "gestión de usuarios", "administración", "panel de control",
            
            "gestion des utilisateurs", "administration", "tableau de bord",
            
            "權限管理", "权限管理", "用户管理", "站点设置",
            
            "benutzerverwaltung", "administration", "einstellungen", "systemkonfiguration",
            
            "admin", "dashboard", "control", "panel", "manage", "users", "settings"
        ]
        
        for feature in admin_features:
            if feature.lower() in content_lower:
                score += 0.02
                if score > 0.20:
                    break
        
        return min(score, 0.20)  

    def _get_response_hash(self, content: str) -> int:
        if not content:
            return 0
        normalized = re.sub(r'\s+', ' ', content.lower()).strip()
        return hash(normalized)
    
    def _is_similar_response(self, content: str, length: int) -> bool:
        if not self.baseline_hash:
            return False
        
        content_hash = self._get_response_hash(content)
        
        length_diff = abs(length - self.baseline_length)
        length_similarity = 1 - (length_diff / max(self.baseline_length, length, 1))
        
        hash_match = (content_hash == self.baseline_hash)
        length_similar = (length_similarity > 0.95)
        
        return hash_match or length_similar

    def _analyze_response_headers(self, headers: Dict) -> float:
        score = 0.0
        
        if any(header in headers for header in ["WWW-Authenticate", "X-Permitted-Cross-Domain-Policies"]):
            score += 0.05
        
        cookies = headers.get("Set-Cookie", "")
        if re.search(r'(csrf|xsrf|token|admin|session|auth)', cookies, re.IGNORECASE):
            score += 0.05
        
        if "X-Powered-By" in headers and re.search(r'(wordpress|joomla|drupal|laravel|django|rails)', headers["X-Powered-By"], re.IGNORECASE):
            score += 0.03
        
        cache_headers = headers.get("Cache-Control", "")
        if "no-store" in cache_headers or "private" in cache_headers:
            score += 0.02
        
        return min(score, 0.10)  

    def _calculate_confidence(self, status_code: int, content: str, title: str, path: str, headers: Dict) -> float:
        confidence = 0.0
        content_length = len(content) if content else 0
        has_login = self._has_login_form(content) if content else False
        
        confidence_factors = []
        
        if not content or content_length < 50:
            adv_logger.log_debug(f"Response too small or empty for {path}")
            return 0.0
            
        if status_code == 200:  
            confidence += 0.3
            confidence_factors.append(f"Status 200 OK: +0.3")
        elif status_code == 403:  
            confidence += 0.35
            confidence_factors.append(f"Status 403 Forbidden (potential protected admin area): +0.35")
        elif status_code == 401:  
            confidence += 0.45  
            confidence_factors.append(f"Status 401 Unauthorized (definite protected area): +0.45")
        elif status_code == 302 or status_code == 301:  
            confidence += 0.1
            confidence_factors.append(f"Status {status_code} Redirect: +0.1")
        elif status_code >= 500:  
            confidence += 0.05  
            confidence_factors.append(f"Status {status_code} Server Error: +0.05")
        elif status_code == 404:
            confidence = 0.0
            confidence_factors.append(f"Status 404 Not Found: +0.0")
            return confidence
        
        if has_login:
            confidence += 0.25
            confidence_factors.append(f"Contains login form: +0.25")
            
            input_count = content.count('<input')
            password_count = content.count('type="password"') + content.count("type='password'")
            
            if password_count > 0:
                confidence += 0.15
                confidence_factors.append(f"Contains password field: +0.15")
                
            if input_count > 5:  
                confidence -= 0.05
                confidence_factors.append(f"Complex form (many fields): -0.05")
        
        admin_keywords = ['admin', 'administration', 'administrator', 'admincp', 'adm', 'moderator', 
                         'dashboard', 'control panel', 'cp', 'panel', 'login', 'manager', 'cms', 'backend']
        
        if title and any(keyword in title.lower() for keyword in admin_keywords):
            title_bonus = 0.35
            confidence += title_bonus
            matching_keywords = [k for k in admin_keywords if k in title.lower()]
            confidence_factors.append(f"Admin keyword in title ({', '.join(matching_keywords)}): +{title_bonus}")

        path_lower = path.lower()
        if any(keyword in path_lower for keyword in ['admin', 'adm', 'cp', 'control', 'panel', 'dashboard', 'login']):
            path_bonus = 0.15
            confidence += path_bonus
            confidence_factors.append(f"Admin keyword in path: +{path_bonus}")
            
        techs = self._detect_technologies(content, headers)
        if techs:
            cms_admin_bonus = 0.10
            confidence += cms_admin_bonus
            confidence_factors.append(f"CMS technologies detected ({', '.join(techs)}): +{cms_admin_bonus}")
            
            if 'WordPress' in techs and ('wp-login' in path_lower or 'wp-admin' in path_lower):
                wp_bonus = 0.20
                confidence += wp_bonus
                confidence_factors.append(f"WordPress admin path match: +{wp_bonus}")
        
        layout_score = self._detect_admin_layout(content)
        confidence += layout_score
        confidence_factors.append(f"Admin layout detection: +{layout_score:.2f}")
        
        meta_score = self._check_meta_indicators(content)
        confidence += meta_score
        confidence_factors.append(f"Meta tag indicators: +{meta_score:.2f}")
        
        keyword_score = self._analyze_content_keywords(content)
        confidence += keyword_score
        confidence_factors.append(f"Content keyword analysis: +{keyword_score:.2f}")
        
        header_score = self._analyze_response_headers(headers)
        confidence += header_score
        confidence_factors.append(f"Response header analysis: +{header_score:.2f}")
        
        if "Welcome to nginx" in content or "Apache2 Ubuntu Default Page" in content or "404" in title:
            confidence -= 0.4
            confidence_factors.append("Default server page or 404 page penalty: -0.4")
            
        user_facing_indicators = [
            'shopping cart', 'add to cart', 'checkout', 'product', 'category', 
            'blog post', 'comment', 'article', 'news', 'contact us', 'about us',
            'privacy policy', 'terms of service', 'faq', 'help center'
        ]
        
        user_facing_count = sum(1 for indicator in user_facing_indicators if indicator in content.lower())
        if user_facing_count > 2:  
            penalty = min(0.4, user_facing_count * 0.1)  
            confidence -= penalty
            confidence_factors.append(f"User-facing content penalty: -{penalty:.2f}")
        
        confidence = max(0.0, min(1.0, confidence))
        
        if confidence > 0.4:  
            details = ", ".join(confidence_factors)
            adv_logger.log_debug(f"Confidence calculation for {path} = {confidence:.2f}: {details}")
        
        return confidence

    async def scan_path(self, base_url: str, path: str) -> Dict:
        try:
            if not self.running:
                return {}
                
            if self.config.DETECTION_MODE == "stealth":
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            if not base_url or not path:
                return {}
                
            full_url = f"{base_url}/{path}".replace("//", "/").replace(":/", "://")
            headers = self._get_headers()
            
            if not self.session:
                adv_logger.log_error(f"No active session for scanning {full_url}")
                return {}
                
            async with self.session.get(full_url, headers=headers, allow_redirects=True, 
                                      timeout=self.config.CONNECTION_TIMEOUT) as response:
                status = response.status
                if status == 404:
                    return {}
                    
                content = await response.text(errors='ignore')
                title = self._extract_title(content)
                
                if self._detect_error_page(content, title, status):
                    adv_logger.log_debug(f"Detected error page for {path} with status {status} and title '{title}'")
                    return {}
                
                response_headers_dict = dict(response.headers)
                
                if self.has_catch_all and self._is_similar_response(content, len(content)):
                    adv_logger.log_debug(f"Skipping {path} - matches baseline catch-all response")
                    return {}
                
                confidence = self._calculate_confidence(status, content, title, path, response_headers_dict)
                
                result = {
                    "url": full_url,
                    "status_code": status,
                    "title": title,
                    "confidence": confidence,
                    "found": confidence > 0.6,  
                    "has_login_form": self._has_login_form(content),
                    "technologies": self._detect_technologies(content, response_headers_dict),
                    "headers": response_headers_dict,
                    "content_length": len(content),
                    "scan_time": datetime.now().isoformat()
                }
                
                if result["found"]:
                    self._save_result_to_file(result)
                
                return result
        except asyncio.TimeoutError:
            adv_logger.log_debug(f"Timeout scanning {base_url}/{path}")
            return {}
        except Exception as e:
            adv_logger.log_debug(f"Error scanning {base_url}/{path}: {str(e)}")
            return {}

    def _save_result_to_file(self, result: Dict):
        try:
            if not isinstance(result, dict) or "url" not in result:
                adv_logger.log_warning("Attempted to save invalid result")
                return
                
            os.makedirs(self.config.LOGS_DIR, exist_ok=True)
            
            success_file_path = os.path.join(self.config.LOGS_DIR, self.success_file)
            
            with open(success_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n=== FOUND ADMIN PANEL ===\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Title: {result['title']}\n")
                f.write(f"Confidence: {result['confidence']:.2f}\n")
                f.write(f"Status Code: {result['status_code']}\n")
                
                if result.get('has_login_form'):
                    f.write(f"Login Form: Yes\n")
                
                if result.get('technologies'):
                    f.write(f"Technologies: {', '.join(result['technologies'])}\n")
                    
                f.write(f"Content Length: {result.get('content_length', 0)} bytes\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")
                
            with open(self.success_file, 'a', encoding='utf-8') as f:
                f.write(f"\n=== FOUND ADMIN PANEL ===\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Title: {result['title']}\n")
                f.write(f"Confidence: {result['confidence']:.2f}\n")
                f.write(f"Status Code: {result['status_code']}\n")
                f.write("-" * 50 + "\n")
                
        except Exception as e:
            adv_logger.log_error(f"Error saving result to {self.success_file}: {str(e)}")

    async def _detect_catch_all(self, url: str) -> bool:
        test_paths = [
            "this-definitely-does-not-exist-12345",
            "random-nonexistent-path-98765",
            "test-404-page-check"
        ]
        
        responses = []
        for test_path in test_paths:
            try:
                full_url = f"{url}/{test_path}".replace("//", "/").replace(":/", "://")
                headers = self._get_headers()
                
                async with self.session.get(full_url, headers=headers, allow_redirects=True, 
                                          timeout=self.config.CONNECTION_TIMEOUT) as response:
                    if response.status == 200:
                        content = await response.text(errors='ignore')
                        responses.append((len(content), self._get_response_hash(content)))
                    else:
                        return False
            except Exception:
                return False
        
        if len(responses) >= 2:
            lengths = [r[0] for r in responses]
            hashes = [r[1] for r in responses]
            
            avg_length = sum(lengths) / len(lengths)
            length_variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            length_similar = (length_variance < (avg_length * 0.1) ** 2)
            
            all_same_hash = len(set(hashes)) == 1
            
            if all_same_hash or length_similar:
                self.baseline_hash = hashes[0]
                self.baseline_length = int(avg_length)
                adv_logger.log_warning(f"Catch-all route detected! Baseline: {self.baseline_length} bytes, hash: {self.baseline_hash}")
                console.print(f"[bold yellow]⚠ Warning: Site appears to have catch-all routing (returns same page for all paths)[/bold yellow]")
                console.print(f"[yellow]  Baseline response: {self.baseline_length} bytes[/yellow]")
                console.print(f"[yellow]  Filtering will be more aggressive to reduce false positives[/yellow]")
                return True
        
        return False

    async def scan(self, url: str, paths: List[str], concurrency: int = 0) -> List[Dict]:
        if not paths:
            adv_logger.log_warning(f"No paths to scan for {url}")
            return []
        
        self._clear_success_file()
        
        self.running = True
        self.results = []
        self.valid_results = []
        
        mode_config = self.config.get_current_mode_config()
        delay_between_requests = mode_config.get("DELAY_BETWEEN_REQUESTS", 0.0)
        request_randomization = mode_config.get("REQUEST_RANDOMIZATION", False)
        confidence_threshold = mode_config.get("CONFIDENCE_THRESHOLD", 0.6)
        max_retries = mode_config.get("MAX_RETRIES", 2)
        verify_found_urls = mode_config.get("VERIFY_FOUND_URLS", False)
        
        self.scan_info = {
            "url": url,
            "mode": self.config.DETECTION_MODE,
            "start_time": time.time(),
            "paths_count": len(paths),
            "concurrency": concurrency if concurrency > 0 else self.config.MAX_CONCURRENT_TASKS,
            "mode_details": mode_config
        }
        
        adv_logger.log_info(f"Starting scan in {self.config.DETECTION_MODE} mode with confidence threshold {confidence_threshold}")
        
        self.ctrl_c_pressed = 0
        self.last_ctrl_c_time = 0
        
        if not self.session:
            await self.create_session()
            if not self.session:
                adv_logger.log_error("Failed to create session for scanning")
                return []
        
        console.print(f"[cyan]Detecting catch-all routing...[/cyan]")
        self.has_catch_all = await self._detect_catch_all(url)
        
        workers = concurrency or self.config.MAX_CONCURRENT_TASKS
        batch_size = self.config.BATCH_SIZE or min(50, len(paths))
        
        try:
            progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[bold]{task.completed}/{task.total}"),
                TextColumn("[cyan]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            )
            
            console.print(f"[cyan]Starting scan of [bold]{url}[/bold] with [bold]{len(paths)}[/bold] paths[/cyan]")
            console.print(f"[cyan]Using [bold]{workers}[/bold] concurrent workers and batch size of [bold]{batch_size}[/bold][/cyan]")
            console.print(f"[cyan]Mode: [bold]{self.config.DETECTION_MODE}[/bold] - {mode_config.get('DESCRIPTION', '')}[/cyan]")
            
            all_results = []
            found_count = 0
            verified_count = 0
            rejected_count = 0
            
            batches = [paths[i:i + batch_size] for i in range(0, len(paths), batch_size)]
            
            with progress:
                task_id = progress.add_task(f"Scanning {url}", total=len(paths))
                
                status_task_id = progress.add_task(
                    f"Found: [green]{found_count}[/green] Verified: [blue]{verified_count}[/blue] Rejected: [red]{rejected_count}[/red]", 
                    total=1, 
                    completed=0
                )
                
                for batch in batches:
                    if not self.running:  
                        console.print("[yellow]Scan stopped by user.[/yellow]")
                        break
                        
                    if request_randomization:
                        random.shuffle(batch)
                    
                    tasks = [self.scan_path(url, path) for path in batch]
                    
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    batch_found = 0
                    batch_verified = 0
                    batch_rejected = 0
                    
                    filtered_results = []
                    for r in batch_results:
                        if r is not None and not isinstance(r, Exception) and isinstance(r, dict):
                            if "confidence" in r and r["confidence"] >= confidence_threshold:
                                r["found"] = True
                                batch_found += 1
                                filtered_results.append(r)
                            elif "confidence" in r:
                                r["found"] = False
                                filtered_results.append(r)
                    
                    all_results.extend(filtered_results)
                    
                    for result in filtered_results:
                        if result.get("found", False):
                            if verify_found_urls:
                                is_valid = await self._verify_found_url(result.get("url", ""))
                                if is_valid:
                                    batch_verified += 1
                                    self.valid_results.append(result)
                                else:
                                    result["found"] = False
                                    result["confidence"] = 0.0
                                    result["verification_failed"] = True
                                    batch_rejected += 1
                                    adv_logger.log_warning(f"Verification failed for {result.get('url', '')}")
                            else:
                                self.valid_results.append(result)
                                batch_verified += 1
                    
                    found_count += batch_found
                    verified_count += batch_verified
                    rejected_count += batch_rejected
                    
                    progress.update(task_id, advance=len(batch))
                    progress.update(
                        status_task_id, 
                        description=f"Found: [green]{found_count}[/green] Verified: [blue]{verified_count}[/blue] Rejected: [red]{rejected_count}[/red]"
                    )
                    
                    if delay_between_requests > 0:
                        if request_randomization:
                            jitter = delay_between_requests * 0.3  
                            actual_delay = max(0.1, delay_between_requests + random.uniform(-jitter, jitter))
                            await asyncio.sleep(actual_delay)
                        else:
                            await asyncio.sleep(delay_between_requests)
            
            self.scan_info["end_time"] = time.time()
            self.scan_info["duration"] = self.scan_info["end_time"] - self.scan_info["start_time"]
            self.scan_info["found_count"] = len(self.valid_results)
            self.scan_info["total_count"] = len(all_results)
            self.scan_info["success_rate"] = len(self.valid_results) / len(paths) if paths else 0
            self.scan_info["verified_count"] = verified_count
            self.scan_info["rejected_count"] = rejected_count
            
            adv_logger.log_scan_complete(
                url, 
                len(paths), 
                len(self.valid_results), 
                self.scan_info["duration"]
            )
            
            self.valid_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            self.results = all_results
            
            self._write_scan_summary()
            
            return all_results
            
        except asyncio.CancelledError:
            console.print("[yellow]\nScan was cancelled.[/yellow]")
            self._save_current_results()  
            return self.results
        except Exception as e:
            error_message = str(e)
            adv_logger.log_error(f"Error during scan: {error_message}")
            return self.results
            
    async def _verify_found_url(self, url: str) -> bool:
        if not url:
            return False
            
        try:
            headers = {
                "User-Agent": random.choice(self.config.USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            if not self.session:
                return False
                
            async with self.session.get(url, headers=headers, allow_redirects=True, 
                                     timeout=self.config.CONNECTION_TIMEOUT) as response:
                if response.status == 404:
                    return False
                    
                content = await response.text(errors='ignore')
                title = self._extract_title(content)
                
                if "404" in title or "not found" in title.lower() or "page not found" in content.lower():
                    return False
                    
                return True
                
        except Exception as e:
            adv_logger.log_error(f"Error verifying URL {url}: {str(e)}")
            return False

    def _clear_success_file(self):
        try:
            target_url = self.scan_info.get('url', 'Unknown')
            
            os.makedirs(self.config.LOGS_DIR, exist_ok=True)
            
            success_file_path = os.path.join(self.config.LOGS_DIR, self.success_file)
            
            with open(success_file_path, 'w', encoding='utf-8') as f:
                f.write(f"--- New Scan Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"Target: {target_url}\n")
                f.write(f"Mode: {self.config.DETECTION_MODE}\n")
                f.write("-" * 50 + "\n\n")
                
            with open(self.success_file, 'w', encoding='utf-8') as f:
                f.write(f"--- New Scan Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"Target: {target_url}\n")
                f.write(f"Mode: {self.config.DETECTION_MODE}\n")
                f.write("-" * 50 + "\n\n")
                
        except Exception as e:
            adv_logger.log_error(f"Error clearing success file: {str(e)}")
    
    def _write_scan_summary(self):
        try:
            with open(self.success_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Scan Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"Duration: {self.scan_info.get('duration', 0):.2f} seconds\n")
                f.write(f"Total paths checked: {self.scan_info.get('total_count', 0)}\n")
                f.write(f"Found admin panels: {self.scan_info.get('found_count', 0)}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            adv_logger.log_error(f"Error writing scan summary: {str(e)}")

    async def cleanup(self):
        if self.session:
            try:
                await self.session.close()
                adv_logger.log_info("Closed HTTP session")
            except Exception as e:
                adv_logger.log_error(f"Error closing HTTP session: {str(e)}")
    
    async def close(self):
        await self.cleanup()
    
    def is_running(self) -> bool:
        return self.running
    
    def get_results(self) -> List[Dict]:
        return self.results
    
    def get_scan_info(self) -> Dict:
        scan_info_copy = self.scan_info.copy() if self.scan_info else {}
        return scan_info_copy
        
    def stop_scan(self):
        self.running = False
        adv_logger.log_warning("Scan stopped by user")
        console.print("[yellow]Scan stopped by user[/yellow]") 
