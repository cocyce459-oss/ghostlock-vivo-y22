# Building & Analyzing on Google Colab (CPU-only)

Everything in this repo except the final on-device step runs fine on a plain
CPU. Colab's standard runtime is enough — **no GPU, no accelerator, no paid tier.**

Colab is useful here because it gives you a clean, disposable Linux box with
gcc and Python already present, and you can throw it away when you're done.

---

## What you can do on Colab

| Step | Colab? | Notes |
|------|--------|-------|
| Install Python deps | ✅ | `pip install -r requirements.txt` |
| Fetch the vmlinux | ✅ | Needs internet, ~32 MB |
| Run `analyze_vmlinux.py` | ✅ | Pure CPU, a few seconds |
| Build the **host** binary | ✅ | `gcc`, x86-64 — for local testing only |
| Build the **android** binary | ✅ | Needs the NDK, see below |
| **Run the exploit on the phone** | ❌ | Requires a real device over adb |

> The exploit itself must run **on the Vivo Y22**, not in Colab. Colab is for
> building and analyzing only. Colab has no USB passthrough to your phone.

---

## Option A — notebook

Open `colab/Ghostlock_Colab_Build.ipynb` in Colab:

<https://colab.research.google.com/github/cocyce459-oss/ghostlock-vivo-y22/blob/main/colab/Ghostlock_Colab_Build.ipynb>

Runtime → **Runtime type → CPU only** (this is the default; just leave it).

Then: **Runtime → Run all.**

---

## Option B — one cell at a time

### 1. Clone

```python
!git clone --depth 1 https://github.com/cocyce459-oss/ghostlock-vivo-y22.git
%cd ghostlock-vivo-y22
```

### 2. Install deps

Analysis needs `capstone` and `pyelftools`. The UI extras (`rich`, `typer`,
`psutil`) are only needed for `src/app/main.py`.

```python
!pip install -q capstone pyelftools rich typer psutil
```

### 3. Fetch the vmlinux

```python
!pip install -q gdown
!gdown "1yX1l9SKl-oFFru-prRG-UmCiLfC-Y8MN" -O Kernel.elf
```

Verify you got a real ELF and not a Drive error page:

```python
!file Kernel.elf
```

### 4. Analyze it

```python
!python3 tools/analyze_vmlinux.py --vmlinux Kernel.elf --device vivo-y22 --verbose
```

> `-v` means **verbose**. The path flag is `--vmlinux` (short: `-k`).
> Older docs said `-v Kernel.elf`, which never worked — see the PR notes.

**Read the output.** If you see `KERNEL VERSION MISMATCH`, stop — the offsets
in `src/core/exploit/target.h` are not valid for that kernel build.

### 5. Build the host binary

```python
!cd src/core/exploit && make host && cd -
```

This produces `ghostlock_y22_host`, an **x86-64** binary. It is for
exercising the code paths and printing the target info. It is not for the phone.

### 6. Build the android binary (needs the NDK)

Colab has no NDK by default. Install it in-cell:

```python
!wget -q https://dl.google.com/android/repository/android-ndk-r26d-linux.zip
!unzip -q android-ndk-r26d-linux.zip
```

Then put the clang wrapper on `PATH`:

```python
import os
os.environ["ANDROID_NDK_HOME"] = "/content/android-ndk-r26d"
os.environ["PATH"] = os.environ["ANDROID_NDK_HOME"] + "/toolchains/llvm/prebuilt/linux-x86_64/bin:" + os.environ["PATH"]
```

```python
!cd src/core/exploit && make android && cd -
```

Confirm the architecture — this is the check that matters:

```python
!file src/core/exploit/ghostlock_y22
```

It **must** say `ARM aarch64`. If it says x86-64, stop. The build is
misconfigured; do not push it.

> As of this writing `make android` refuses to fall back to the host compiler,
> so it will error rather than hand you an x86 binary named like the android one.

### 7. Run the read-only preflight

```python
!VMLINUX=Kernel.elf bash scripts/preflight.sh
```

### 8. Download the artifacts to your machine

In Colab: **File → Download** for each, or:

```python
from google.colab import files
files.download("src/core/exploit/ghostlock_y22")
```

---

## On your own machine afterwards

```bash
adb devices                                   # device must be authorized
adb push ghostlock_y22 /data/local/tmp/
adb shell chmod +x /data/local/tmp/ghostlock_y22
```

**Read `docs/safety-guide.md` before you do that.** Then:

```bash
adb shell /data/local/tmp/ghostlock_y22
```

---

## Troubleshooting

**`make: *** [analyze] Error 2`**
You are on an old revision. The `analyze` target shipped broken — the `-v`
flag collided with `--vmlinux`. Update, or just use `--verbose`.

**`Capstone not found`**
`pip install capstone`. Without it the analyzer skips the ADRP scan and falls
back to hardcoded profile offsets, which is *not* analysis.

**`gdown` downloads an HTML file**
Drive rate-limited or the file needs a confirm token. Re-run, or download
manually from the Drive link and upload it to Colab.

**`No space left on device` / long unzip**
The NDK zip is ~700 MB and Colab's disk is finite. `!rm android-ndk-r26d-linux.zip`
right after unzipping.

**Runtime disconnects mid-build**
The NDK download is long. Colab kills idle runtimes; re-run from the cell you
were on. For a longer-lived box use a free CPU VM elsewhere.
