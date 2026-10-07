"""CLI:  python -m antincendio_app serve | genera <cartella_documenti> [--dati dati.json] [--out cartella]"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="antincendio_app", description="Valutazione del rischio incendio (VRI) autogestita — senza chiavi API")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="avvia l'interfaccia web")
    s.add_argument("--host", default="0.0.0.0"); s.add_argument("--port", type=int, default=8000)
    g = sub.add_parser("genera", help="genera VRI e Piano di Emergenza da una cartella di documenti/foto/video")
    g.add_argument("cartella", nargs="?", default=None); g.add_argument("--dati", help="file JSON con i dati noti (chiavi come nel form)")
    g.add_argument("--out", default="out"); g.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("antincendio_app.web.server:app", host=a.host, port=a.port)
        return 0
    from .coordinatore import esegui_tutto
    dati = json.loads(Path(a.dati).read_text(encoding="utf-8")) if a.dati else {}
    files = sorted(p for p in Path(a.cartella).iterdir() if p.is_file()) if a.cartella else []
    caso, res = esegui_tutto(dati, files, a.out, pdf=not a.no_pdf)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\nStato: {res['stato']} — vedere {a.out}/Relazione_di_controllo.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
