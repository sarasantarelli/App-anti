"""CLI:  python -m antincendio_app serve | genera <cartella_documenti> [--dati dati.json] [--out cartella]"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="antincendio_app", description="Valutazione del rischio incendio (VRI) autogestita — senza chiavi API")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="avvia l'interfaccia web")
    s.add_argument("--host", default="127.0.0.1", help="127.0.0.1 = solo questo PC (default); 0.0.0.0 = visibile in rete")
    s.add_argument("--port", type=int, default=8000); s.add_argument("--no-browser", action="store_true")
    sub.add_parser("diagnostica", help="controlla l'installazione e dice cosa manca")
    g = sub.add_parser("genera", help="genera VRI e Piano di Emergenza da una cartella di documenti/foto/video")
    g.add_argument("cartella", nargs="?", default=None); g.add_argument("--dati", help="file JSON con i dati noti (chiavi come nel form)")
    g.add_argument("--out", default="out"); g.add_argument("--no-pdf", action="store_true")
    sub.add_parser("verifica-template", help="audit di coerenza e refusi dei template")
    a = ap.parse_args(argv)
    if a.cmd == "verifica-template":
        from .audit import verifica
        r = verifica()
        print("\n".join("- " + x for x in r) or "Nessuna anomalia rilevata.")
        return 0
    if a.cmd == "diagnostica":
        from .ambiente import diagnostica
        bad = 0
        for c in diagnostica():
            seg = "OK " if c["ok"] else ("ERR" if c["obbligatorio"] else "---")
            print(f"[{seg}] {c['nome']}: {c['dettaglio']}" + ("" if c["ok"] else f"  →  {c['rimedio']}"))
            bad += (not c["ok"] and c["obbligatorio"])
        return 1 if bad else 0
    if a.cmd == "serve":
        import socket, threading, webbrowser, uvicorn
        port = a.port
        for p in range(a.port, a.port + 20):          # prima porta libera
            with socket.socket() as sk:
                if sk.connect_ex((a.host if a.host != "0.0.0.0" else "127.0.0.1", p)) != 0:
                    port = p; break
        url = f"http://localhost:{port}"
        print(f"\nApp-anti avviata: {url}   (CTRL+C per fermare)\nI dati restano su questo PC nella cartella 'data'.")
        if not a.no_browser:
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        uvicorn.run("antincendio_app.web.server:app", host=a.host, port=port, log_level="warning")
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
