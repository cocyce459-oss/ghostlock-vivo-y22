# Ghostlock Vivo Y22 - Root Makefile
.PHONY: all setup build host android clean status exploit analyze help

PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

all: setup build

setup:
	@echo "[*] Setting up Ghostlock Vivo Y22..."
	@bash scripts/setup.sh

build:
	@bash scripts/build.sh

host:
	@cd src/core/exploit && make host

android:
	@cd src/core/exploit && make android

clean:
	@echo "[*] Cleaning..."
	@rm -rf venv __pycache__ src/__pycache__ src/*/__pycache__ src/*/*/__pycache__
	@cd src/core/exploit && make clean || true
	@rm -f Kernel.elf vmlinux
	@echo "[✓] Cleaned"

status:
	@$(PY) src/app/main.py status || $(PYTHON) src/app/main.py status

exploit:
	@$(PY) src/app/main.py exploit --offline || $(PYTHON) src/app/main.py exploit --offline

analyze:
	@echo "[*] Analyze vmlinux (provide path via VMLINUX=...)"
	@$(PY) tools/analyze_vmlinux.py --vmlinux $(VMLINUX) --device vivo-y22 -v || $(PYTHON) tools/analyze_vmlinux.py --vmlinux $(VMLINUX) --device vivo-y22 -v

help:
	@echo "Ghostlock Vivo Y22 - Make targets:"
	@echo "  setup    - Create venv and install deps"
	@echo "  build    - Build exploit binaries"
	@echo "  host     - Build host version"
	@echo "  android  - Build android version (needs NDK)"
	@echo "  status   - Show device status"
	@echo "  exploit  - Run exploit in offline demo mode"
	@echo "  analyze  - Analyze vmlinux: make analyze VMLINUX=Kernel.elf"
	@echo "  clean    - Clean build artifacts"
