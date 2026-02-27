import subprocess
import time
import os
import json
import sys
import urllib.parse
import argparse
import logging
import shutil
import requests
import signal
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import random
import re
import socket
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import ssl
import concurrent.futures
from aiohttp import ClientSession, TCPConnector, ClientTimeout
from aiohttp.client_exceptions import (
    ClientConnectionError, ClientPayloadError, 
    ClientResponseError, ServerDisconnectedError,
    TooManyRedirects, ServerTimeoutError,
)
from scripts.logging import get_logger

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except (ImportError, AttributeError):
    import warnings
    warnings.filterwarnings('ignore', 'Unverified HTTPS request')

adv_logger = get_logger('logs')
logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).parent
ROOT_DIR = SCRIPTS_DIR.parent
CONFIG_DIR = ROOT_DIR / "config"
PATHS_DIR = ROOT_DIR / "paths"
RESULTS_DIR = ROOT_DIR / "results"
LOGS_DIR = ROOT_DIR / "logs"
GENERAL_PATHS_FILE = PATHS_DIR / "general_paths.json"
CHANGELOG_FILE = ROOT_DIR / "CHANGELOG.md"
CONFIG_FILE = CONFIG_DIR / "config.json"

for directory in [CONFIG_DIR, PATHS_DIR, RESULTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

ctrl_c_pressed = 0
last_ctrl_c_time = 0
ctrl_c_timeout = 2  
current_scan_results = {}
success_file = "success.txt"

def signal_handler(sig, frame):

    global ctrl_c_pressed, last_ctrl_c_time
    
    current_time = time.time()
    
    if ctrl_c_pressed > 0 and (current_time - last_ctrl_c_time) < ctrl_c_timeout:
        print("\n\n[!] Exiting application (Ctrl+C pressed twice).")
        save_results_to_success_file()
        sys.exit(0)
    
    ctrl_c_pressed += 1
    last_ctrl_c_time = current_time
    
    if ctrl_c_pressed == 1:
        print("\n\n[!] Scan interrupted by user. Displaying current results...")
        
        if current_scan_results:
            print("\nScan Summary (Interrupted)")
            print(f"Target URL: {current_scan_results.get('url', 'Unknown')}")
            print(f"Scan Modes: {', '.join(current_scan_results.get('modes', ['Unknown']))}")
            if 'results' in current_scan_results:
                for mode, result_data in current_scan_results['results'].items():
                    if isinstance(result_data, dict) and 'found' in result_data and 'total' in result_data:
                        print(f"Mode {mode}: Found {result_data['found']} panels out of {result_data['total']} paths checked")
                        
            save_results_to_success_file()
        else:
            print("\nNo results available yet.")
        
        print("\n[!] Press Ctrl+C again within 2 seconds to exit the application.")
        print("[!] Or press Enter to continue...")
        return

def save_results_to_success_file():
    if not current_scan_results:
        return
        
    try:
        with open(success_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Interrupted Scan Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(f"Target: {current_scan_results.get('url', 'Unknown')}\n")
            f.write(f"Modes: {', '.join(current_scan_results.get('modes', ['Unknown']))}\n")
            
            if 'results' in current_scan_results:
                for mode, result_data in current_scan_results['results'].items():
                    if isinstance(result_data, dict) and 'found' in result_data:
                        f.write(f"Mode {mode}: Found {result_data['found']} panels\n")
                        
                        if 'found_urls' in result_data:
                            f.write("\nFound Admin Panels:\n")
                            for url_data in result_data['found_urls']:
                                f.write(f"- {url_data.get('url', 'Unknown')}\n")
                                if 'title' in url_data:
                                    f.write(f"  Title: {url_data['title']}\n")
                                if 'confidence' in url_data:
                                    f.write(f"  Confidence: {url_data['confidence']:.2f}\n")
            
            f.write("-" * 50 + "\n")
    except Exception as e:
        adv_logger.log_error(f"Error saving results to {success_file}: {str(e)}")

signal.signal(signal.SIGINT, signal_handler)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            adv_logger.log_info(f"Loaded configuration from {CONFIG_FILE}")
            return config
        except Exception as e:
            adv_logger.log_error(f"Error loading config from {CONFIG_FILE}: {str(e)}")
    adv_logger.log_warning(f"Config file {CONFIG_FILE} not found or invalid, using default configuration")
    return {}

config_data = load_config()

def print_banner():
    version = config_data.get("VERSION", "1.0.0")
    tool_name = config_data.get("TOOL_NAME", "Find The Admin Panel")
    developer = config_data.get("DEVELOPER", "Anonymous")
    github = config_data.get("GITHUB", "https://github.com/")
    
    print(banner)

def print_section(title):
    print("\n" + "═" * 80)
    print(f" {title} ".center(80, "="))
    print("═" * 80 + "\n")

def parse_url(url):
    if not url:
        return None
        
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
        
    try:
        parsed = urllib.parse.urlparse(url)
        return url
    except:
        return None

def run_command(command, description, show_output=True, capture_output=False):

    global ctrl_c_pressed
    
    print_section(description)
    print(f"Command: {command}\n")
    
    start_time = time.time()
    result = None
    
    try:
        if show_output and not capture_output:
            result = subprocess.run(command, shell=True)
            if result.returncode != 0:
                print(f"\n[!] Command failed with exit code {result.returncode}")
                adv_logger.log_error(f"Command failed: {command}, exit code: {result.returncode}")
        elif capture_output:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            if show_output:
                print(result)
        else:
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("Command executed silently.")
            if result.returncode != 0:
                print(f"Command failed with exit code {result.returncode}")
                print(result.stderr)
                adv_logger.log_error(f"Silent command failed: {command}, exit code: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Command execution error: {e}")
        print(e.output)
        adv_logger.log_error(f"Command execution error: {e}")
    except Exception as e:
        print(f"\n[!] Unexpected error: {str(e)}")
        adv_logger.log_error(f"Unexpected error in run_command: {str(e)}")
    
    execution_time = time.time() - start_time
    print(f"\nCommand completed in {execution_time:.2f} seconds")
    print("\n" + "═" * 80)
    
    if ctrl_c_pressed > 0:
        print("\n[!] Command interrupted by user.")
        
    if capture_output:
        return result

def update_changelog(change_description, version="1.0.0"):
    try:
        change_date = datetime.now().strftime("%Y-%m-%d")
        
        if not CHANGELOG_FILE.exists():
            with open(CHANGELOG_FILE, 'w') as f:
                f.write("# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n")
        
        with open(CHANGELOG_FILE, 'r') as f:
            content = f.readlines()
            
        header_end = 3 
        new_change = f"\n## [{version}] - {change_date}\n\n- {change_description}\n"
        content.insert(header_end, new_change)
        
        with open(CHANGELOG_FILE, 'w') as f:
            f.writelines(content)
            
        adv_logger.log_info(f"Changelog updated with: {change_description}")
        return True
    except Exception as e:
        adv_logger.log_error(f"Failed to update changelog: {str(e)}")
        return False

def save_temp_paths_file(paths, file_path):
    try:
        with open(file_path, 'w') as f:
            json.dump(paths, f, indent=4)
    except Exception as e:
        adv_logger.log_error(f"Error saving temp paths file: {str(e)}")

def fetch_site_info(url, timeout=10):
    config = load_config()
    user_agents = config.get('USER_AGENTS', [])
    
    info = {
        'url': url,
        'status': None,
        'server': 'Unknown',
        'technologies': [],
        'headers': {},
        'title': 'Unknown',
        'language': 'en',  
        'response_time': 0,
        'content_length': 0
    }
    
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
    
    if not user_agents:
        adv_logger.log_warning("No user agents found in config.json")
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    else:
        user_agent = random.choice(user_agents)
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5,ar;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        start_time = time.time()
        response = requests.get(
            url, 
            headers=headers, 
            timeout=timeout,
            verify=False,
            allow_redirects=True
        )
        response_time = time.time() - start_time
        
        info['status'] = response.status_code
        info['headers'] = dict(response.headers)
        info['response_time'] = response_time
        info['content_length'] = len(response.content)
        
        if 'Server' in response.headers:
            info['server'] = response.headers['Server']
            
        tech_signatures = {
            'WordPress': ['wp-content', 'wp-includes', 'wp-admin'],
            'Joomla': ['joomla', 'com_content', 'com_users'],
            'Drupal': ['drupal', 'sites/all', 'sites/default'],
            'Laravel': ['laravel', 'csrf-token'],
            'Django': ['csrfmiddlewaretoken', 'django'],
            'Angular': ['ng-app', 'ng-controller', 'angular'],
            'React': ['react', 'react-dom', 'reactjs'],
            'Vue.js': ['vue', 'vue.js', 'vuejs'],
            'Bootstrap': ['bootstrap.css', 'bootstrap.min.css', 'bootstrap.js'],
            'jQuery': ['jquery.js', 'jquery.min.js'],
            'PHP': ['php', '.php'],
            'ASP.NET': ['asp.net', '.aspx', 'viewstate'],
            'Node.js': ['node_modules'],
            'Express': ['express', 'powered by express']
        }
        
        for tech, signatures in tech_signatures.items():
            if any(sig.lower() in response.text.lower() for sig in signatures):
                info['technologies'].append(tech)
                
        title_match = re.search('<title>(.*?)</title>', response.text, re.IGNORECASE)
        if title_match:
            info['title'] = title_match.group(1).strip()
            
        return info
        
    except requests.exceptions.Timeout:
        adv_logger.log_warning(f"Request timeout for {url}")
    except requests.exceptions.ConnectionError:
        adv_logger.log_warning(f"Connection error for {url}")
    except requests.exceptions.RequestException as e:
        adv_logger.log_error(f"Request error for {url}: {str(e)}")
    except Exception as e:
        adv_logger.log_error(f"Error fetching site info: {str(e)}")
        
    return info

def detect_site_language(url):
    print_section("Detecting Site Language")
    print(f"Analyzing URL: {url}")
    
    site_info = fetch_site_info(url)
    
    print(f"Status Code: {site_info['status']}")
    print(f"Server: {site_info['server']}")
    print(f"Title: {site_info['title']}")
    print(f"Technologies: {', '.join(site_info['technologies'])}")
    print(f"Response Time: {site_info['response_time']:.2f}s")
    print(f"Content Length: {site_info['content_length']} bytes")

    print(f"Using general paths from: {GENERAL_PATHS_FILE}")
    return str(GENERAL_PATHS_FILE), "en", ["en"], False
    
def check_internet_connection():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def clean_url(url):
    if not url or len(url) < 3:
        raise ValueError("URL is too short or empty")
    
    url = url.strip()
    
    url = re.sub(r'^([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}(:[0-9]+)?.*$', 
                lambda m: f"https://{m.group(0)}" if not m.group(0).startswith(('http://', 'https://')) else m.group(0), 
                url)
    
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL format")
    
    return url

def create_timestamp_dir(base_dir, prefix="scan"):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dir_path = os.path.join(base_dir, f"{prefix}_{timestamp}")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def parse_args():
    parser = argparse.ArgumentParser(
        description="Advanced Admin Panel Finder - Smart Scan Helper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-u", "--url", help="Target URL to scan")
    parser.add_argument("--mode", choices=["all", "aggressive", "stealth", "simple"], default="all",
                      help="Scan mode (default: all)")
    parser.add_argument("--concurrency", type=int, default=50,
                      help="Number of concurrent requests")
    parser.add_argument("--timeout", type=int, default=30,
                      help="Request timeout in seconds")
    parser.add_argument("--no-verify", action="store_true",
                      help="Disable SSL verification")
    parser.add_argument("--quiet", action="store_true",
                      help="Suppress detailed output")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    return parser.parse_args()

def count_paths(file_path):
    try:
        with open(file_path, 'r') as f:
            paths = json.load(f)
        return len(paths)
    except Exception as e:
        adv_logger.log_error(f"Error counting paths in {file_path}: {str(e)}")
        return 0

def main():
    global ctrl_c_pressed, last_ctrl_c_time, current_scan_results
    
    ctrl_c_pressed = 0
    last_ctrl_c_time = 0
    
    args = parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        adv_logger.log_info("Debug logging enabled")
    
    print_banner()
    
    if not check_internet_connection():
        print("[!] Warning: No internet connection detected. The scanner may not work properly.")
        if input("Continue anyway? (y/n): ").lower() != 'y':
            sys.exit(0)
    
    try:
        url = args.url
        if not url:
            url = input("Enter the target URL (e.g., https://example.com): ").strip()
            if not url:
                print("[!] Error: URL cannot be empty")
                return
        
        try:
            url = clean_url(url)
            print(f"\n[+] Target set to: {url}")
        except ValueError as e:
            print(f"[!] Error: {str(e)}")
            return
        
        output_dir = create_timestamp_dir(str(RESULTS_DIR))
        print(f"[+] Results will be saved to: {output_dir}")
        
        if not os.path.exists(GENERAL_PATHS_FILE):
            print(f"[!] Warning: General paths file {GENERAL_PATHS_FILE} not found!")
            sys.exit(1)
        else:
            print(f"[+] Found general paths file with {count_paths(GENERAL_PATHS_FILE)} paths")
        
        paths_file = str(GENERAL_PATHS_FILE)
        primary_lang = "en"
        all_langs = ["en"]
        
        url_safe = urllib.parse.quote_plus(url)
        base_name = f"{url_safe}_{primary_lang}"
        
        scan_modes = []
        if args.mode == "all":
            scan_modes = ["aggressive", "stealth", "simple"]
        else:
            scan_modes = [args.mode]
        
        print(f"[+] Running scans with modes: {', '.join(scan_modes)}")
        print(f"[+] Using paths from: {paths_file}")
        
        current_scan_results = {
            'url': url,
            'modes': scan_modes,
            'results': {}
        }
        
        scan_results = {}
        
        for mode in scan_modes:
            if ctrl_c_pressed > 0:
                print(f"\n[!] Scan for mode {mode} skipped due to user interruption.")
                continue
                
            command = (
                f"python {os.path.join(ROOT_DIR, 'finder.py')} "
                f"-u {url} "
                f"--mode {mode} "
                f"-p {paths_file} "
                f"--concurrency {args.concurrency} "
                f"-j -h "  
                f"--timeout {args.timeout} "
            )
            
            if args.no_verify:
                command += "--no-verify "
                
            if args.quiet:
                command += "--quiet "
                
            if args.debug:
                command += "--debug "
                
            command += f"--output {os.path.join(output_dir, f'{base_name}_{mode}')}"
            
            result = run_command(
                command,
                f"Running {mode} scan for {url} using general paths",
                show_output=not args.quiet,
                capture_output=args.quiet
            )
            
            scan_results[mode] = result
            
            result_file = os.path.join(output_dir, f'{base_name}_{mode}.json')
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        results_data = json.load(f)
                        found_count = sum(1 for item in results_data.get('results', []) if item.get('found', False))
                        total_count = len(results_data.get('results', []))
                        
                        current_scan_results['results'][mode] = {
                            'found': found_count,
                            'total': total_count,
                            'file': result_file
                        }
                except Exception as e:
                    adv_logger.log_error(f"Error reading scan results for {mode}: {str(e)}")
        
        print_section("Scan Summary")
        print(f"Target URL: {url}")
        print(f"Used path source: {paths_file}")
        print(f"Modes used: {', '.join(scan_modes)}")
        print(f"Results saved to: {output_dir}")
        
        for mode in scan_modes:
            result_file = os.path.join(output_dir, f'{base_name}_{mode}.json')
            html_report = os.path.join(output_dir, f'{base_name}_{mode}.html')
            
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                        
                    found_count = sum(1 for item in results.get('results', []) if item.get('found', False))
                    total_count = len(results.get('results', []))
                    
                    print(f"\n[+] {mode.capitalize()} scan results:")
                    print(f"    - Found: {found_count} potential admin panels")
                    print(f"    - Total URLs scanned: {total_count}")
                    if found_count > 0:
                        print(f"    - HTML report: {html_report}")
                except Exception as e:
                    print(f"[!] Error reading results from {result_file}: {str(e)}")
        
        scan_info = f"Scan completed for {url}\n- Scan modes: {', '.join(scan_modes)}\n- Results saved to: {output_dir}"
        update_changelog(scan_info)
        
        print("\n" + "═" * 80)
        print("[+] All scans completed. Check the results directory for findings.")
        print("[+] Remember to review the HTML reports for detailed information.")
        print("═" * 80)
    
    except KeyboardInterrupt:
        print("\n\n[!] Scan interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
        adv_logger.log_error("An error occurred during execution", exc_info=True)
    finally:
        if ctrl_c_pressed == 0:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Scan interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
        adv_logger.log_error("An error occurred during execution", exc_info=True)
        sys.exit(1)

class ScanOptimizer:
    
    def __init__(self, config):
        self.config = config
        self.seen_paths = set()
        self.common_responses = {}
        self.failed_paths = set()
        self.throttled_hosts = {}
        self.host_capabilities = {}
    
    def reset(self):
        self.seen_paths = set()
        self.common_responses = {}
        self.failed_paths = set()
        self.throttled_hosts = {}
        self.host_capabilities = {}
    
    def should_throttle(self, host: str) -> bool:
        if host not in self.throttled_hosts:
            return False
            
        throttle_info = self.throttled_hosts[host]
        current_time = time.time()
        
        if current_time - throttle_info['start_time'] > throttle_info['duration']:
            del self.throttled_hosts[host]
            return False
            
        return True
    
    def add_throttle(self, host: str, failure_count: int = 1):
        current_time = time.time()
        
        if host in self.throttled_hosts:
            throttle_info = self.throttled_hosts[host]
            throttle_info['count'] += failure_count
            
            throttle_info['duration'] = min(120, 5 * (2 ** min(5, throttle_info['count'])))
            throttle_info['start_time'] = current_time
        else:
            self.throttled_hosts[host] = {
                'count': failure_count,
                'duration': 5,  
                'start_time': current_time
            }
    
    def optimize_paths(self, paths: List[str]) -> List[str]:
        filtered_paths = [p for p in paths if p not in self.failed_paths]
        
        path_categories = {}
        
        patterns = {
            'admin': re.compile(r'admin|administrator|adm|manage|manager|mgr', re.I),
            'login': re.compile(r'login|signin|sign-in|auth|authentication', re.I),
            'dashboard': re.compile(r'dashboard|panel|control|console', re.I),
            'api': re.compile(r'api|rest|graphql|endpoint', re.I),
            'user': re.compile(r'user|account|profile|member', re.I),
            'backup': re.compile(r'backup|bak|old|temp|tmp|copy', re.I),
            'generic': re.compile(r'.*')
        }
        
        for path in filtered_paths:
            categorized = False
            for category, pattern in patterns.items():
                if pattern.search(path):
                    if category not in path_categories:
                        path_categories[category] = []
                    path_categories[category].append(path)
                    categorized = True
                    break
            
            if not categorized:
                if 'other' not in path_categories:
                    path_categories['other'] = []
                path_categories['other'].append(path)
        
        category_order = ['admin', 'login', 'dashboard', 'user', 'api', 'backup', 'generic', 'other']
        
        optimized_paths = []
        for category in category_order:
            if category in path_categories:
                optimized_paths.extend(path_categories[category])
        
        if len(filtered_paths) < len(paths):
            sample_size = min(50, len(paths) - len(filtered_paths))
            remainder = list(self.failed_paths)[:sample_size]
            optimized_paths.extend(remainder)
        
        return optimized_paths
    
    def should_skip_path(self, path: str) -> bool:
        if path in self.seen_paths:
            return True
        
        if path in self.failed_paths:
            return True
        
        return False
    
    def record_path_result(self, path: str, status_code: int, success: bool = True):
        self.seen_paths.add(path)
        
        if not success and path not in self.failed_paths:
            self.failed_paths.add(path)
        
        if status_code not in self.common_responses:
            self.common_responses[status_code] = 0
        self.common_responses[status_code] += 1
    
    def record_host_capabilities(self, host: str, supports_keep_alive: bool, 
                                supports_http2: bool, avg_response_time: float):
        self.host_capabilities[host] = {
            'supports_keep_alive': supports_keep_alive,
            'supports_http2': supports_http2,
            'avg_response_time': avg_response_time
        }
    
    def get_optimal_batch_size(self, host: str) -> int:
        if host in self.throttled_hosts:
            return 5
        
        if host in self.host_capabilities:
            capabilities = self.host_capabilities[host]
            
            if capabilities['supports_keep_alive'] and capabilities['avg_response_time'] < 0.5:
                if capabilities['supports_http2']:
                    return self.config.MAX_CONCURRENT_REQUESTS
                else:
                    return min(30, self.config.MAX_CONCURRENT_REQUESTS)
            
            if capabilities['avg_response_time'] > 1.0:
                return 10
        
        return min(20, self.config.MAX_CONCURRENT_REQUESTS)


class ResponseAnalyzer:

    def __init__(self, config):
        self.config = config
        self.login_form_re = re.compile(r'<form[^>]*>.*?(?:<input[^>]*password[^>]*>|<input[^>]*username[^>]*>).*?</form>', re.DOTALL | re.IGNORECASE)
        self.admin_indicators_re = re.compile(r'admin|administrator|login|dashboard|control\s*panel|manage|console', re.IGNORECASE)
        self.sensitive_terms_re = re.compile(r'password|username|user|token|auth|key|credential', re.IGNORECASE)
    
    def analyze_response(self, url: str, status_code: int, html_content: str, 
                         response_headers: Dict[str, str], response_time: float) -> Dict:
        result = {
            "url": url,
            "status_code": status_code,
            "title": "",
            "confidence": 0.0,
            "found": False,
            "has_login_form": False,
            "technologies": [],
            "headers": response_headers,
            "server": response_headers.get("Server", "Unknown"),
            "forms": [],
            "inputs": [],
            "content_length": len(html_content) if html_content else 0,
            "response_time": response_time
        }
        
        if status_code >= 400 and status_code != 401 and status_code != 403:
            return result
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            title_tag = soup.find('title')
            if title_tag:
                result["title"] = title_tag.text.strip()
            
            login_forms = self.login_form_re.findall(html_content)
            result["has_login_form"] = len(login_forms) > 0
            
            forms = soup.find_all('form')
            result["forms"] = [self._extract_form_info(form) for form in forms]
            
            inputs = soup.find_all('input')
            result["inputs"] = [self._extract_input_info(input_field) for input_field in inputs]
            
            result["technologies"] = self._detect_technologies(soup, html_content, response_headers)
            
            result["confidence"] = self._calculate_confidence(result, soup, html_content)
            
            result["found"] = result["confidence"] >= 0.5
            
            return result
            
        except Exception as e:
            adv_logger.log_error(f"Error analyzing response for {url}: {str(e)}")
            return result
    
    def _extract_form_info(self, form_tag) -> Dict:
        try:
            action = form_tag.get('action', '')
            method = form_tag.get('method', 'get').upper()
            
            inputs = form_tag.find_all('input')
            input_fields = []
            
            for input_tag in inputs:
                input_type = input_tag.get('type', 'text')
                input_name = input_tag.get('name', '')
                input_id = input_tag.get('id', '')
                
                input_fields.append({
                    'type': input_type,
                    'name': input_name,
                    'id': input_id
                })
            
            return {
                'action': action,
                'method': method,
                'inputs': input_fields
            }
        except Exception:
            return {'action': '', 'method': 'GET', 'inputs': []}
    
    def _extract_input_info(self, input_tag) -> Dict:
        try:
            input_type = input_tag.get('type', 'text')
            input_name = input_tag.get('name', '')
            input_id = input_tag.get('id', '')
            
            return {
                'type': input_type,
                'name': input_name,
                'id': input_id
            }
        except Exception:
            return {'type': 'text', 'name': '', 'id': ''}
    
    def _detect_technologies(self, soup, html_content: str, headers: Dict[str, str]) -> List[str]:
        technologies = []
        
        if 'Server' in headers:
            server = headers['Server']
            if 'nginx' in server.lower():
                technologies.append('Nginx')
            elif 'apache' in server.lower():
                technologies.append('Apache')
            elif 'microsoft-iis' in server.lower():
                technologies.append('IIS')
            elif 'cloudflare' in server.lower():
                technologies.append('Cloudflare')
        
        if re.search(r'jquery', html_content, re.I):
            technologies.append('jQuery')
        
        if re.search(r'react', html_content, re.I) or soup.find('div', {'id': 'root'}):
            technologies.append('React')
        
        if re.search(r'angular', html_content, re.I) or soup.find('ng-app'):
            technologies.append('Angular')
        
        if re.search(r'bootstrap', html_content, re.I) or soup.find('link', {'href': re.compile(r'bootstrap')}):
            technologies.append('Bootstrap')
        
        if re.search(r'wp-content|wordpress', html_content, re.I) or soup.find('meta', {'name': 'generator', 'content': re.compile(r'WordPress')}):
            technologies.append('WordPress')
        
        if re.search(r'joomla', html_content, re.I) or soup.find('meta', {'name': 'generator', 'content': re.compile(r'Joomla')}):
            technologies.append('Joomla')
        
        if re.search(r'drupal', html_content, re.I) or soup.find('meta', {'name': 'generator', 'content': re.compile(r'Drupal')}):
            technologies.append('Drupal')
        
        if 'X-Powered-By' in headers and 'php' in headers['X-Powered-By'].lower():
            technologies.append('PHP')
        
        if 'X-AspNet-Version' in headers or 'X-Powered-By' in headers and 'asp.net' in headers['X-Powered-By'].lower():
            technologies.append('ASP.NET')
        
        return list(set(technologies))  
    
    def _calculate_confidence(self, result: Dict, soup, html_content: str) -> float:
        confidence = 0.0
        
        if self.admin_indicators_re.search(result["url"]):
            confidence += 0.2
        
        if result["has_login_form"]:
            confidence += 0.3
        
        if self.admin_indicators_re.search(result["title"]):
            confidence += 0.2
        
        if result["status_code"] in [401, 403]:
            confidence += 0.15
        
        admin_tech = ["WordPress Admin", "Joomla", "Drupal", "phpMyAdmin", "cPanel", "WebMin", "AdminLTE"]
        for tech in result["technologies"]:
            if tech in admin_tech:
                confidence += 0.1
                break
        
        if self.admin_indicators_re.search(html_content):
            confidence += 0.1
        
        if self.sensitive_terms_re.search(html_content):
            confidence += 0.05
        
        url_path = urlparse(result["url"]).path.strip('/')
        if (result["has_login_form"] and len(url_path.split('/')) <= 2 and 
            ('login' in url_path.lower() or 'admin' in url_path.lower())):
            confidence += 0.1
        
        return min(1.0, confidence)


async def create_optimized_session(config, optimizer: ScanOptimizer) -> ClientSession:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    timeout = ClientTimeout(total=config.TIMEOUT, connect=config.TIMEOUT/2)
    
    connector = TCPConnector(
        ssl=ssl_context,
        limit=config.MAX_CONCURRENT_REQUESTS,
        ttl_dns_cache=300,  
        force_close=False,  
        enable_cleanup_closed=True,
        verify_ssl=False
    )
    
    session = ClientSession(
        connector=connector,
        timeout=timeout,
        trust_env=True,
        auto_decompress=True
    )
    
    return session


async def scan_paths_concurrently(
    target_url: str, 
    paths: List[str], 
    session: ClientSession, 
    config, 
    optimizer: ScanOptimizer, 
    analyzer: ResponseAnalyzer,
    progress_callback=None
) -> List[Dict]:
    host = urlparse(target_url).netloc
    
    optimized_paths = optimizer.optimize_paths(paths)
    
    batch_size = optimizer.get_optimal_batch_size(host)
    
    results = []
    total_paths = len(optimized_paths)
    completed = 0
    
    for i in range(0, total_paths, batch_size):
        if optimizer.should_throttle(host):
            await asyncio.sleep(5)
        
        batch_paths = optimized_paths[i:i+batch_size]
        batch_paths = [p for p in batch_paths if not optimizer.should_skip_path(p)]
        
        if not batch_paths:
            completed += len(optimized_paths[i:i+batch_size])
            if progress_callback:
                progress_callback(completed, total_paths)
            continue
        
        tasks = []
        for path in batch_paths:
            url = urljoin(target_url, path)
            tasks.append(_scan_single_path(url, path, session, config, optimizer, analyzer))
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                adv_logger.log_error(f"Error during scan: {str(result)}")
                continue
            
            if result:
                results.append(result)
        
        completed += len(batch_paths)
        if progress_callback:
            progress_callback(completed, total_paths)
        
        await asyncio.sleep(0.2)
    
    return results


async def _scan_single_path(url: str, path: str, session: ClientSession, config, 
                           optimizer: ScanOptimizer, analyzer: ResponseAnalyzer) -> Optional[Dict]:
    host = urlparse(url).netloc
    
    headers = {"User-Agent": random.choice(config.USER_AGENTS)}
    
    start_time = time.time()
    try:
        async with session.get(url, headers=headers, allow_redirects=True, timeout=config.TIMEOUT) as response:
            response_time = time.time() - start_time
            
            html_content = await response.text(errors='ignore')
            response_headers = dict(response.headers)
            
            optimizer.record_path_result(path, response.status, True)
            
            supports_keep_alive = 'Connection' in response_headers and 'keep-alive' in response_headers['Connection'].lower()
            supports_http2 = response.version is not None and response.version >= (2, 0)
            optimizer.record_host_capabilities(host, supports_keep_alive, supports_http2, response_time)
            
            result = analyzer.analyze_response(url, response.status, html_content, 
                                            response_headers, response_time)
            
            return result
            
    except (ClientConnectionError, ClientPayloadError, ClientResponseError,
            ServerDisconnectedError, TooManyRedirects, ServerTimeoutError) as e:
        optimizer.record_path_result(path, 0, False)
        
        optimizer.add_throttle(host)
        
        adv_logger.log_error(f"Connection error for {url}: {str(e)}")
        return None
    except asyncio.TimeoutError:
        optimizer.record_path_result(path, 0, False)
        
        optimizer.add_throttle(host)
        
        adv_logger.log_error(f"Timeout for {url}")
        return None
    except Exception as e:
        optimizer.record_path_result(path, 0, False)
        
        adv_logger.log_error(f"Error scanning {url}: {str(e)}")
        return None 

def auto_update_wordlist(wordlist_path, update_source=None):
    try:
        adv_logger.log_info(f"Attempting to auto-update wordlist: {wordlist_path}")
        
        if not os.path.exists(wordlist_path):
            parent_dir = os.path.dirname(wordlist_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            with open(wordlist_path, 'w') as f:
                json.dump([], f)
            adv_logger.log_info(f"Created new empty wordlist at {wordlist_path}")
        
        with open(wordlist_path, 'r') as f:
            try:
                existing_paths = json.load(f)
                if not isinstance(existing_paths, list):
                    existing_paths = []
                    adv_logger.log_warning(f"Wordlist {wordlist_path} has invalid format, resetting to empty list")
            except json.JSONDecodeError:
                existing_paths = []
                adv_logger.log_warning(f"Wordlist {wordlist_path} has invalid JSON, resetting to empty list")
        
        original_count = len(existing_paths)
        adv_logger.log_info(f"Current wordlist has {original_count} entries")
        
        new_paths = []
        if update_source and update_source.startswith(('http://', 'https://')):
            try:
                headers = {
                    'User-Agent': 'FindTheAdminPanel/6.1 WordlistUpdater'
                }
                response = requests.get(update_source, timeout=10, headers=headers, verify=False)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'json' in content_type:
                        fetched_data = response.json()
                        if isinstance(fetched_data, list):
                            new_paths = fetched_data
                        elif isinstance(fetched_data, dict) and 'paths' in fetched_data:
                            new_paths = fetched_data.get('paths', [])
                    else:
                        new_paths = [line.strip() for line in response.text.split('\n') if line.strip()]
                        
                    adv_logger.log_info(f"Fetched {len(new_paths)} paths from {update_source}")
                else:
                    adv_logger.log_warning(f"Failed to fetch paths from {update_source}, status code: {response.status_code}")
            except Exception as e:
                adv_logger.log_error(f"Error fetching paths from {update_source}: {str(e)}")
        
        elif update_source and os.path.isfile(update_source):
            try:
                with open(update_source, 'r') as f:
                    if update_source.endswith('.json'):
                        try:
                            fetched_data = json.load(f)
                            if isinstance(fetched_data, list):
                                new_paths = fetched_data
                            elif isinstance(fetched_data, dict) and 'paths' in fetched_data:
                                new_paths = fetched_data.get('paths', [])
                        except json.JSONDecodeError:
                            f.seek(0)
                            new_paths = [line.strip() for line in f if line.strip()]
                    else:
                        new_paths = [line.strip() for line in f if line.strip()]
                        
                adv_logger.log_info(f"Read {len(new_paths)} paths from file {update_source}")
            except Exception as e:
                adv_logger.log_error(f"Error reading paths from file {update_source}: {str(e)}")
        
        else:
            admin_patterns = [
                "admin", "administrator", "admincp", "admins", "admin/login", "admin/dashboard", 
                "login", "wp-admin", "wp-login.php", "panel", "cpanel", "control", "dashboard",
                "adm", "moderator", "webadmin", "adminarea", "bb-admin", "adminLogin", "admin_area",
                "backend", "cmsadmin", "administration", "cms", "manage", "portal", "supervisor",
                "manager", "mgr", "user/admin", "user/login", "siteadmin", "console", "admin1",
                "adminpanel", "robots.txt", "sitemap.xml", ".env", ".git/config", ".htaccess",
                "server-status", "phpmyadmin", "myadmin", "pma", "system", "admincontrol"
            ]
            
            variants = []
            for pattern in admin_patterns:
                variants.append(pattern)
                variants.append(f"{pattern}/")
                variants.append(f"{pattern}.php")
                variants.append(f"{pattern}.html")
                variants.append(f"{pattern}.asp")
                variants.append(f"{pattern}.aspx")
                variants.append(f"{pattern}.jsp")
                
            new_paths = list(set(variants))
            adv_logger.log_info(f"Generated {len(new_paths)} admin path patterns for enrichment")
            
        combined_paths = list(set(existing_paths + new_paths))
        
        combined_paths.sort()
        
        backup_path = f"{wordlist_path}.bak"
        try:
            shutil.copy2(wordlist_path, backup_path)
            adv_logger.log_info(f"Created backup at {backup_path}")
        except Exception as e:
            adv_logger.log_warning(f"Failed to create backup: {str(e)}")
        
        with open(wordlist_path, 'w') as f:
            json.dump(combined_paths, f, indent=2)
        
        final_count = len(combined_paths)
        added_count = final_count - original_count
        stats = {
            "original_count": original_count,
            "final_count": final_count,
            "added_count": added_count,
            "percent_increase": round((added_count / max(original_count, 1)) * 100, 2)
        }
        
        message = f"Wordlist updated successfully. Added {added_count} new paths ({stats['percent_increase']}% increase)"
        adv_logger.log_info(message)
        
        return True, message, stats
    
    except Exception as e:
        error_msg = f"Error updating wordlist: {str(e)}"
        adv_logger.log_error(error_msg)
        return False, error_msg, {} 
