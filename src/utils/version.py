"""
Ghostlock Version Metadata
"""
VERSION = "2.0.0-y22-aresin"
CODENAME = "F3 Aresin"
TARGET_DEVICE = "Vivo Y22 (V2127 / PD2226)"
SOC = "MediaTek MT6769Z / Helio G85"
KERNEL_BASE = "4.14.186+ (Vivo stock)"
CVE = "CVE-2026-43499"
EXPLOIT_TYPE = "Futex PI futex_q + waiter use-after-free -> cred overwrite"

def get_version_string():
    return f"Ghostlock {VERSION} [{CODENAME}] for {TARGET_DEVICE}"

def get_banner_meta():
    return {
        "version": VERSION,
        "codename": CODENAME,
        "device": TARGET_DEVICE,
        "soc": SOC,
        "kernel": KERNEL_BASE,
        "cve": CVE,
    }
