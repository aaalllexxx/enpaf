"""
ENPAF CLI — Console UI Utilities
Beautiful console output with colors, progress bars, and ASCII art.
"""

import io
import sys
import time
import threading
from typing import List, Optional

# Force UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        try:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
        except Exception:
            pass
    # Also enable ANSI escape codes on Windows 10+
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

# Try to use colorama for Windows ANSI support
try:
    import colorama
    colorama.init(autoreset=True)
except ImportError:
    pass


# ─── ANSI Color Codes ────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


C = Colors  # Shortcut


# ─── Logo ─────────────────────────────────────────────────────

LOGO = f"""
{C.BRIGHT_MAGENTA}{C.BOLD}  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   ██████╗  █████╗ ███████╗                           ║
  ║   ██╔══██╗██╔══██╗██╔════╝                           ║
  ║   ██████╔╝███████║█████╗      {C.BRIGHT_CYAN}Python + Web → APK{C.BRIGHT_MAGENTA}    ║
  ║   ██╔═══╝ ██╔══██║██╔══╝      {C.DIM}ENPAF Framework{C.RESET}{C.BRIGHT_MAGENTA}{C.BOLD}      ║
  ║   ██║     ██║  ██║██║          {C.DIM}v1.0.0{C.RESET}{C.BRIGHT_MAGENTA}{C.BOLD}             ║
  ║   ╚═╝     ╚═╝  ╚═╝╚═╝                              ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝{C.RESET}
"""

LOGO_SMALL = f"{C.BRIGHT_MAGENTA}{C.BOLD}  🚀 PAF{C.RESET} {C.DIM}— ENPAF Framework v1.0.0{C.RESET}"


# ─── Print Helpers ────────────────────────────────────────────

def logo():
    """Print the full PAF logo."""
    print(LOGO)


def logo_small():
    """Print the small logo."""
    print(LOGO_SMALL)
    print()


def info(message: str):
    """Print an info message."""
    print(f"  {C.BRIGHT_CYAN}ℹ{C.RESET}  {message}")


def success(message: str):
    """Print a success message."""
    print(f"  {C.BRIGHT_GREEN}✔{C.RESET}  {message}")


def warning(message: str):
    """Print a warning message."""
    print(f"  {C.BRIGHT_YELLOW}⚠{C.RESET}  {C.YELLOW}{message}{C.RESET}")


def error(message: str):
    """Print an error message."""
    print(f"  {C.BRIGHT_RED}✖{C.RESET}  {C.RED}{message}{C.RESET}")


def step(number: int, message: str):
    """Print a numbered step."""
    print(f"  {C.BRIGHT_MAGENTA}{C.BOLD}[{number}]{C.RESET}  {message}")


def header(message: str):
    """Print a section header."""
    print()
    print(f"  {C.BOLD}{C.BRIGHT_WHITE}{message}{C.RESET}")
    print(f"  {C.DIM}{'─' * len(message)}{C.RESET}")


def dim(message: str):
    """Print dimmed text."""
    print(f"  {C.DIM}{message}{C.RESET}")


def newline():
    """Print a blank line."""
    print()


def command_hint(cmd: str, description: str = ""):
    """Print a command hint."""
    desc = f"  {C.DIM}— {description}{C.RESET}" if description else ""
    print(f"    {C.BRIGHT_CYAN}${C.RESET} {C.BOLD}{cmd}{C.RESET}{desc}")


def table(headers: List[str], rows: List[List[str]], indent: int = 4):
    """Print a formatted table."""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Print header
    prefix = " " * indent
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(f"{prefix}{C.BOLD}{C.BRIGHT_WHITE}{header_line}{C.RESET}")
    separator = "  ".join("─" * w for w in widths)
    print(f"{prefix}{C.DIM}{separator}{C.RESET}")

    # Print rows
    for row in rows:
        row_line = "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
        print(f"{prefix}{row_line}")


# ─── Spinner ──────────────────────────────────────────────────

class Spinner:
    """An animated spinner for long-running operations."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Loading..."):
        self.message = message
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame = 0

    def start(self):
        """Start the spinner."""
        self._running = True
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def _animate(self):
        while self._running:
            frame = self.FRAMES[self._frame % len(self.FRAMES)]
            sys.stdout.write(f"\r  {C.BRIGHT_MAGENTA}{frame}{C.RESET}  {self.message}")
            sys.stdout.flush()
            self._frame += 1
            time.sleep(0.08)

    def stop(self, final_message: str = None, is_success: bool = True):
        """Stop the spinner."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        # Clear the line
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()
        if final_message:
            if is_success:
                success(final_message)
            else:
                error(final_message)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ─── Progress Bar ─────────────────────────────────────────────

class ProgressBar:
    """A visual progress bar."""

    def __init__(self, total: int, message: str = "", width: int = 30):
        self.total = total
        self.message = message
        self.width = width
        self.current = 0

    def update(self, amount: int = 1):
        """Update the progress bar."""
        self.current = min(self.current + amount, self.total)
        self._render()

    def set(self, value: int):
        """Set the progress bar to a specific value."""
        self.current = min(value, self.total)
        self._render()

    def _render(self):
        if self.total == 0:
            pct = 100
        else:
            pct = int(self.current / self.total * 100)
        filled = int(self.width * self.current / self.total) if self.total > 0 else self.width
        bar = "█" * filled + "░" * (self.width - filled)
        sys.stdout.write(
            f"\r  {C.BRIGHT_MAGENTA}{bar}{C.RESET}  {pct:>3}%  {C.DIM}{self.message}{C.RESET}"
        )
        sys.stdout.flush()
        if self.current >= self.total:
            print()

    def finish(self):
        """Complete the progress bar."""
        self.set(self.total)


# ─── User Input ───────────────────────────────────────────────

def ask(question: str, default: str = "") -> str:
    """Ask the user for input."""
    default_hint = f" {C.DIM}({default}){C.RESET}" if default else ""
    try:
        answer = input(f"  {C.BRIGHT_CYAN}?{C.RESET}  {question}{default_hint}: ").strip()
        return answer if answer else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def confirm(question: str, default: bool = True) -> bool:
    """Ask the user for yes/no confirmation."""
    hint = "Y/n" if default else "y/N"
    try:
        answer = input(f"  {C.BRIGHT_CYAN}?{C.RESET}  {question} ({hint}): ").strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes", "д", "да")
    except (EOFError, KeyboardInterrupt):
        print()
        return default
