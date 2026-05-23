"""
run.py — Start all three servers simultaneously.
Run from the project root: python run.py
 
Starts:
  - Backend      on http://localhost:8000
  - Middle Layer on http://localhost:8001
  - Frontend     on http://localhost:3000
 
Press Ctrl+C to stop all servers.
"""
 
import subprocess
import sys
import os
import signal
import threading
import time
 
# ─── Colors for terminal output ───────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"
 
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
 
# ─── Single shared venv Python ────────────────────────────────────────────────
# Points to the single env/ virtual environment at the project root.
# On Windows: env\Scripts\python.exe
# On Mac/Linux: env/bin/python
if sys.platform == "win32":
    VENV_PYTHON = os.path.join(PROJECT_ROOT, "..", "env", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(PROJECT_ROOT, "..", "env", "bin", "python")
 
# Fall back to current Python if venv not found
if not os.path.exists(VENV_PYTHON):
    print(f"{YELLOW}[warn] venv not found at {VENV_PYTHON}, using system Python{RESET}")
    VENV_PYTHON = sys.executable
 
SERVERS = [
    {
        "name":    "Backend",
        "color":   GREEN,
        "cwd":     os.path.join(PROJECT_ROOT, "backend"),
        "command": [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
    },
    {
        "name":    "Middle Layer",
        "color":   YELLOW,
        "cwd":     os.path.join(PROJECT_ROOT, "middle_layer"),
        "command": [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8001"],
    },
    {
        "name":    "Frontend",
        "color":   CYAN,
        "cwd":     os.path.join(PROJECT_ROOT, "frontend"),
        "command": [VENV_PYTHON, "-m", "http.server", "3000"],
    },
]
 
processes = []
 
 
def stream_output(process, name, color):
    """Stream a server's stdout and stderr to the terminal with a colored prefix."""
    def read_stream(stream):
        for line in iter(stream.readline, b""):
            decoded = line.decode("utf-8", errors="replace").rstrip()
            if decoded:
                print(f"{color}[{name}]{RESET} {decoded}")
 
    t_out = threading.Thread(target=read_stream, args=(process.stdout,), daemon=True)
    t_err = threading.Thread(target=read_stream, args=(process.stderr,), daemon=True)
    t_out.start()
    t_err.start()
 
 
def start_servers():
    print(f"{BOLD}Using Python: {VENV_PYTHON}{RESET}\n")
    for server in SERVERS:
        print(f"{BOLD}{server['color']}Starting {server['name']}...{RESET}")
        proc = subprocess.Popen(
            server["command"],
            cwd=server["cwd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        processes.append((server["name"], proc))
        stream_output(proc, server["name"], server["color"])
        time.sleep(1.5)  # Stagger startup slightly
 
    print(f"\n{BOLD}All servers running:{RESET}")
    print(f"  {GREEN}Backend      ->  http://localhost:8000{RESET}")
    print(f"  {YELLOW}Middle Layer ->  http://localhost:8001{RESET}")
    print(f"  {CYAN}Frontend     ->  http://localhost:3000{RESET}")
    print(f"\n{RED}Press Ctrl+C to stop all servers.{RESET}\n")
 
 
def stop_servers(sig=None, frame=None):
    print(f"\n{RED}{BOLD}Shutting down all servers...{RESET}")
    for name, proc in processes:
        print(f"  Stopping {name}...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"{GREEN}All servers stopped.{RESET}")
    sys.exit(0)
 
 
# ─── Handle Ctrl+C ────────────────────────────────────────────────────────────
signal.signal(signal.SIGINT, stop_servers)
signal.signal(signal.SIGTERM, stop_servers)
 
if __name__ == "__main__":
    start_servers()
    # Keep main thread alive and watch for unexpected exits
    while True:
        for name, proc in processes:
            if proc.poll() is not None:
                print(f"{RED}[{name}] process exited unexpectedly with code {proc.returncode}{RESET}")
        time.sleep(2)