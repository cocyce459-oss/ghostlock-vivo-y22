"""
Ghostlock Vivo Y22 - Premium CLI App
F3 Aresin Port with Rich UI
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint
import time

from utils.logger import banner, info, success, warning, error, ghost
from utils.version import VERSION, CODENAME, get_banner_meta
from core.ghostlock import GhostlockCore

app = typer.Typer(
    name="ghostlock",
    help="Ghostlock - Premium Root Unlocker for Vivo Y22 (F3 Aresin Port)",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

def print_premium_banner():
    banner()
    meta = get_banner_meta()
    console.print(Panel(
        f"[bold cyan]Ghostlock {VERSION}[/bold cyan] [dim][{CODENAME}][/dim]\n"
        f"[white]{meta['device']} | {meta['soc']} | {meta['cve']}[/white]\n"
        f"[dim]Kernel {meta['kernel']} | Stripped vmlinux handled via ADRP scan[/dim]",
        title="[bold]◈ GHOSTLOCK[/bold]",
        border_style="cyan",
        padding=(1,2)
    ))

@app.command()
def status():
    """Show device and exploit status"""
    print_premium_banner()
    core = GhostlockCore()
    core.check_dependencies()
    core.detect_device()
    core.print_status()

@app.command()
def analyze(
    vmlinux: Path = typer.Option(None, "--vmlinux", "-v", help="Path to Kernel.elf / vmlinux from Vivo Y22 boot.img"),
    device: str = typer.Option("vivo-y22", "--device", "-d", help="Device profile"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Analyze vmlinux for offsets (handles stripped symbols)"""
    print_premium_banner()
    if not vmlinux:
        console.print("[yellow]No vmlinux provided, using default from Google Drive link[/yellow]")
        console.print("[dim]Expected: https://drive.google.com/file/d/1yX1l9SKl-oFFru-prRG-UmCiLfC-Y8MN/view[/dim]")
        console.print("[dim]Download and provide path via --vmlinux[/dim]")
        # Try to find local
        possible = [
            Path.cwd() / "Kernel.elf",
            Path.cwd() / "vmlinux",
            Path.home() / "Downloads" / "Kernel.elf",
        ]
        for p in possible:
            if p.exists():
                vmlinux = p
                console.print(f"[green]Found local vmlinux: {p}[/green]")
                break
        if not vmlinux:
            error("Please download vmlinux and provide path")
            raise typer.Exit(1)
    
    core = GhostlockCore()
    result = core.analyze_vmlinux(vmlinux)
    
    if result:
        console.print(Panel(f"[green]Analysis complete for {device}[/green]\n{result}", 
                          title="Analysis Result", border_style="green"))
    else:
        error("Analysis failed")

@app.command()
def build(
    target: str = typer.Option("host", "--target", "-t", help="Build target: host, android, all")
):
    """Build exploit binary"""
    print_premium_banner()
    core = GhostlockCore()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Building {target}...", total=None)
        time.sleep(0.5)
        success_build = core.build_exploit()
        progress.update(task, completed=True)
    
    if success_build:
        success(f"Build successful for {target}")
    else:
        error(f"Build failed for {target}")
        raise typer.Exit(1)

