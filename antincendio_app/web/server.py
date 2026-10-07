"""Interfaccia web (FastAPI). Nessuna chiave API: tutta l'elaborazione è locale.

Sicurezza per l'esposizione pubblica:
 - APP_PASSWORD (consigliato): abilita l'autenticazione HTTP Basic (utente qualsiasi, password = APP_PASSWORD)
 - ogni pratica ha un ID casuale non indovinabile; i dati si cancellano dopo RETENTION_HOURS (default 72 h)
 - limite di upload MAX_UPLOAD_MB per pratica
"""
from __future__ import annotations
import os, secrets, threading, time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .. import service, schema, __version__

STATIC = Path(__file__).parent / "static"
store = service.Store()
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    from ..agents import norme
    norme.indicizza_async()
    def loop():
        while True:
            store.cleanup(); time.sleep(3600)
    threading.Thread(target=loop, daemon=True).start()
    yield


app = FastAPI(title="App-anti — Valutazione rischio incendio", version=__version__, lifespan=lifespan)
security = HTTPBasic(auto_error=False)
PASSWORD = os.environ.get("APP_PASSWORD", "")


def auth(cred: HTTPBasicCredentials | None = Depends(security)):
    if not PASSWORD:
        return
    if cred is None or not secrets.compare_digest(cred.password.encode(), PASSWORD.encode()):
        raise HTTPException(401, "Autenticazione richiesta", headers={"WWW-Authenticate": 'Basic realm="App-anti"'})


def _pid(pid: str):
    try:
        store.path(pid)
        if not (store.path(pid)).exists():
            raise KeyError
    except KeyError:
        raise HTTPException(404, "Pratica non trovata")
    return pid


@app.get("/api/health")
def health():
    return {"ok": True, "versione": __version__}


@app.get("/api/schema", dependencies=[Depends(auth)])
def get_schema():
    return {"campi": [{"chiave": k, "label": l, "tipo": t, "gruppo": g, "aiuto": a} for k, l, t, g, a in schema.CAMPI],
            "tipologie": schema.TIPOLOGIE,
            "liste": {k: {"label": v["label"], "colonne": [{"chiave": c, "label": l, "tipo": t} for c, l, t in v["colonne"]]} for k, v in schema.LISTE.items()}}


@app.get("/api/norme", dependencies=[Depends(auth)])
def norme_cerca(q: str, n: int = 5):
    from ..agents import norme
    return norme.cerca(q, min(n, 10))


@app.get("/api/norme/elenco", dependencies=[Depends(auth)])
def norme_elenco():
    from ..agents import norme
    return {"documenti": norme.elenco(), "stato": norme.stato()}


@app.post("/api/norme/upload", dependencies=[Depends(auth)])
async def norme_upload(files: list[UploadFile] = File(...)):
    from ..agents import norme
    try:
        for f in files:
            norme.aggiungi(f.filename or "norma.pdf", await f.read())
    except ValueError as e:
        raise HTTPException(400, str(e))
    norme.indicizza_async()
    return {"documenti": norme.elenco(), "stato": norme.stato()}


@app.delete("/api/norme/{nome}", dependencies=[Depends(auth)])
def norme_del(nome: str):
    from ..agents import norme
    norme.rimuovi(nome)
    return {"documenti": norme.elenco()}


@app.get("/api/pratiche", dependencies=[Depends(auth)])
def elenco():
    return store.elenco()


@app.delete("/api/pratiche/{pid}", dependencies=[Depends(auth)])
def elimina(pid: str):
    _pid(pid)
    store.elimina(pid)
    return {"ok": True}


@app.get("/api/diagnostica", dependencies=[Depends(auth)])
def diagnostica():
    from ..ambiente import diagnostica as dg
    return dg()


@app.post("/api/pratiche", dependencies=[Depends(auth)])
async def nuova(files: list[UploadFile] = File(default=[])):
    pid = store.new()
    try:
        data = [(f.filename or "file", await f.read()) for f in files]
        if data:
            service.aggiungi_file(store, pid, data)
        service.analizza(store, pid)
    except ValueError as e:
        raise HTTPException(413, str(e))
    return {"id": pid, **service.riepilogo(store, pid)}


@app.get("/api/pratiche/{pid}", dependencies=[Depends(auth)])
def leggi(pid: str):
    return {"id": _pid(pid), **service.riepilogo(store, pid)}


@app.post("/api/pratiche/{pid}/file", dependencies=[Depends(auth)])
async def carica(pid: str, files: list[UploadFile] = File(...)):
    _pid(pid)
    try:
        service.aggiungi_file(store, pid, [(f.filename or "file", await f.read()) for f in files])
    except ValueError as e:
        raise HTTPException(413, str(e))
    service.analizza(store, pid)
    return {"id": pid, **service.riepilogo(store, pid)}


@app.put("/api/pratiche/{pid}/dati", dependencies=[Depends(auth)])
async def dati(pid: str, request: Request):
    _pid(pid)
    body = await request.json()
    caso = store.load(pid)
    service.applica_dati(caso, body)
    store.save(pid, caso)
    service.analizza(store, pid)
    return {"id": pid, **service.riepilogo(store, pid)}


@app.put("/api/pratiche/{pid}/risposte", dependencies=[Depends(auth)])
async def risposte(pid: str, request: Request):
    _pid(pid)
    body = await request.json()     # {voce_id: {esito, nota, azione, priorita, responsabile, scadenza}}
    caso = store.load(pid)
    tec = caso.esito.get("risposte_tecnico", {})
    for k, v in body.items():
        if not v or not (v.get("esito") or v.get("nota") or v.get("azione")):
            tec.pop(k, None)
        else:
            tec[k] = {x: v.get(x) for x in ("esito", "nota", "azione", "priorita", "responsabile", "scadenza") if v.get(x) not in (None, "")}
    caso.esito["risposte_tecnico"] = tec
    store.save(pid, caso)
    service.analizza(store, pid)
    return {"id": pid, **service.riepilogo(store, pid)}


@app.post("/api/pratiche/{pid}/genera", dependencies=[Depends(auth)])
def genera(pid: str, pdf: bool = True):
    _pid(pid)
    return service.genera(store, pid, pdf=pdf)


@app.get("/api/pratiche/{pid}/download/{nome}", dependencies=[Depends(auth)])
def download(pid: str, nome: str):
    _pid(pid)
    f = store.path(pid) / "out" / Path(nome).name
    if not f.exists():
        raise HTTPException(404, "File non trovato")
    return FileResponse(f, filename=f.name)


@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/", dependencies=[Depends(auth)])
def index():
    return FileResponse(STATIC / "index.html")
