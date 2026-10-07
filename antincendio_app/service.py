"""Livello di servizio: gestione delle pratiche su disco (usato da web e CLI)."""
from __future__ import annotations
import json, os, re, shutil, time, uuid, zipfile
from pathlib import Path
from .models import Caso, Dato
from . import coordinatore as CO, schema
from .agents import ingestion

DATA_DIR = Path(os.environ.get("APP_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
RETENTION_H = float(os.environ.get("RETENTION_HOURS", "72"))
MAX_UPLOAD_MB = float(os.environ.get("MAX_UPLOAD_MB", "200"))


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]", "_", Path(name).name)[:120] or "file"


class Store:
    def __init__(self, base: Path = DATA_DIR):
        self.base = Path(base); self.base.mkdir(parents=True, exist_ok=True)

    def path(self, pid: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{12,32}", pid):
            raise KeyError(pid)
        return self.base / pid

    def new(self) -> str:
        pid = uuid.uuid4().hex[:20]
        (self.base / pid / "input").mkdir(parents=True)
        return pid

    def load(self, pid) -> Caso:
        f = self.path(pid) / "caso.json"
        if not f.exists():
            return Caso()
        return Caso.from_dict(json.loads(f.read_text(encoding="utf-8")))

    def save(self, pid, caso: Caso):
        (self.path(pid) / "caso.json").write_text(json.dumps(caso.to_dict(), ensure_ascii=False, default=str), encoding="utf-8")

    def cleanup(self):
        lim = time.time() - RETENTION_H * 3600
        for d in self.base.iterdir():
            try:
                if d.is_dir() and d.stat().st_mtime < lim:
                    shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass


def _conv(tipo: str, v):
    if v is None or v == "":
        return None
    if tipo == "num":
        return float(str(v).replace(",", "."))
    if tipo == "bool":
        return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "si", "sì", "yes")
    if tipo == "tri":
        if isinstance(v, bool):
            return v
        return {"si": True, "sì": True, "true": True, "no": False, "false": False}.get(str(v).lower())
    if tipo == "multi":
        return v if isinstance(v, list) else [x.strip() for x in str(v).split(",") if x.strip()]
    return v


def applica_dati(caso: Caso, dati: dict):
    for k, v in dati.items():
        if k in schema.LISTE:
            vv = [r for r in (v or []) if any(str(x).strip() for x in r.values())]
            if vv:
                caso.set(k, vv, "inserito dal tecnico", True)
            else:
                caso.dati.pop(k, None)
            continue
        tipo = schema.TIPI.get(k, "text")
        try:
            val = _conv(tipo, v)
        except ValueError:
            continue
        if val is None:
            caso.dati.pop(k, None)
        else:
            caso.set(k, val, "inserito dal tecnico", True)


def aggiungi_file(store: Store, pid: str, files: list[tuple[str, bytes]]) -> Caso:
    caso = store.load(pid)
    inp = store.path(pid) / "input"
    tot = sum(f.stat().st_size for f in inp.glob("*"))
    percorsi = []
    for name, content in files:
        tot += len(content)
        if tot > MAX_UPLOAD_MB * 1e6:
            raise ValueError(f"limite di {MAX_UPLOAD_MB:g} MB per pratica superato")
        p = inp / _safe(name)
        p.write_bytes(content)
        percorsi.append(p)
    CO.leggi_documenti(caso, percorsi)
    store.save(pid, caso)
    return caso


def analizza(store: Store, pid: str) -> Caso:
    caso = store.load(pid)
    CO.analizza(caso)
    store.save(pid, caso)
    return caso


def riepilogo(store: Store, pid: str) -> dict:
    caso = store.load(pid)
    if "normativo" not in caso.esito:
        CO.analizza(caso); store.save(pid, caso)
    n, r = caso.esito["normativo"], caso.esito["rischio"]
    from . import checklist as CL
    import docx
    tpl = n["template"]
    voci = CL.estrai(docx.Document(str(CO.TPL / CO.FILES[tpl])), tpl)
    eff = caso.esito.get("risposte", {})
    tec = caso.esito.get("risposte_tecnico", {})
    voci_out = []
    for v in voci:
        e = eff.get(v.id, {})
        voci_out.append({"id": v.id, "misura": v.misura, "gruppo": v.gruppo, "testo": v.testo, "applic": v.applic,
                         "esito": e.get("esito"), "nota": e.get("nota", ""), "azione": tec.get(v.id, {}).get("azione", ""),
                         "auto": bool(e.get("auto")), "manuale": v.id in tec and bool(tec[v.id].get("esito"))})
    st = caso.esito.get("strategia", {})
    return {
        "dati": {k: {"valore": d.valore, "fonte": d.fonte, "confermato": d.confermato} for k, d in caso.dati.items()},
        "evidenze": [{"file": e["file"], "tipo": e["tipo"], "caratteri": len(e.get("testo", "")), "nota": e.get("nota", "")} for e in caso.evidenze],
        "findings": [f.__dict__ for f in caso.findings],
        "domande": caso.esito.get("domande", []),
        "sintesi": {
            "stato": caso.esito.get("stato", "BOZZA"), "template": tpl, "ramo": n["ramo_descrizione"], "soggetta_dpr151": n["soggetta_dpr151"],
            "rischio_basso": n["rischio_basso"], "occupanti": n["occupanti"], "rvita": r["rvita"], "rbeni": r["rbeni"],
            "rambiente": r["rambiente_significativo"], "qf": r["qf"], "qf_fonte": r["qf_fonte"], "formazione": n["formazione"],
            "qfd": r.get("qfd"), "completezza": caso.esito.get("completezza"),
            "livelli": {str(k): v["livello"] for k, v in st.get("misure", {}).items()} if st.get("modo") == "codice" else {},
            "requisiti": n["requisiti_allegato_I"],
        },
        "voci": voci_out,
        "azioni": caso.esito.get("azioni", []),
        "log": caso.log,
    }


def genera(store: Store, pid: str, pdf=True, tieni_guide=False) -> dict:
    caso = store.load(pid)
    CO.analizza(caso)
    import docx
    from . import checklist as CL
    tpl = caso.esito["normativo"]["template"]
    voci = CL.estrai(docx.Document(str(CO.TPL / CO.FILES[tpl])), tpl)
    out = store.path(pid) / "out"
    if out.exists():
        shutil.rmtree(out)
    res = CO.genera(caso, voci, caso.esito["risposte"], out, pdf=pdf, tieni_guide=tieni_guide)
    store.save(pid, caso)
    z = out / "Fascicolo_completo.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out.iterdir():
            if f != z and f.name != "caso.json":
                zf.write(f, f.name)
    res["zip"] = z.name
    return res
