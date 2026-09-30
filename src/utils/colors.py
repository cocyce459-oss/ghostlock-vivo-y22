"""
Ghostlock - Premium Color System
Deep obsidian + neon cyan + electric violet
"""
from rich.style import Style

# Core Palette - Ghostlock Design Tokens
class GhostColors:
    # Backgrounds
    VOID_BLACK = "#0A0E27"
    DEEP_SPACE = "#101534"
    OBSIDIAN = "#0D1117"
    
    # Accents - Neon
    NEON_CYAN = "#00D4FF"
    ICE_BLUE = "#00F5FF"
    ELECTRIC_VIOLET = "#9D4EDD"
    CYBER_MAGENTA = "#FF006E"
    
    # Text
    PEARL_WHITE = "#E0E7FF"
    GHOST_GRAY = "#8B92B5"
    MUTED = "#5A6585"
    
    # Semantic
    SUCCESS = "#00FF88"
    WARNING = "#FFB800"
    ERROR = "#FF006E"
    INFO = "#00D4FF"

    # Rich Styles
    @classmethod
    def styles(cls):
        return {
            "primary": Style(color=cls.NEON_CYAN, bold=True),
            "secondary": Style(color=cls.ELECTRIC_VIOLET),
            "success": Style(color=cls.SUCCESS, bold=True),
            "warning": Style(color=cls.WARNING, bold=True),
            "error": Style(color=cls.ERROR, bold=True),
            "muted": Style(color=cls.MUTED),
            "ghost": Style(color=cls.GHOST_GRAY),
            "pearl": Style(color=cls.PEARL_WHITE),
        }

# ANSI fallback for non-rich contexts
class AnsiColors:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    VIOLET = "\033[95m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