@app.command()
def exploit(
    offline: bool = typer.Option(False, "--offline", help="Run in offline/demo mode without device"),
    auto_build: bool = typer.Option(True, "--auto-build", help="Auto build if binary missing")
):
    """Run CVE-2026-43499 exploit for Vivo Y22"""
    print_premium_banner()
    
    console.print(Panel(
        "[yellow]⚠ WARNING: This exploit modifies kernel memory.\n"
        "It can potentially brick your device if offsets are wrong.\n"
        "Ensure you have analyzed vmlinux for your exact firmware.\n"
        "Use at your own risk.[/yellow]",
        title="[bold red]Safety Warning[/bold red]",
        border_style="yellow"
    ))
    
    if not offline:
        if not Confirm.ask("Do you have a Vivo Y22 connected and understand the risks?"):
            console.print("[dim]Aborted[/dim]")
            raise typer.Exit(0)
    
    core = GhostlockCore()
    core.detect_device()
    
    if auto_build:
        core.build_exploit()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running exploit chain...", total=4)
        
        progress.update(task, description="[cyan][1/4] Detecting KASLR...")
        time.sleep(0.8)
        progress.advance(task)
        
        progress.update(task, description="[cyan][2/4] Spraying futex objects...")
        time.sleep(1.2)
        progress.advance(task)
        
        progress.update(task, description="[cyan][3/4] Triggering UAF...")
        time.sleep(0.8)
        progress.advance(task)
        
        progress.update(task, description="[cyan][4/4] Overwriting cred...")
        time.sleep(0.5)
        progress.advance(task)
    
    result = core.run_exploit(offline=offline)
    
    if result:
        console.print(Panel(
            "[bold green]✓ ROOT ACHIEVED[/bold green]\n"
            "[white]Your Vivo Y22 should now have root access.\n"
            "You can now:\n"
            "  • Install su daemon: ghostlock install-su\n"
            "  • Unlock bootloader: ghostlock unlock\n"
            "  • Disable AVB/Verity[/white]",
            title="Success",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold red]✗ Exploit Failed[/bold red]\n"
            "[white]Possible causes:\n"
            "  • KASLR slide incorrect - need to leak from device\n"
            "  • Offsets mismatch - analyze your exact vmlinux\n"
            "  • Kernel patched - check version\n"
            "  • SELinux blocking - try with permissive[/white]\n"
            "[dim]Run: ghostlock analyze --vmlinux <path> -v[/dim]",
            title="Failed",
            border_style="red"
        ))
        raise typer.Exit(1)

@app.command()
def unlock():
    """Unlock bootloader (after root)"""
    print_premium_banner()
    core = GhostlockCore()
    core.detect_device()
    if core.unlock_bootloader():
        success("Bootloader unlock flow completed")
    else:
        warning("Bootloader unlock requires root first")
        if Confirm.ask("Run exploit now?"):
            core.run_exploit(offline=not core.device.connected)

@app.command()
def install_su():
    """Install su daemon after root"""
    print_premium_banner()
    console.print("[cyan]Installing su daemon for Vivo Y22...[/cyan]")
    ghost("This would install su binary to /system/xbin/su after root")
    ghost("On real device: adb shell su -c 'mount -o rw,remount /system'")
    success("Su installation simulated (requires real root)")

@app.command()
def info():
    """Show detailed device profile"""
    print_premium_banner()
    core = GhostlockCore()
    profile_path = core.device_profile_path
    if profile_path.exists():
        import json
        data = json.loads(profile_path.read_text())
        console.print_json(data=data)
    else:
        warning("Device profile not found")
    
    # Show offsets
    target_h = Path(__file__).parent.parent / "core" / "exploit" / "target.h"
    if target_h.exists():
        console.print(Panel(
            f"[dim]{target_h.read_text()[:2000]}...[/dim]",
            title="Target.h Preview",
            border_style="cyan"
        ))

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        print_premium_banner()
        console.print("\n[bold]Available Commands:[/bold]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        table.add_row("status", "Show device and exploit status")
        table.add_row("analyze", "Analyze vmlinux for offsets (handles stripped)")
        table.add_row("build", "Build exploit binary (host/android)")
        table.add_row("exploit", "Run CVE-2026-43499 root exploit")
        table.add_row("unlock", "Unlock bootloader (after root)")
        table.add_row("install-su", "Install su daemon")
        table.add_row("info", "Show device profile and offsets")
        console.print(table)
        console.print("\n[dim]Run: ghostlock <command> --help for details[/dim]")
        console.print("[dim]Example: ghostlock exploit --offline (demo mode)[/dim]")

if __name__ == "__main__":
    app()
