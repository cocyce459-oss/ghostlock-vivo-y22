# Ghostlock Aesthetic Guide

## Philosophy

> "Form follows function, but function deserves beauty."

Ghostlock is not just a root tool - it's a statement. Premium software deserves premium aesthetics.

## Design Tokens

```
PRIMARY:     #0A0E27 (Deep Void Black)
ACCENT:      #00D4FF (Neon Cyan)
SECONDARY:   #9D4EDD (Electric Violet)
WARN:        #FF006E (Cyber Magenta)
SUCCESS:     #00F5FF (Ice Blue)
TEXT:        #E0E7FF (Pearl White)
MUTED:       #5A6585
GHOST:       #8B92B5
```

## Typography

- **Code**: IBM Plex Mono, JetBrains Mono, monospace
- **UI**: Inter, Segoe UI, sans-serif
- **Headers**: Bold, 1.2x spacing
- **Body**: Regular, 1.5x line height

## Components

### Banner

```
╔════════════════════════════════════════════════════════════╗
║   ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗██╗      ...   ║
║   Vivo Y22 | MT6769Z Helio G85 | CVE-2026-43499            ║
╚════════════════════════════════════════════════════════════╝
```

### Logging

- `[◈]` Info - Cyan
- `[✓]` Success - Green bold
- `[⚠]` Warning - Yellow
- `[✗]` Error - Red
- `ghost >` Debug - Dim

### Panels

- Border: Cyan glow
- Background: Deep void black
- Padding: 1,2
- Title: Bold

### Tables

- Header: Bold cyan
- Rows: White / dim alternating
- Border: Subtle

## CLI UX

- Use Rich for all output
- Spinner for long tasks
- Progress bar for exploit chain [1/4], [2/4], etc
- Confirm for dangerous actions
- Offline demo mode for safe exploration

## Code Style

- Python: Black formatted, type hints, docstrings
- C: Kernel style, but with Ghostlock header
- Comments: Explain why, not what
- No magic numbers - use defines from target.h

## Branding

- Logo: Ghost + Lock + Neon
- Mood: Minimalist cyberpunk, clean lines, glowing edges
- No clutter, breathing room, premium margins

## Inspiration

- Cyberpunk 2077 UI
- Linear.app design
- Vercel dashboard
- Apple Terminal (but neon)

## Implementation

See:

- `src/utils/colors.py` - Color tokens
- `src/utils/logger.py` - Logging with Rich
- `src/app/main.py` - Premium CLI
- `assets/branding/` - Logo, banner
- `assets/themes/` - CSS/JSON themes
