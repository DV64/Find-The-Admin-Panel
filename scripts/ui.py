import os
import platform
import re
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich.box import ROUNDED, DOUBLE, HEAVY
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich import box
from rich.style import Style
from rich.prompt import Prompt
from rich.columns import Columns

class TerminalDisplay:
    
    def __init__(self):
        self.console = Console()
        self.status_style = Style(color="cyan", bold=True)
        self.title_style = Style(color="blue", bold=True)
        
    def clear_screen(self):
        if platform.system().lower() == "windows":
            os.system("cls")
        else:
            os.system("clear")
    
    def show_banner(self, config):
        banner = Text()
        banner.append("  ███████╗██╗███╗   ██╗██████╗ ███████╗██████╗ \n", style="bold cyan")
        banner.append("  ██╔════╝██║████╗  ██║██╔══██╗██╔════╝██╔══██╗\n", style="bold cyan")
        banner.append("  █████╗  ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝\n", style="bold cyan")
        banner.append("  ██╔══╝  ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗\n", style="bold cyan")
        banner.append("  ██║     ██║██║ ╚████║██████╔╝███████╗██║  ██║\n", style="bold cyan")
        banner.append("  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝\n", style="bold cyan")
        
        banner.append("\n")
        banner.append("  FIND THE ADMIN PANEL - WEB SECURITY TOOL\n", style="bold white")
        banner.append("\n")
        
        version_info = Text("  Version: ", style="white")
        version_info.append(config.VERSION, style="bold cyan")
        version_info.append("   Developer: ", style="white")
        version_info.append(config.DEVELOPER, style="bold cyan")
        version_info.append("   Released: ", style="white")
        version_info.append(config.RELEASE_DATE, style="bold cyan")
        version_info.append("\n")
        
        banner.append(version_info)
        
        self.console.print(Panel(
            banner,
            box=box.HEAVY,
            border_style="blue",
            padding=(1, 2),
            title="[bold white]Admin Panel Finder[/bold white]",
            title_align="center"
        ))
    
    def show_target_info(self, url: str, scan_mode: str = "standard", wordlist_path: str = "", proxies_enabled: bool = False, headless_enabled: bool = False):
        panel = Panel(
            f"[bold white]Target:[/bold white] [cyan]{url}[/cyan]\n"
            f"[bold white]Mode:[/bold white] [cyan]{scan_mode}[/cyan]" + 
            (f"\n[bold white]Wordlist:[/bold white] [cyan]{os.path.basename(wordlist_path)}[/cyan]" if wordlist_path else ""),
            title="[bold]Scan Configuration[/bold]",
            border_style="cyan",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def show_results(self, results):
        if not results:
            self.console.print(Panel("[italic]No results to display.[/italic]", border_style="yellow", box=box.ROUNDED))
            return
        
        table = Table(title="Scan Results", box=box.DOUBLE_EDGE, header_style="bold cyan", border_style="cyan")
        table.add_column("URL", style="cyan", justify="left")
        table.add_column("Status", style="green", justify="center")
        table.add_column("Confidence", style="magenta", justify="center")
        
        sorted_results = sorted(results, key=lambda x: x.get('confidence', 0), reverse=True)
        
        for result in sorted_results:
            url = result.get("url", "Unknown")
            status = str(result.get("status_code", "Unknown"))
            confidence = f"{result.get('confidence', 0) * 100:.1f}%"
            
            url_style = "cyan"
            if result.get('confidence', 0) > 0.5:
                url_style = "bold cyan"
            
            status_style = "green" if status.startswith("2") else "yellow" if status.startswith("3") else "red"
            
            table.add_row(url, f"[{status_style}]{status}[/{status_style}]", confidence)
        
        self.console.print(Panel(table, border_style="cyan", box=box.ROUNDED))
    
    def show_summary(self, total_scanned: int, valid_found: int, scan_time: float, technologies=None):
        success_rate = (valid_found / total_scanned * 100) if total_scanned > 0 else 0
        
        panel = Panel(
            f"[bold white]Total Scanned:[/bold white] [cyan]{total_scanned}[/cyan]\n"
            f"[bold white]Found:[/bold white] [green]{valid_found}[/green]\n"
            f"[bold white]Success Rate:[/bold white] [magenta]{success_rate:.2f}%[/magenta]\n"
            f"[bold white]Scan Time:[/bold white] [cyan]{scan_time:.2f} seconds[/cyan]",
            title="[bold]Scan Summary[/bold]",
            border_style="green",
            box=box.HEAVY
        )
        
        if technologies and len(technologies) > 0:
            tech_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
            tech_table.add_column("Technology", style="cyan")
            tech_table.add_column("Count", style="magenta", justify="right")
            
            for tech, count in technologies.items():
                tech_table.add_row(tech, str(count))
            
            tech_panel = Panel(
                tech_table,
                title="[bold]Detected Technologies[/bold]",
                border_style="cyan",
                box=box.ROUNDED
            )
            
            layout = Layout()
            layout.split_row(
                Layout(panel),
                Layout(tech_panel)
            )
            self.console.print(layout)
        else:
            self.console.print(panel)

    def show_scan_completion(self, results=None, scan_time: float = 0.0, total_paths: int = 0):
        found_count = 0
        if results:
            found_count = sum(1 for r in results if r.get("found", False))
            
        panel = Panel(
            f"[bold]✓ Scan completed in {scan_time:.2f} seconds[/bold]\n"
            f"[green]• Found {found_count} potential admin panels[/green]\n"
            f"[green]• Scanned {total_paths} unique paths[/green]",
            title="[bold]Scan Complete[/bold]",
            border_style="green",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def show_results_list(self, files):
        table = Table(title="Available Results", box=box.DOUBLE, header_style="bold green", border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Filename", style="green")
        table.add_column("Date", style="green")
        table.add_column("Type", style="green", justify="center")
        
        for i, file in enumerate(files, 1):
            if file.endswith(('.json', '.html', '.txt', '.csv')):
                file_type = file.split('.')[-1].upper()
                date_match = re.search(r'(\d{8}_\d{6})', file)
                date = date_match.group(1) if date_match else "Unknown"
                
                if date != "Unknown":
                    try:
                        date_obj = datetime.strptime(date, "%Y%m%d_%H%M%S")
                        date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                
                table.add_row(str(i), file, date, file_type)
        
        self.console.print(Panel(table, border_style="green", box=box.ROUNDED))
    
    def show_help(self):
        help_layout = Layout()
        
        overview = Panel(
            "This tool helps you find admin panels and login pages on websites by scanning common paths and analyzing responses.",
            title="[bold]Overview[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )
        
        features = Table(show_header=False, box=box.SIMPLE)
        features.add_column("Feature", style="bold cyan")
        features.add_column("Description", style="white")
        
        features.add_row("• Multiple scan modes", "Choose between quick, stealth, or aggressive scanning")
        features.add_row("• Smart detection", "AI-powered confidence scoring for results")
        features.add_row("• Export options", "Save results in JSON, HTML, CSV, and TXT formats")
        features.add_row("• Logging system", "Detailed logs for troubleshooting")
        
        features_panel = Panel(
            features,
            title="[bold]Features[/bold]",
            border_style="green",
            box=box.ROUNDED
        )
        
        commands = Table(show_header=False, box=box.SIMPLE)
        commands.add_column("Command", style="bold cyan", width=20)
        commands.add_column("Description", style="white")
        
        commands.add_row("[1] Start Scan", "Begin scanning a target URL")
        commands.add_row("[2] View Results", "Browse previous scan results")
        commands.add_row("[3] Settings", "Configure scan options")
        commands.add_row("[4] Help", "Show this help page")
        commands.add_row("[0] Exit", "Close the application")
        
        commands_panel = Panel(
            commands,
            title="[bold]Commands[/bold]",
            border_style="magenta",
            box=box.ROUNDED
        )
        
        tips = Table(show_header=False, box=box.SIMPLE)
        tips.add_column("Tip", style="bold cyan")
        tips.add_column("Description", style="white")
        
        tips.add_row("• URL Format", "Always include http:// or https:// in your target URLs")
        tips.add_row("• Stealth Mode", "Use for more sensitive targets to avoid detection")
        tips.add_row("• Custom Wordlists", "Create your own wordlists for specialized targets")
        tips.add_row("• HTML Reports", "Check HTML reports for interactive results viewing")
        
        tips_panel = Panel(
            tips,
            title="[bold]Tips & Tricks[/bold]",
            border_style="yellow",
            box=box.ROUNDED
        )
        
        help_layout.split_column(
            Layout(overview, size=5),
            Layout(features_panel, size=10),
            Layout(commands_panel, size=12),
            Layout(tips_panel, size=10)
        )
        
        self.console.print(help_layout)
        
    def show_progress(self, message, completed=None, total=None):
        if completed is not None and total is not None:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[bold cyan]{task.completed}/{task.total}"),
                TextColumn("[magenta]({task.percentage:.0f}%)"),
                expand=True
            ) as progress:
                task = progress.add_task(message, total=total, completed=completed)
                progress.update(task, advance=0)
        else:
            self.console.print(f"[bold blue]➤[/bold blue] [cyan]{message}[/cyan]")
        
    def show_error(self, message):
        self.console.print(Panel(f"[bold red]✘ {message}[/bold red]", border_style="red", box=box.ROUNDED))
        
    def show_warning(self, message):
        self.console.print(Panel(f"[bold yellow]⚠ {message}[/bold yellow]", border_style="yellow", box=box.ROUNDED))
        
    def show_success(self, message):
        self.console.print(Panel(f"[bold green]✓ {message}[/bold green]", border_style="green", box=box.ROUNDED))
    
    def show_info(self, message):
        self.console.print(f"[bold blue]ℹ {message}[/bold blue]")
    
    def get_input(self, prompt):
        return self.console.input(f"[bold cyan]➤[/bold cyan] [cyan]{prompt}[/cyan] ")


display = TerminalDisplay()
