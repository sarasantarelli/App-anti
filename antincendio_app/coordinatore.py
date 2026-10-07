"""COORDINATORE: esperto di settore e regista della pipeline.

Sequenza (ogni passo registra nel log e nei rilievi, così l'organo di vigilanza può ricostruire il ragionamento):
 1 LETTURA documenti/foto/video  →  2 ESTRAZIONE dati con fonte  →  3 CONTROLLO dati mancanti
 4 RISCHIO (profili)  →  5 NORMATIVO (percorso A/B/C, DPR 151)  →  6 STRATEGIA (S.1–S.10, esodo, estintori)
 7 MISURE (check-list dal template, azioni correttive)  →  8 CONTROLLO incrociato  →  9 COMPOSIZIONE (docx/pdf)  →  10 VERIFICA del documento.
"""
from __future__ import annotations
import json, shutil, subprocess, tempfile, zipfile
from datetime import datetime
from pathlib import Path
import docx
from .models import Caso
from .agents import ingestion, estrazione, rischio, normativo, strategia, controllo
from . import checklist as CL
from .compositore import minicodice, codice, raccordo, pe

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates"
FILES = {"minicodice": "VRI_Minicodice_template_2.docx", "codice": "VRI_Codice_Integrale_RTO_completa_2.docx", "raccordo": "VRI_Raccordo_CPI_template.docx"}
COMPOSE = {"minicodice": minicodice, "codice": codice, "raccordo": raccordo}


def leggi_documenti(caso: Caso, percorsi: list[str | Path]) -> Caso:
    for p in percorsi:
        ev = ingestion.leggi_file(p)
        caso.evidenze.append(ev)
        caso.log.append(f"Lettura: {ev['file']} ({ev['tipo']}) {len(ev.get('testo', ''))} caratteri {('— ' + ev['nota']) if ev.get('nota') else ''}")
        if ev.get("nota") and ev["tipo"] in ("foto", "video", "documento"):
            caso.add("Lettura", "attenzione", f"{ev['file']}: {ev['nota']}")
    return caso


def analizza(caso: Caso, risposte: dict | None = None) -> tuple[Caso, list, dict]:
    """Esegue gli agenti di analisi. Ritorna (caso, voci_checklist, risposte_effettive)."""
    caso.findings = [f for f in caso.findings if f.agente in ("Lettura", "Estrazione")]
    caso.esito.pop("azioni_extra", None)
    if caso.evidenze:
        estrazione.estrai(caso)
    controllo.pre(caso)
    rischio.profili(caso)
    normativo.qualifica(caso)
    rischio.profili(caso)          # secondo giro: qf,d dipende dal percorso
    strategia.strategia(caso)
    tpl = caso.esito["normativo"]["template"]
    voci = CL.estrai(docx.Document(str(TPL / FILES[tpl])), tpl)
    risposte = dict(risposte if risposte is not None else caso.esito.get("risposte_tecnico", {}))
    caso.esito["risposte_tecnico"] = risposte
    eff = {}
    for v in voci:
        s = CL.suggerisci(v, caso)
        if s:
            eff[v.id] = s
    eff.update({k: v for k, v in risposte.items() if v and (v.get("esito") or v.get("nota"))})
    # azioni: NC dal sopralluogo + verifiche dimensionali + scadenze
    az = CL.azioni_da_nc(voci, eff)
    for e in strategia.verifiche_esodo(caso):
        if not e["ok"]:
            az.append({"priorita": 1 if e["chiave"] in ("uscite", "lcc", "les") else 2, "azione": e["azione"], "misura": "S.4" if e["chiave"] != "estintori" else "S.6",
                       "responsabile": "Datore di lavoro", "scadenza": "", "origine": "dim-" + e["chiave"], "stato": "Aperta"})
            caso.add("Strategia", "critico" if e["chiave"] in ("uscite", "lcc", "les") else "attenzione", f"{e['voce']}: {e['msg']}", "Codice S.4/S.6")
    az.sort(key=lambda a: (a["priorita"], a.get("misura", "")))
    caso.esito["azioni"] = az
    caso.esito["risposte"] = {k: v for k, v in eff.items()}
    controllo.post(caso, voci, eff)
    return caso, voci, eff


def _pdf(docx_path: Path, outdir: Path) -> Path | None:
    try:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx_path)],
                       check=True, capture_output=True, timeout=240)
        p = outdir / (docx_path.stem + ".pdf")
        return p if p.exists() else None
    except Exception:
        return None


