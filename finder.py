
import os
import sys
import asyncio
import argparse
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.config import Config
from scripts.ui import TerminalDisplay
from scripts.scanner import Scanner
from scripts.exporter import ResultExporter
from scripts.menu import start_menu
from scripts.utils import setup_signal_handler, validate_url, count_lines_in_file
from scripts.logger import get_logger
from scripts.wordlist_updater import auto_update_wordlist
from scripts.input_validator import validate_url as secure_validate_url, validate_paths_list
from scripts.rate_limiter import get_rate_limiter
from scripts.path_fuzzer import get_fuzzer, fuzz_paths

adv_logger = get_logger('logs')


async def scan_target(config, target_url, wordlist_path=None, export_format="", interactive=False):
    display = TerminalDisplay()
    
    if not wordlist_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        wordlist_path = os.path.join(base_dir, config.DEFAULT_WORDLIST)
    
    is_valid, result = secure_validate_url(target_url)
    if not is_valid:
        adv_logger.log_error(f"Invalid URL: {result}")
        if interactive:
            display.show_error(f"Invalid URL: {result}")
            return [], {}
        else:
            print(f"Error: Invalid URL: {result}")
            sys.exit(1)
    target_url = result
    
    if not os.path.exists(wordlist_path):
        adv_logger.log_error(f"Wordlist file not found: {wordlist_path}")
        if interactive:
            display.show_error(f"Wordlist file not found: {wordlist_path}")
            return [], {}
        else:
            print(f"Error: Wordlist file not found: {wordlist_path}")
            sys.exit(1)
    
    scanner = await Scanner.create(config)
    
    setup_signal_handler(scanner)
    
    try:
        paths = []
        if wordlist_path.endswith('.json'):
            try:
                with open(wordlist_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        paths = data
                    elif isinstance(data, dict) and 'paths' in data:
                        paths = data['paths']
                    else:
                        adv_logger.log_error(f"Invalid JSON format in wordlist: {wordlist_path}")
                        paths = []
            except Exception as e:
                adv_logger.log_error(f"Error reading JSON wordlist: {str(e)}")
                if interactive:
                    display.show_error(f"Error reading JSON wordlist: {str(e)}")
                    return [], {}
                else:
                    print(f"Error: {str(e)}")
                    sys.exit(1)
        else:
            try:
                with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                    paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except Exception as e:
                adv_logger.log_error(f"Error reading wordlist file: {str(e)}")
                if interactive:
                    display.show_error(f"Error reading wordlist file: {str(e)}")
                    return [], {}
                else:
                    print(f"Error: {str(e)}")
                    sys.exit(1)
        
        paths = [p for p in paths if p and isinstance(p, str)]
        paths = validate_paths_list(paths)
        
        if config.USE_PATH_FUZZING:
            fuzzer = get_fuzzer(config.FUZZING_DEPTH)
            original_count = len(paths)
            paths = fuzz_paths(paths, config.FUZZING_DEPTH)
            adv_logger.log_info(f"Path fuzzing: expanded {original_count} paths to {len(paths)} paths")
        
        mode_config = config.get_current_mode_config()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if config.DETECTION_MODE == "simple" and len(paths) > 1000:
            original_count = len(paths)
            paths = paths[:1000]
            adv_logger.log_info(f"Simple mode: Limited paths from {original_count} to {len(paths)}")
        elif config.DETECTION_MODE == "stealth" and len(paths) > 500:
            original_count = len(paths)
            admin_keywords = ['admin', 'administrator', 'dashboard', 'panel', 'control', 'login', 'cp']
            prioritized_paths = [p for p in paths if any(keyword in p.lower() for keyword in admin_keywords)]
            
            random_paths = list(set(paths) - set(prioritized_paths))
            import random
            if random_paths:
                random.shuffle(random_paths)
                selected_random = random_paths[:200]
            else:
                selected_random = []
                
            paths = prioritized_paths[:300] + selected_random
            adv_logger.log_info(f"Stealth mode: Selected {len(paths)} optimized paths from {original_count}")
        
        scan_mode = "custom" if wordlist_path != os.path.join(base_dir, config.DEFAULT_WORDLIST) else "default"
        adv_logger.log_scan_start(target_url, scan_mode, len(paths))
        
        if interactive:
            display.clear_screen()
            display.show_banner(config)
            display.show_target_info(target_url, scan_mode, wordlist_path)
        else:
            print(f"\n{'='*60}")
            print(f"Find The Admin Panel v{config.VERSION}")
            print(f"{'='*60}")
            print(f"Target: {target_url}")
            print(f"Wordlist: {wordlist_path} ({len(paths)} paths)")
            print(f"Mode: {config.DETECTION_MODE} - {mode_config.get('DESCRIPTION', '')}")
            if config.USE_PATH_FUZZING:
                print(f"Path Fuzzing: Enabled (depth {config.FUZZING_DEPTH})")
            if config.USE_RATE_LIMITING:
                print(f"Rate Limiting: {config.RATE_LIMIT} req/s (burst: {config.RATE_LIMIT_BURST})")
            if config.USE_PROXIES:
                print(f"Proxy: Enabled")
            print(f"{'='*60}\n")
        
        start_time = datetime.now()
        results = await scanner.scan(target_url, paths)
        scan_time = (datetime.now() - start_time).total_seconds()
        
        scan_info = scanner.get_scan_info()
        scan_info["scan_time"] = scan_time
        scan_info["target_url"] = target_url
        scan_info["scan_mode"] = scan_mode
        scan_info["detection_mode"] = config.DETECTION_MODE
        scan_info["total_paths"] = len(paths)
        scan_info["fuzzing_enabled"] = config.USE_PATH_FUZZING
        scan_info["rate_limiting_enabled"] = config.USE_RATE_LIMITING
        
        adv_logger.log_scan_complete(
            target_url, 
            len(paths), 
            sum(1 for r in results if r.get("found", False)), 
            scan_time
        )
        
        if interactive:
            display.show_scan_completion(results, scan_time, len(paths))
            display.show_results(results)
            display.show_summary(len(paths), sum(1 for r in results if r.get("found", False)), scan_time)
        else:
            found_count = sum(1 for r in results if r.get("found", False))
            print(f"\n{'='*60}")
            print(f"Scan completed in {scan_time:.2f} seconds")
            print(f"Checked {len(paths)} paths")
            print(f"Found {found_count} potential admin panels")
            print(f"{'='*60}\n")
            
            if found_count > 0:
                print("Potential admin panels found:\n")
                for r in results:
                    if r.get("found", False):
                        print(f"  ✓ {r.get('url')}")
                        print(f"    Confidence: {r.get('confidence', 0):.2f} | Status: {r.get('status_code', 0)}")
                        if r.get('title'):
                            print(f"    Title: {r.get('title', 'N/A')}")
                        if r.get('technologies'):
                            print(f"    Tech: {', '.join(r.get('technologies', [])[:5])}")
                        print()
        
        if config.SAVE_RESULTS:
            exporter = ResultExporter(config)
            if interactive:
                display.show_progress("Exporting results...")
            else:
                print("Exporting results...")
            
            export_format = export_format or config.EXPORT_FORMATS[0] or "txt"
            export_status = exporter.export_results(results, scan_info, export_format)
            
            if interactive:
                display.show_success("Results exported successfully")
            else:
                print(f"Results exported to {config.RESULTS_DIR}/")
        
        return results, scan_info
        
    except Exception as e:
        adv_logger.log_error(f"Error during scan: {str(e)}")
        if interactive:
            display.show_error(f"Error during scan: {str(e)}")
        else:
            print(f"Error: {str(e)}")
        return [], {}
    finally:
        await scanner.close()


async def update_wordlists(config, source_url=None, interactive=False):
    display = TerminalDisplay()
    
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_wordlist_path = os.path.join(base_dir, config.DEFAULT_WORDLIST)
        
        if interactive:
            display.clear_screen()
            display.show_banner(config)
            display.show_progress(f"Updating wordlists...")
        else:
            print(f"Updating wordlists...")
            
        success, message, stats = auto_update_wordlist(default_wordlist_path, source_url)
        
        if success:
            if interactive:
                display.show_success(message)
                display.show_info(f"Original paths: {stats['original_count']}")
                display.show_info(f"New paths: {stats['final_count']}")
                display.show_info(f"Added: {stats['added_count']} (+{stats['percent_increase']}%)")
            else:
                print(f"Success: {message}")
                print(f"Original paths: {stats['original_count']}")
                print(f"New paths: {stats['final_count']}")
                print(f"Added: {stats['added_count']} (+{stats['percent_increase']}%)")
            return True
        else:
            if interactive:
                display.show_error(message)
            else:
                print(f"Error: {message}")
            return False
    
    except Exception as e:
        error_msg = f"Error updating wordlists: {str(e)}"
        adv_logger.log_error(error_msg)
        
        if interactive:
            display.show_error(error_msg)
        else:
            print(f"Error: {error_msg}")
        
        return False


async def main():
    try:
        config = Config()
        
        parser = argparse.ArgumentParser(
            description="Find The Admin Panel v7.0 - A powerful tool for identifying admin panels",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        
        parser.add_argument("-u", "--url", help="Target URL to scan")
        parser.add_argument("-w", "--wordlist", help="Path to wordlist file")
        parser.add_argument("-e", "--export", help="Export format (json, html, csv, txt)")
        parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
        parser.add_argument("--version", action="store_true", help="Show version and exit")
        
        parser.add_argument("--detection-mode", choices=["simple", "stealth", "aggressive"], 
                           help="Set the detection mode")
        parser.add_argument("--concurrency", type=int, help="Set maximum concurrent requests")
        parser.add_argument("--timeout", type=int, help="Connection timeout in seconds")
        
        parser.add_argument("--http3", action="store_true", help="Enable HTTP/3 protocol support")
        parser.add_argument("--fuzzing", action="store_true", help="Enable path fuzzing")
        parser.add_argument("--fuzzing-depth", type=int, choices=[1, 2, 3], default=1,
                           help="Path fuzzing depth (1-3)")
        parser.add_argument("--rate-limit", type=int, help="Set rate limit (requests per second)")
        parser.add_argument("--no-rate-limit", action="store_true", help="Disable rate limiting")
        
        parser.add_argument("--proxy", help="Proxy server URL (http://host:port or socks5://host:port)")
        parser.add_argument("--proxy-file", help="File containing proxy list (one per line)")
        
        parser.add_argument("--update-wordlist", action="store_true", help="Update wordlists with latest paths")
        parser.add_argument("--source", help="Source URL for wordlist updates")
        parser.add_argument("-v", action="count", default=0, help="Verbose output (-v, -vv, -vvv)")
        
        args = parser.parse_args()
        
        if args.version:
            print(f"Find The Admin Panel v{config.VERSION}")
            print(f"Release Date: {config.RELEASE_DATE}")
            print(f"Developed by: {config.DEVELOPER}")
            print(f"GitHub: {config.GITHUB}")
            return
        
        if args.update_wordlist:
            await update_wordlists(config, args.source, args.interactive)
            if not args.url:
                return
        
        if args.detection_mode and args.detection_mode in config.DETECTION_MODES:
            config.set_detection_mode(args.detection_mode)
            adv_logger.log_info(f"Detection mode set to: {args.detection_mode}")
        
        if args.http3:
            config.USE_HTTP3 = True
            adv_logger.log_info("HTTP/3 support enabled")
        
        if args.fuzzing:
            config.USE_PATH_FUZZING = True
            config.FUZZING_DEPTH = args.fuzzing_depth
            adv_logger.log_info(f"Path fuzzing enabled (depth {args.fuzzing_depth})")
        
        if args.rate_limit:
            config.RATE_LIMIT = args.rate_limit
            config.USE_RATE_LIMITING = True
            adv_logger.log_info(f"Rate limit set to {args.rate_limit} req/s")
        
        if args.no_rate_limit:
            config.USE_RATE_LIMITING = False
            adv_logger.log_info("Rate limiting disabled")
        
        if args.concurrency and args.concurrency > 0:
            config.MAX_CONCURRENT_TASKS = args.concurrency
            adv_logger.log_info(f"Concurrency set to {args.concurrency}")
        
        if args.timeout and args.timeout > 0:
            config.CONNECTION_TIMEOUT = args.timeout
            adv_logger.log_info(f"Connection timeout set to {args.timeout}s")
        
        if args.proxy:
            config.USE_PROXIES = True
            config.PROXIES = [args.proxy]
            adv_logger.log_info(f"Using proxy: {args.proxy}")
        
        if args.proxy_file:
            config.USE_PROXIES = True
            config.PROXY_LIST_FILE = args.proxy_file
            adv_logger.log_info(f"Using proxy file: {args.proxy_file}")
        
        if args.v >= 1:
            adv_logger.log_info(f"Verbose level set to {args.v}")
        
        if args.interactive or not args.url:
            await start_menu(config)
        else:
            await scan_target(config, args.url, args.wordlist, args.export, False)
            
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
        adv_logger.log_warning("Scan interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"Error: {str(e)}")
        adv_logger.log_error(f"Unhandled error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
