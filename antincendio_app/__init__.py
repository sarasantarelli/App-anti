"""App-anti: valutazione del rischio incendio (VRI/RTO) autogestita, senza chiavi API."""
__version__ = "0.3.0"

import json as _json, os as _os
from pathlib import Path as _Path

# config.json (creato dall'installatore) sposta dati/backup/norme fuori dalla cartella del programma:
# l'aggiornamento del programma non può quindi toccarli.
_cfg = _Path(__file__).resolve().parents[1] / "config.json"
if _cfg.exists():
    try:
        _c = _json.loads(_cfg.read_text(encoding="utf-8"))
        for _k, _e in (("dati", "APP_DATA_DIR"), ("backup", "APP_BACKUP_DIR"), ("norme", "NORME_DIR"), ("porta", "APP_PORT")):
            if _c.get(_k):
                _os.environ.setdefault(_e, str(_c[_k]))
    except Exception:
        pass
