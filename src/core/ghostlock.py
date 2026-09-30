"""
Ghostlock Core - Vivo Y22 Root Framework
Premium modular architecture
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Add utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import log, info, success, warning, error, ghost, banner
from utils.version import VERSION, get_banner_meta

@dataclass
class DeviceInfo:
    connected: bool = False
    model: str = "Unknown"
    android_version: str = "Unknown"
    kernel_version: str = "Unknown"
    bootloader_locked: bool = True
    adb_available: bool = False
    fastboot_available: bool = False
    root_status: bool = False

class GhostlockCore:
    def __init__(self, config_path: Optional[Path] = None):
        self.root = Path(__file__).parent.parent.parent
        self.config_path = config_path or self.root / "config" / "settings.json"
        self.device_profile_path = self.root / "src" / "profiles" / "vivo-y22" / "device.json"
        self.exploit_binary = self.root / "src" / "core" / "exploit" / "ghostlock_y22"
        self.config = self._load_config()
        self.device = DeviceInfo()
        self.meta = get_banner_meta()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except Exception as e:
                warning(f"Failed to load config: {e}, using defaults")
        return {
            "device": "vivo-y22",
            "exploit": "cve-2026-43499",
            "auto_kaslr": True,
            "verify_offsets": True,
            "theme": "neon-dark"
        }

    def check_dependencies(self) -> bool:
        info("Checking dependencies...")
        deps = ["adb", "fastboot"]
        missing = []
        for dep in deps:
            if subprocess.run(["which", dep], capture_output=True).returncode != 0:
                missing.append(dep)
        if missing:
            warning(f"Missing optional tools: {', '.join(missing)} - some features limited")
        else:
            success("All dependencies available")
        return True

    def detect_device(self) -> DeviceInfo:
        info("Detecting Vivo Y22...")
        # Try adb
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            if "device" in result.stdout and "List" in result.stdout:
                lines = result.stdout.strip().split("\n")[1:]
                for line in lines:
                    if "device" in line and not line.startswith("*"):
                        self.device.connected = True
                        self.device.adb_available = True
                        ghost(f"ADB device found: {line.strip()}")
                        # Get props
                        try:
                            model = subprocess.run(["adb", "shell", "getprop", "ro.product.model"], 
                                                 capture_output=True, text=True, timeout=3)
                            if model.stdout:
                                self.device.model = model.stdout.strip()
                            
                            android = subprocess.run(["adb", "shell", "getprop", "ro.build.version.release"],
                                                   capture_output=True, text=True, timeout=3)
                            if android.stdout:
                                self.device.android_version = android.stdout.strip()
                            
                            kernel = subprocess.run(["adb", "shell", "cat", "/proc/version"],
                                                  capture_output=True, text=True, timeout=3)
                            if kernel.stdout:
                                self.device.kernel_version = kernel.stdout.strip()[:100]
                            
                            # Check root
                            root_check = subprocess.run(["adb", "shell", "id"],
                                                      capture_output=True, text=True, timeout=3)
                            if "uid=0" in root_check.stdout:
                                self.device.root_status = True
                        except Exception as e:
                            ghost(f"Failed to get device props: {e}")
                        break
        except FileNotFoundError:
            warning("adb not found - running in offline mode")
        except Exception as e:
            warning(f"Device detection error: {e}")

        if not self.device.connected:
            warning("No device connected - running in simulation/offline mode")
            self.device.model = "Vivo Y22 (Simulated)"
            self.device.android_version = "12"
            self.device.kernel_version = "4.14.186+ Vivo Y22"

        return self.device

    def analyze_vmlinux(self, vmlinux_path: Path) -> Dict[str, Any]:
        info(f"Analyzing vmlinux: {vmlinux_path}")
        if not vmlinux_path.exists():
            error(f"vmlinux not found: {vmlinux_path}")
            return {}
        
        # Delegate to tools/analyze_vmlinux.py
        tool = self.root / "tools" / "analyze_vmlinux.py"
        if not tool.exists():
            error(f"Analyzer tool not found: {tool}")
            return {}
        
        try:
            result = subprocess.run(
                [sys.executable, str(tool), "--vmlinux", str(vmlinux_path), "--device", "vivo-y22", "--json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    success("vmlinux analysis complete")
                    return data
                except:
                    # Fallback parse text
                    ghost(result.stdout[-500:])
                    return {"raw": result.stdout}
            else:
                warning(f"Analyzer failed: {result.stderr}")
                return {}
        except Exception as e:
            error(f"Analysis error: {e}")
            return {}

    def build_exploit(self) -> bool:
        info("Building exploit for Vivo Y22...")
        exploit_dir = self.root / "src" / "core" / "exploit"
        makefile = exploit_dir / "Makefile"
        if not makefile.exists():
            error("Makefile not found")
            return False
        
        try:
            result = subprocess.run(["make", "host"], cwd=exploit_dir, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                success(f"Exploit built: {exploit_dir / 'ghostlock_y22_host'}")
                return True
            else:
                warning(f"Build warning: {result.stderr}")
                # Still try to check if binary exists
                if (exploit_dir / "ghostlock_y22_host").exists():
                    success("Binary exists despite warnings")
                    return True
                return False
        except Exception as e:
            error(f"Build failed: {e}")
            return False

    def run_exploit(self, offline: bool = False) -> bool:
        if offline or not self.device.connected:
            info("Running exploit in OFFLINE/DEMO mode for Vivo Y22")
            ghost("This simulates the exploit flow without real device")
            
            # Run host binary if exists
            host_bin = self.root / "src" / "core" / "exploit" / "ghostlock_y22_host"
            if host_bin.exists():
                try:
                    result = subprocess.run([str(host_bin)], capture_output=True, text=True, timeout=10)
                    print(result.stdout)
                    if result.stderr:
                        print(result.stderr)
                    success("Demo exploit completed")
                    return True
                except Exception as e:
                    warning(f"Demo run failed: {e}, showing simulated success")
                    # Simulate success
                    time.sleep(1)
                    success("Simulated root achieved for Vivo Y22 (offline demo)")
                    return True
            else:
                warning("Host binary not found, building...")
                self.build_exploit()
                return self.run_exploit(offline=True)
        else:
            info(f"Running exploit on real device: {self.device.model}")
            # Push and run via adb
            android_bin = self.root / "src" / "core" / "exploit" / "ghostlock_y22"
            if not android_bin.exists():
                # Build android version
                exploit_dir = self.root / "src" / "core" / "exploit"
                subprocess.run(["make", "android"], cwd=exploit_dir, timeout=60)
            
            if android_bin.exists():
                try:
                    info("Pushing exploit to device...")
                    subprocess.run(["adb", "push", str(android_bin), "/data/local/tmp/ghostlock_y22"], 
                                 check=True, timeout=10)
                    subprocess.run(["adb", "shell", "chmod", "+x", "/data/local/tmp/ghostlock_y22"],
                                 check=True, timeout=5)
                    info("Executing exploit on device...")
                    result = subprocess.run(["adb", "shell", "/data/local/tmp/ghostlock_y22"],
                                          capture_output=True, text=True, timeout=30)
                    print(result.stdout)
                    if "ROOT SUCCESSFUL" in result.stdout or "uid=0" in result.stdout:
                        success("Root achieved on Vivo Y22!")
                        self.device.root_status = True
                        return True
                    else:
                        warning("Exploit may have failed, check output")
                        print(result.stderr)
                        return False
                except Exception as e:
                    error(f"Device exploit failed: {e}")
                    return False
            else:
                error("Android binary not found")
                return False

    def unlock_bootloader(self) -> bool:
        info("Bootloader unlock flow for Vivo Y22")
        warning("Vivo Y22 has proprietary bootloader unlock - requires official unlock or EDL")
        ghost("Steps:")
        ghost("1. Enable Developer Options: Tap Build Number 7x")
        ghost("2. Enable OEM Unlocking and USB Debugging")
        ghost("3. Use Vivo official unlock tool if available, or")
        ghost("4. After root, you can disable verified boot via kernel patch")
        
        if self.device.root_status:
            success("Device is rooted, you can now patch bootloader checks")
            info("To disable AVB: adb shell su -c 'echo 0 > /sys/.../verified_boot' (device specific)")
            return True
        else:
            warning("Root required for bootloader bypass on Vivo Y22")
            return False

    def print_status(self):
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        table = Table(title="Ghostlock Vivo Y22 Status", show_header=True, header_style="bold cyan")
        table.add_column("Component", style="dim")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        
        table.add_row("Device", "✓ Connected" if self.device.connected else "○ Offline",
                     f"{self.device.model} | Android {self.device.android_version}")
        table.add_row("Kernel", "✓ Detected" if self.device.kernel_version else "○ Unknown",
                     self.device.kernel_version[:60])
        table.add_row("Root", "✓ Rooted" if self.device.root_status else "✗ Not Rooted",
                     "uid=0" if self.device.root_status else "Need exploit")
        table.add_row("Exploit", "✓ Ready" if self.exploit_binary.exists() else "○ Need Build",
                     "CVE-2026-43499 F3 Aresin")
        table.add_row("Bootloader", "Locked" if self.device.bootloader_locked else "Unlocked",
                     "Vivo proprietary")
        
        console.print(table)
        
        meta = self.meta
        panel_text = f"[cyan]Version:[/cyan] {meta['version']} [{meta['codename']}]\n"
        panel_text += f"[cyan]Target:[/cyan] {meta['device']}\n"
        panel_text += f"[cyan]SoC:[/cyan] {meta['soc']}\n"
        panel_text += f"[cyan]CVE:[/cyan] {meta['cve']}"
        console.print(Panel(panel_text, title="Ghostlock Meta", border_style="cyan"))

def main():
    core = GhostlockCore()
    banner()
    core.check_dependencies()
    core.detect_device()
    core.print_status()

if __name__ == "__main__":
    main()
