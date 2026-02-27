import os
import sys
import re
import time
import asyncio
import json
from typing import List, Dict, Any, Optional, Union, Callable
from scripts.logger import get_logger
from scripts.ui import TerminalDisplay
from scripts.config import Config
from scripts.scanner import Scanner
from scripts.exporter import ResultExporter
from rich.panel import Panel
from rich.table import Table
from rich import box

adv_logger = get_logger('logs')
display = TerminalDisplay()

class Menu:
    
    def __init__(self, config: Config):
        self.config = config
        self.scanner = None
        self.exporter = ResultExporter(config)
        self.running = True
        self.current_menu = "main"
        self.last_scan_results = []
        self.last_scan_info = {}
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    async def start(self):
        try:
            adv_logger.log_info("Starting menu system")
            
            display.clear_screen()
            display.show_banner(self.config)
            
            self.scanner = await Scanner.create(self.config)
            
            while self.running:
                if self.current_menu == "main":
                    await self._show_main_menu()
                elif self.current_menu == "scan":
                    await self._show_scan_menu()
                elif self.current_menu == "results":
                    await self._show_results_menu()
                elif self.current_menu == "settings":
                    await self._show_settings_menu()
                elif self.current_menu == "help":
                    await self._show_help_menu()
                elif self.current_menu == "exit":
                    self._exit_program()
                    break
                else:
                    self.current_menu = "main"
                    
        except KeyboardInterrupt:
            adv_logger.log_info("Menu system stopped by user (Ctrl+C)")
        except Exception as e:
            adv_logger.log_error(f"Error in menu system: {str(e)}")
        finally:
            if self.scanner:
                await self.scanner.close()
    
    async def _show_main_menu(self):
        display.clear_screen()
        display.show_banner(self.config)
        
        display.console.print(Panel(
            "Select an option to proceed",
            title="[bold]MAIN MENU[/bold]",
            border_style="cyan",
            title_align="center"
        ))
        
        options = [
            ("[bold cyan][[bold white]1[/bold white]][/bold cyan] [bold cyan]Start Scan[/bold cyan]", "Find admin panels on a website"),
            ("[bold cyan][[bold white]2[/bold white]][/bold cyan] [bold cyan]View Results[/bold cyan]", "Browse previous scan results"),
            ("[bold cyan][[bold white]3[/bold white]][/bold cyan] [bold cyan]Settings[/bold cyan]", "Configure scan options"),
            ("[bold cyan][[bold white]4[/bold white]][/bold cyan] [bold cyan]Help[/bold cyan]", "Show help information"),
            ("[bold cyan][[bold white]0[/bold white]][/bold cyan] [bold cyan]Exit[/bold cyan]", "Close the application")
        ]
        
        options_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        options_table.add_column("Option", style="bold cyan")
        options_table.add_column("Description", style="dim")
        
        for option, description in options:
            options_table.add_row(option, description)
        
        display.console.print(options_table)
        
        choice = display.get_input("\nEnter your choice: ")
        
        if choice == "1":
            self.current_menu = "scan"
        elif choice == "2":
            self.current_menu = "results"
        elif choice == "3":
            self.current_menu = "settings"
        elif choice == "4":
            self.current_menu = "help"
        elif choice == "0":
            self.current_menu = "exit"
    
    async def _show_scan_menu(self):
        display.clear_screen()
        display.show_banner(self.config)
        
        display.console.print(Panel(
            "Configure and run scans for admin panels",
            title="[bold]SCAN MENU[/bold]",
            border_style="cyan",
            title_align="center"
        ))
        
        options = [
            ("[bold cyan][[bold white]1[/bold white]][/bold cyan] [bold cyan]Start New Scan[/bold cyan]", "Begin scanning a new target"),
            ("[bold cyan][[bold white]2[/bold white]][/bold cyan] [bold cyan]Configure Scan Options[/bold cyan]", "Set scan parameters"),
            ("[bold cyan][[bold white]3[/bold white]][/bold cyan] [bold cyan]View Results[/bold cyan]", "Browse scan results"),
            ("[bold cyan][[bold white]4[/bold white]][/bold cyan] [bold cyan]Import Target List[/bold cyan]", "Scan multiple targets"),
            ("[bold cyan][[bold white]5[/bold white]][/bold cyan] [bold cyan]Return to Main Menu[/bold cyan]", "Go back to main menu"),
            ("[bold cyan][[bold white]0[/bold white]][/bold cyan] [bold cyan]Exit[/bold cyan]", "Close the application")
        ]
        
        options_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        options_table.add_column("Option", style="bold cyan")
        options_table.add_column("Description", style="dim")
        
        for option, description in options:
            options_table.add_row(option, description)
        
        display.console.print(options_table)
        
        option = display.get_input("Select an option: ")
        
        if option == "1":
            display.clear_screen()
            display.show_banner(self.config)
            
            display.console.print(Panel(
                "Configure target and scan parameters",
                title="[bold]NEW SCAN[/bold]",
                border_style="cyan",
                title_align="center"
            ))
            
            target_url = display.get_input("Enter target URL (e.g., https://example.com): ")
            if not target_url:
                display.show_error("Target URL cannot be empty")
                display.get_input("Press Enter to continue...")
                await self._show_scan_menu()
                return
            
            is_valid, target_url = self._validate_url(target_url)
            if not is_valid:
                display.show_error(f"Invalid URL format: {target_url}")
                display.get_input("Press Enter to continue...")
                await self._show_scan_menu()
                return
            
            display.console.print("\n[bold]Scan Configuration:[/bold]")
            
            scan_modes_table = Table(show_header=False, box=box.SIMPLE, title="[bold]Scan Modes[/bold]", title_style="bold cyan", border_style="cyan")
            scan_modes_table.add_column("Mode", style="bold cyan", width=12)
            scan_modes_table.add_column("Description", style="white")
            
            scan_modes_table.add_row("[bold green]simple[/bold green]", "Fast scan with common paths")
            scan_modes_table.add_row("[bold yellow]stealth[/bold yellow]", "Slower scan with delays to avoid detection")
            scan_modes_table.add_row("[bold red]aggressive[/bold red]", "Comprehensive scan with all available techniques")
            
            display.console.print(scan_modes_table)
            
            scan_mode = display.get_input("\nSelect scan mode [simple/stealth/aggressive] (default: simple): ").lower()
            if not scan_mode or scan_mode.strip() == "":
                scan_mode = "simple"
                display.show_warning(f"Using default mode: {scan_mode}")
            elif scan_mode not in ["simple", "stealth", "aggressive"]:
                display.show_warning(f"Invalid mode '{scan_mode}', using default mode: simple")
                scan_mode = "simple"
            
            default_wordlist = os.path.join(self.base_dir, self.config.DEFAULT_WORDLIST)
            
            print(f"\nDefault wordlist: {default_wordlist}")
            use_custom = display.get_input("Use custom wordlist? [y/N]: ").lower() == "y"
            
            wordlist_path = default_wordlist
            if use_custom:
                wordlist_path = display.get_input("Enter path to wordlist file: ")
                if not os.path.exists(wordlist_path):
                    display.show_error(f"Wordlist file not found: {wordlist_path}")
                    wordlist_path = default_wordlist
                    display.show_warning(f"Using default wordlist: {wordlist_path}")
            
            
            scan_details = f"""[bold]Target URL:[/bold] {target_url}
[bold]Scan Mode:[/bold] {scan_mode}
[bold]Wordlist:[/bold] {wordlist_path}
[bold]Paths:[/bold] Loading...
"""
            
            display.console.print(Panel(
                scan_details,
                title="[bold]Scan Details[/bold]",
                border_style="cyan",
                box=box.ROUNDED
            ))
            
            confirm = display.get_input("\nStart scan? [Y/n]  (default: Y): ").lower() != "n"
            if confirm:
                display.show_progress(f"Starting {scan_mode} scan for {target_url}")
                
                try:
                    paths = []
                    if wordlist_path.endswith('.json'):
                        try:
                            with open(wordlist_path, 'r', encoding='utf-8') as f:
                                paths_data = json.load(f)
                                if isinstance(paths_data, dict) and 'paths' in paths_data:
                                    paths = paths_data['paths']
                                elif isinstance(paths_data, list):
                                    paths = paths_data
                                else:
                                    display.show_error(f"Invalid JSON format in wordlist: {wordlist_path}")
                                    paths = []
                        except Exception as e:
                            display.show_error(f"Error reading JSON file: {str(e)}")
                            paths = []
                    else:
                        try:
                            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                                paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        except Exception as e:
                            display.show_error(f"Error reading wordlist file: {str(e)}")
                            paths = []
                    
                    if not paths:
                        display.show_error("No paths found for scanning in the specified file.")
                        display.get_input("Press Enter to continue...")
                        return

                    self.config.DETECTION_MODE = scan_mode
                    self.config._setup_detection_modes()
                    
                    mode_config = self.config.get_current_mode_config()
                    mode_description = mode_config.get("DESCRIPTION", "")
                    concurrency = mode_config.get("MAX_CONCURRENT_TASKS", self.config.MAX_CONCURRENT_TASKS)
                    
                    display.console.print(f"\n[bold cyan]Mode Details:[/bold cyan] {mode_description}")
                    display.console.print(f"[bold cyan]Concurrency:[/bold cyan] {concurrency} tasks")
                    display.console.print(f"[bold cyan]Confidence Threshold:[/bold cyan] {mode_config.get('CONFIDENCE_THRESHOLD', 0.6)}")
                    
                    total_paths = len(paths)
                    display.show_progress(f"Scanning {total_paths} paths for {target_url}")
                    
                    try:
                        if self.scanner:
                            results = await self.scanner.scan(target_url, paths, self.config.MAX_CONCURRENT_TASKS)
                        else:
                            display.show_error("Scanner not initialized")
                            display.get_input("\nPress Enter to return to main menu...")
                            return
                        
                        if not results and not isinstance(results, list):
                            display.show_warning("No results obtained from scan operation")
                            display.get_input("\nPress Enter to return to main menu...")
                            return
                        
                        scan_info = {}
                        if self.scanner:
                            scan_info = self.scanner.get_scan_info() or {}
                            
                        if not scan_info:
                            scan_info = {
                                "duration": 0,
                                "url": target_url,
                                "mode": scan_mode,
                                "paths_count": total_paths,
                                "found_count": 0
                            }
                        
                        self.last_scan_results = results
                        self.last_scan_info = scan_info
                        
                        scan_time = scan_info.get("duration", 0)
                        found_count = sum(1 for r in results if r.get("found", False))
                        
                        display.show_scan_completion(results, scan_time, total_paths)
                        display.show_results(results)
                        display.show_summary(total_paths, found_count, scan_time)
                        
                        if self.config.SAVE_RESULTS and results:
                            display.show_progress("Exporting results...")
                            export_status = self.exporter.export_results(results, scan_info)
                            display.show_success("Results exported successfully")
                    except Exception as e:
                        adv_logger.log_error(f"Error during scan: {str(e)}", exc_info=True)
                        display.show_error(f"Error during scan: {str(e)}")
                        display.show_warning("Please check your internet connection and verify the URL")
                    
                    display.get_input("\nPress Enter to return to main menu...")
                except Exception as e:
                    display.show_error(f"Error during scan: {str(e)}")
                    display.get_input("Press Enter to continue...")
            
            await self._show_scan_menu()
        elif option == "2":
            await self._show_settings_menu()
            await self._show_scan_menu()
        elif option == "3":
            await self._show_results_menu()
            await self._show_scan_menu()
        elif option == "4":
            if hasattr(self, "_show_import_target_dialog"):
                self._show_import_target_dialog()
            else:
                display.show_error("Import target functionality is not implemented")
                display.get_input("Press Enter to continue...")
            await self._show_scan_menu()
        elif option == "5":
            await self._show_main_menu()
        elif option == "0":
            self._exit_program()
        else:
            display.show_error("Invalid option")
            display.get_input("Press Enter to continue...")
            await self._show_scan_menu()
    
    async def _show_results_menu(self):
        display.clear_screen()
        display.show_banner(self.config)
        
        result_files = self.exporter.list_result_files()
        
        if not result_files:
            display.show_warning("No result files found")
            display.get_input("Press Enter to return to the main menu...")
            self.current_menu = "main"
            return
        
        display.show_results_list(result_files)
        
        choice = display.get_input("\nEnter file number to view or 0 to return to main menu: ")
        
        if choice == "0":
            self.current_menu = "main"
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(result_files):
                    filename = result_files[idx]
                    
                    if filename.endswith(".html"):
                        display.show_success(f"Opening {filename} in web browser...")
                        try:
                            filepath = os.path.join(self.config.RESULTS_DIR, filename)
                            filepath = os.path.abspath(filepath)
                            
                            if sys.platform == 'win32':
                                os.startfile(filepath)
                            elif sys.platform == 'darwin':  
                                os.system(f'open "{filepath}"')
                            else:  
                                os.system(f'xdg-open "{filepath}"')
                        except Exception as e:
                            display.show_error(f"Failed to open file in browser: {str(e)}")
                    else:
                        content = self.exporter.view_result_file(filename)
                        display.clear_screen()
                        display.show_banner(self.config)
                        print(f"\n=== {filename} ===\n")
                        print(content)
                
                display.get_input("\nPress Enter to return to the results menu...")
            except (ValueError, IndexError):
                display.show_error("Invalid selection")
                display.get_input("Press Enter to continue...")
    
    async def _show_settings_menu(self):
        display.clear_screen()
        display.show_banner(self.config)
        
        print("\n[1] Enable/Disable Result Saving")
        print("[2] Change Export Formats")
        print("[3] Change Request Timeout")
        print("[4] Change Maximum Concurrent Requests")
        print("[0] Back to Main Menu")
        
        choice = display.get_input("\nEnter your choice: ")
        
        if choice == "1":
            self.config.SAVE_RESULTS = not self.config.SAVE_RESULTS
            if self.config.SAVE_RESULTS:
                display.show_success("Result saving enabled")
            else:
                display.show_warning("Result saving disabled")
            self.config.save_config()
            display.get_input("Press Enter to continue...")
        elif choice == "2":
            display.clear_screen()
            display.show_banner(self.config)
            print("\nCurrent export formats: " + ", ".join(self.config.EXPORT_FORMATS))
            print("\nAvailable formats: json, html, csv, txt")
            
            formats_input = display.get_input("Enter formats (comma separated, e.g., json,html): ")
            formats = [fmt.strip().lower() for fmt in formats_input.split(",")]
            
            valid_formats = [fmt for fmt in formats if fmt in self.exporter.supported_formats]
            
            if valid_formats:
                self.config.EXPORT_FORMATS = valid_formats
                self.config.save_config()
                display.show_success(f"Export formats updated: {', '.join(valid_formats)}")
            else:
                display.show_error("No valid formats specified")
            
            display.get_input("Press Enter to continue...")
        elif choice == "3":
            display.clear_screen()
            display.show_banner(self.config)
            print(f"\nCurrent request timeout: {self.config.CONNECTION_TIMEOUT} seconds")
            
            timeout_input = display.get_input("Enter new timeout in seconds (5-60): ")
            try:
                timeout = float(timeout_input)
                if 5 <= timeout <= 60:
                    self.config.CONNECTION_TIMEOUT = int(timeout)
                    self.config.save_config()
                    display.show_success(f"Request timeout updated to {timeout} seconds")
                else:
                    display.show_error("Timeout must be between 5 and 60 seconds")
            except ValueError:
                display.show_error("Invalid timeout value")
            
            display.get_input("Press Enter to continue...")
        elif choice == "4":
            display.clear_screen()
            display.show_banner(self.config)
            print(f"\nCurrent maximum concurrent requests: {self.config.MAX_CONCURRENT_TASKS}")
            
            requests_input = display.get_input("Enter new maximum (10-100): ")
            try:
                max_requests = int(requests_input)
                if 10 <= max_requests <= 100:
                    self.config.MAX_CONCURRENT_TASKS = max_requests
                    self.config.save_config()
                    display.show_success(f"Maximum concurrent requests updated to {max_requests}")
                else:
                    display.show_error("Value must be between 10 and 100")
            except ValueError:
                display.show_error("Invalid value")
            
            display.get_input("Press Enter to continue...")
        elif choice == "0":
            self.current_menu = "main"
    
    async def _show_help_menu(self):
        display.clear_screen()
        display.show_banner(self.config)
        
        display.show_help()
        
        display.get_input("\nPress Enter to return to the main menu...")
        self.current_menu = "main"
    
    def _exit_program(self):
        self.running = False
        adv_logger.log_info("Exiting Admin Panel Finder")
        display.clear_screen()
        display.show_banner(self.config)
        print("\nThank you for using Admin Panel Finder!")
        print(f"GitHub: {self.config.GITHUB}")
        print("\nExiting...\n")
    
    def _validate_url(self, url):
        if not re.match(r'^https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}', url):
            return False, url
        return True, url

    def _show_import_target_dialog(self):
        from scripts.ui import display
        
        display.clear_screen()
        display.show_banner(self.config)
        
        display.show_info("Import Target List")
        display.show_warning("This feature is not fully implemented yet")
        display.get_input("Press Enter to continue...")

async def start_menu(config: Config):
    menu = Menu(config)
    await menu.start()