def genera(caso: Caso, voci, risposte, outdir: str | Path, pdf=True, tieni_guide=False) -> dict:
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    tpl = caso.esito["normativo"]["template"]
    stato = caso.esito.get("stato", "BOZZA")
    suf = "" if stato.startswith("PRONTO") else "_BOZZA"
    nome = (str(caso.get("ragione_sociale") or "Attivita")).replace(" ", "_").replace("/", "-")[:40]
    res = {"documenti": []}
    f_vri = out / f"VRI_{nome}{suf}.docx"
    pend = COMPOSE[tpl].compila(caso, voci, risposte, f_vri, tieni_guide=tieni_guide)
    f_pe = out / f"Piano_di_Emergenza_{nome}{suf}.docx"
    pend_pe = pe.compila(caso, f_pe, tieni_guide=tieni_guide)
    for f, pn, tipo in ((f_vri, pend, "VRI"), (f_pe, pend_pe, "Piano di Emergenza")):
        prob = controllo.verifica_documento(f, caso)
        item = {"tipo": tipo, "file": f.name, "campi_da_completare": pn, "verifica": prob}
        if pdf:
            p = _pdf(f, out)
            if p:
                item["pdf"] = p.name
        res["documenti"].append(item)
    rel = out / "Relazione_di_controllo.md"
    rel.write_text(relazione(caso, res), encoding="utf-8")
    res["relazione"] = rel.name
    (out / "caso.json").write_text(json.dumps(caso.to_dict(), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    res["stato"] = stato
    return res


def relazione(caso: Caso, res: dict) -> str:
    n, r = caso.esito["normativo"], caso.esito["rischio"]
    L = [f"# Relazione di controllo — {caso.get('ragione_sociale', '')}", "",
         f"Data: {datetime.now():%d/%m/%Y %H:%M} — Stato documento: **{caso.esito.get('stato')}**", "",
         "> Documento interno di tracciabilità del ragionamento automatico. Non sostituisce la valutazione, la firma e le responsabilità di datore di lavoro, RSPP e (se dovuto) professionista antincendio.", "",
         "## Esito analisi", "", f"- Percorso normativo: {n['ramo_descrizione']}",
         f"- Soggetta a DPR 151/2011: {'sì' if n['soggetta_dpr151'] else 'no'} ({n['fonte_assoggettamento']})",
         f"- Rvita {r['rvita']} · Rbeni {r['rbeni']} · Rambiente {'significativo' if r['rambiente_significativo'] else 'non significativo'} · qf {r['qf'] if r['qf'] is not None else 'n.d.'} ({r['qf_fonte']})",
         f"- Classificazione: {'BASSO' if n['rischio_basso'] else 'NON BASSO'} — formazione addetti Livello {n['formazione']['livello']}", "",
         "## Fonti dei dati", ""]
    for k, d in caso.dati.items():
        if d.ok():
            L.append(f"- `{k}` = {d.valore!r} — fonte: {d.fonte}{'' if d.confermato else ' (non confermato dal tecnico)'}")
    L += ["", "## Rilievi degli agenti", ""]
    for f in caso.findings:
        L.append(f"- [{f.livello.upper()}] ({f.agente}) {f.messaggio}" + (f" — _{f.riferimento}_" if f.riferimento else ""))
    L += ["", "## Domande aperte", ""] + [f"- ({d['gravita']}) {d['domanda']}" for d in caso.esito.get("domande", [])]
    L += ["", "## Documenti generati", ""]
    for d in res["documenti"]:
        L.append(f"- {d['tipo']}: `{d['file']}` — campi da completare: {d['campi_da_completare']}" + (f" — verifica: {'; '.join(d['verifica'])}" if d["verifica"] else " — verifica coerenza: ok"))
    L += ["", "## Log di esecuzione", ""] + [f"1. {x}" for x in caso.log]
    return "\n".join(L)


def esegui_tutto(dati: dict, file_input: list, outdir, risposte=None, pdf=True) -> tuple[Caso, dict]:
    c = Caso()
    for k, v in dati.items():
        c.set(k, v)
    leggi_documenti(c, file_input)
    c, voci, eff = analizza(c, risposte)
    res = genera(c, voci, eff, outdir, pdf=pdf)
    return c, res
