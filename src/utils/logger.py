"""
Ghostlock Logger - Premium logging with Rich
"""
import logging
from rich.logging import RichHandler
from rich.console import Console
from .colors import GhostColors

console = Console()

def get_logger(name: str = "ghostlock") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    handler = RichHandler(
        console=console,
        show_time=True,
        omit_repeated_times=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False
    )
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s", datefmt="[%X]")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

log = get_logger()

def banner():
    console.print(r"""
[bold cyan]
 ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗██╗      ██████╗  ██████╗██╗  ██╗
██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝██║     ██╔═══██╗██╔════╝██║ ██╔╝
██║  ███╗███████║██║   ██║███████╗   ██║   ██║     ██║   ██║██║     █████╔╝ 
██║   ██║██╔══██║██║   ██║╚════██║   ██║   ██║     ██║   ██║██║     ██╔═██╗ 
╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   ███████╗╚██████╔╝╚██████╗██║  ██╗
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝
[/bold cyan]
[dim]  Vivo Y22 | MT6769Z Helio G85 | CVE-2026-43499 | Premium Edition[/dim]
""")

def info(msg: str):
    log.info(f"[cyan]◈[/cyan] {msg}")

def success(msg: str):
    log.info(f"[green]✓[/green] [bold]{msg}[/bold]")

def warning(msg: str):
    log.warning(f"[yellow]⚠[/yellow] {msg}")

def error(msg: str):
    log.error(f"[red]✗[/red] {msg}")

def ghost(msg: str):
    console.print(f"[dim]  ghost > {msg}[/dim]")

def step(num: int, total: int, msg: str):
    console.print(f"[bold cyan][{num}/{total}][/bold cyan] [white]{msg}[/white]")
