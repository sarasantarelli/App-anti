"""Backup automatici e aggiornamento dell'app (senza toccare dati, norme e template dell'utente)."""
from __future__ import annotations
import os, shutil, tempfile, threading, time, urllib.request, zipfile
from datetime import datetime
from pathlib import Path
from . import service, __version__

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = Path(os.environ.get("APP_BACKUP_DIR", ROOT / "backup"))
KEEP = int(os.environ.get("BACKUP_KEEP", "14"))
UPDATE_URL = os.environ.get("APP_UPDATE_URL", "https://github.com/sarasantarelli/App-anti/archive/refs/heads/claude/fire-safety-assessment-app-0c719q.zip")
RAW_URL = os.environ.get("APP_VERSION_URL", "https://raw.githubusercontent.com/sarasantarelli/App-anti/claude/fire-safety-assessment-app-0c719q/antincendio_app/__init__.py")
CONFIG = ROOT / "config.json"
_agg = {"disponibile": False, "remota": None, "controllato": None, "errore": None}
PROTETTI = {"config.json", "data", "norme", "backup", ".venv", ".git", "templates", "__pycache__"}


def crea_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    f = BACKUP_DIR / f"backup_{datetime.now():%Y%m%d_%H%M%S}.zip"
    base = service.DATA_DIR
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        for p in base.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(base))
    for old in sorted(BACKUP_DIR.glob("backup_*.zip"))[:-KEEP]:
        old.unlink(missing_ok=True)
    return f


def elenco_backup() -> list[dict]:
    if not BACKUP_DIR.exists():
        return []
    return [{"file": p.name, "mb": round(p.stat().st_size / 1e6, 2), "quando": p.stat().st_mtime}
            for p in sorted(BACKUP_DIR.glob("backup_*.zip"), reverse=True)]


def ripristina(zip_path: Path) -> int:
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            dest = (service.DATA_DIR / m).resolve()
            if service.DATA_DIR.resolve() not in dest.parents:      # difesa da path traversal
                continue
            if m.endswith("/"):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(m)); n += 1
    return n


def avvia_backup_periodici():
    def loop():
        while True:
            try:
                el = elenco_backup()
                if not el or time.time() - el[0]["quando"] > 20 * 3600:
                    if any(service.DATA_DIR.glob("*/caso.json")):
                        crea_backup()
            except Exception:
                pass
            time.sleep(3600)
    threading.Thread(target=loop, daemon=True).start()


def applica_zip(path: Path) -> dict:
    """Sovrascrive il codice con quello dello ZIP. Dati, norme, backup e template dell'utente restano intatti
    (i template nuovi vanno in templates/_nuovi/ per il confronto)."""
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(path) as z:
            for m in z.namelist():
                if ".." in Path(m).parts or Path(m).is_absolute():
                    raise ValueError("archivio non valido")
            z.extractall(td)
        radici = [p.parent.parent for p in Path(td).rglob("antincendio_app/__init__.py")]
        if not radici:
            raise ValueError("lo ZIP non contiene l'app (manca antincendio_app)")
        src = radici[0]
        nuova = None
        for line in (src / "antincendio_app" / "__init__.py").read_text(encoding="utf-8").splitlines():
            if line.startswith("__version__"):
                nuova = line.split("=")[1].strip().strip('"\'')
        copiati, nuovi_tpl = 0, []
        for p in src.rglob("*"):
            rel = p.relative_to(src)
            if p.is_dir() or rel.parts[0] in (PROTETTI - {"templates"}) or any(x == "__pycache__" for x in rel.parts):
                continue
            if rel.parts[0] == "templates":
                dest = ROOT / rel
                if dest.exists() and dest.read_bytes() != p.read_bytes():
                    alt = ROOT / "templates" / "_nuovi" / rel.name
                    alt.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, alt); nuovi_tpl.append(rel.name)
                elif not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
                continue
            dest = ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest); copiati += 1
    return {"file_aggiornati": copiati, "versione_precedente": __version__, "versione_nuova": nuova, "template_nuovi_da_confrontare": nuovi_tpl}


def scarica_e_applica() -> dict:
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "agg.zip"
        try:
            urllib.request.urlretrieve(UPDATE_URL, f)
        except Exception as e:
            raise ValueError(f"download non riuscito ({e}). Se il repository è privato, scarica lo ZIP a mano e caricalo qui.")
        return applica_zip(f)


def _vtuple(v: str):
    try:
        return tuple(int(x) for x in str(v).strip().split("."))
    except Exception:
        return (0,)


def versione_remota() -> str | None:
    import re
    with urllib.request.urlopen(RAW_URL, timeout=15) as r:
        m = re.search(r'__version__\s*=\s*"([^"]+)"', r.read().decode("utf-8", "ignore"))
    return m.group(1) if m else None


def controlla_aggiornamenti() -> dict:
    try:
        rem = versione_remota()
        _agg.update(remota=rem, disponibile=bool(rem and _vtuple(rem) > _vtuple(__version__)), controllato=time.time(), errore=None)
    except Exception as e:
        _agg.update(controllato=time.time(), errore=str(e)[:120])
    return dict(_agg)


def stato_aggiornamento() -> dict:
    return dict(_agg)


def leggi_impostazioni() -> dict:
    import json
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    except Exception:
        return {}


def salva_impostazioni(nuove: dict) -> dict:
    import json
    c = leggi_impostazioni(); c.update({k: v for k, v in nuove.items() if k in ("auto_aggiorna",)})
    CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    return c


def avvia_controllo_aggiornamenti(riavvia):
    """Controlla all'avvio e ogni 6 ore. Se «auto_aggiorna» è attivo applica l'aggiornamento (con backup) e chiede il riavvio."""
    def loop():
        time.sleep(20)
        while True:
            st = controlla_aggiornamenti()
            if st["disponibile"] and leggi_impostazioni().get("auto_aggiorna"):
                try:
                    crea_backup(); scarica_e_applica(); riavvia()
                except Exception as e:
                    _agg["errore"] = str(e)[:120]
            time.sleep(6 * 3600)
    threading.Thread(target=loop, daemon=True).start()
