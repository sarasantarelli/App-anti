"""Modalità «gestionale»: l'app sta in background (senza finestra nera), si apre come finestra dedicata,
si riavvia da sola dopo un aggiornamento e parte con Windows se richiesto.

Uso: python -m antincendio_app gestionale   (o doppio clic su GESTIONALE.pyw / sul collegamento del Desktop)
"""
from __future__ import annotations
import os, platform, shutil, socket, subprocess, sys, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("APP_PORT", "8000"))
URL = f"http://localhost:{PORT}"
RESTART_CODE = 3


def _in_ascolto(port=PORT) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _browser_app() -> list[str] | None:
    """Edge/Chrome in modalità «app» (finestra senza schede, come un programma)."""
    cands = []
    if platform.system() == "Windows":
        for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [Path(base) / "Microsoft/Edge/Application/msedge.exe", Path(base) / "Google/Chrome/Application/chrome.exe"]
    else:
        for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            p = shutil.which(n)
            if p:
                cands.append(Path(p))
    for p in cands:
        if p.exists():
            return [str(p), f"--app={URL}", "--window-size=1280,860"]
    return None


def apri_finestra():
    cmd = _browser_app()
    if cmd:
        try:
            subprocess.Popen(cmd)
            return
        except Exception:
            pass
    webbrowser.open(URL)


def _py_server() -> list[str]:
    cmd = [sys.executable.replace("pythonw.exe", "python.exe"), "-m", "antincendio_app", "serve", "--no-browser", "--port", str(PORT)]
    if os.environ.get("APP_HOST"):
        cmd += ["--host", os.environ["APP_HOST"]]
    return cmd


def supervisore():
    """Tiene acceso il server; se esce con codice 3 (aggiornamento) reinstalla i componenti e riparte."""
    flags = 0x08000000 if platform.system() == "Windows" else 0   # CREATE_NO_WINDOW
    while True:
        p = subprocess.Popen(_py_server(), cwd=str(ROOT), creationflags=flags, env={**os.environ, "APP_SUPERVISED": "1"})
        rc = p.wait()
        if rc != RESTART_CODE:
            return rc
        subprocess.run([sys.executable.replace("pythonw.exe", "python.exe"), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")],
                       cwd=str(ROOT), creationflags=flags)


def main(silenzioso: bool = False):
    if _in_ascolto():
        if not silenzioso:
            apri_finestra()              # già in esecuzione: basta aprire la finestra
        return 0
    import threading
    def attendi_e_apri():
        for _ in range(120):
            if _in_ascolto():
                if not silenzioso:
                    apri_finestra()
                return
            time.sleep(0.5)
    threading.Thread(target=attendi_e_apri, daemon=True).start()
    return supervisore()


if __name__ == "__main__":
    sys.exit(main("--silenzioso" in sys.argv))
