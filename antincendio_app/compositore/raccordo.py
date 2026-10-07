"""Compila il template VRI di raccordo con la pratica VVF (attività soggetta, DPR 151/2011).
Ruoli: la VRI NON sostituisce progetto/SCIA/asseverazione del professionista antincendio."""
from __future__ import annotations
import re
from datetime import date, datetime
from pathlib import Path
from .. import docxkit as K
from .base import Base, nz, fmt_num

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "VRI_Raccordo_CPI_template.docx"


def _data(s):
    try:
        return datetime.strptime(str(s).strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def compila(caso, voci, risposte, out, tieni_guide=False):
    b = Base(TEMPLATE, caso, voci, risposte, tieni_guide)
    n = caso.esito["normativo"]
    b.cover(); b.anagrafica()
    b.label_fill("DATI DELLA PRATICA VVF", {
        "Comando VVF": b.d("comando_vvf"), "Attività Allegato I": " — ".join(x for x in (str(b.d("voce_dpr151") or ""), str(b.d("voce_dpr151_desc") or "")) if x) or None,
        "Categoria": b.d("categoria_dpr151"), "Tipo di procedimento": b.d("tipo_procedimento"), "Estremi pratica": b.d("estremi_pratica"),
        "Data rilascio": b.d("data_cpi"), "Periodicità": (f"{int(float(b.d('periodicita_rinnovo')))} anni" if b.d("periodicita_rinnovo") else None),
        "Scadenza prossimo": b.d("scadenza_rinnovo"), "Professionista antincendio": b.d("professionista_antincendio")})
    # VRI-2.1
    scr = [x for x in n["screening"] if x["esito"] == "SOPRA"]
    b.label_fill("Elemento", {
        "Voce Allegato I": f"n. {b.d('voce_dpr151') or ', '.join(str(x['voce']) for x in scr) or '___'} — {b.d('voce_dpr151_desc') or (scr[0]['descrizione'] if scr else '___')}",
        "Parametro di soglia": (f"{scr[0]['soglia']} — rilevato {scr[0]['valore']}" if scr else None),
        "Categoria risultante": b.d("categoria_dpr151")})
    # VRI-2.2 stato pratica
    scad = _data(b.d("scadenza_rinnovo"))
    for _, t in K.find_tables(b.doc, "Verifica"):
        if len(t.rows) == 6 and K.ctext(t.rows[1].cells[0]).startswith("Tipo di procedimento"):
            tp = str(b.d("tipo_procedimento") or "").lower()
            cs = K.uniq_cells(t.rows[1])
            for key, lab in (("cpi", "CPI ex art. 3"), ("scia", "SCIA art. 4"), ("attestaz", "Attestazione")):
                if key in tp:
                    K.tick(cs[1], lab)
            if b.d("estremi_pratica"):
                K.set_cell(K.uniq_cells(t.rows[2])[1], str(b.d("estremi_pratica")))
            cat = str(b.d("categoria_dpr151") or "").upper()
            if cat:
                cs4 = K.uniq_cells(t.rows[4])
                K.choose(cs4[1], "N.A. (cat" if cat != "C" else "Presente")
            cs5 = K.uniq_cells(t.rows[5])
            if scad:
                oggi = date.today()
                if scad >= oggi:
                    K.choose(cs5[1], "Sì, prossima scadenza"); K.fill_tokens(cs5[1], [scad.strftime("%d/%m/%Y")])
                else:
                    mesi = max(1, (oggi.year - scad.year) * 12 + oggi.month - scad.month)
                    K.choose(cs5[1], "Scaduto, in ritardo"); K.fill_tokens(cs5[1], [None, str(mesi)])
                    K.shade(cs5[1], K.NC_FILL)
                    caso.add("Raccordo", "critico", f"Rinnovo periodico della pratica VVF scaduto il {scad:%d/%m/%Y}: attivare subito il professionista antincendio (art. 5 DPR 151/2011).", "DPR 151/2011 art. 5")
                    caso.esito.setdefault("azioni_extra", []).append({"priorita": 1, "azione": f"Rinnovo periodico VVF scaduto il {scad:%d/%m/%Y}: incaricare il professionista antincendio e presentare l'attestazione di rinnovo", "misura": "VRI-2.2", "responsabile": "Datore di lavoro / professionista antincendio", "scadenza": "entro 30 gg", "stato": "Aperta", "origine": "scadenza-vvf"})
    for _, t in K.find_tables(b.doc, "CONCLUSIONE VRI-2"):
        pass
    for t in b.doc.tables:
        if len(t.rows) == 1 and K.ctext(t.rows[0].cells[0]).startswith("CONCLUSIONE VRI-2"):
            stato = "scaduta" if scad and scad < date.today() else ("regolare" if scad else "da verificare")
            K.fill_tokens(t.rows[0].cells[0], [str(b.d("categoria_dpr151") or "___"), f"{stato}; la VRI non sostituisce progetto, SCIA o asseverazione del professionista antincendio"])
    b.attivita(); b.affollamento(); b.sostanze()
    # VRI-6
    sost = set(b.d("sostanze", []) or [])
    rs = bool(b.d("sostanze_significative") or b.d("lavorazioni_pericolose") or sost & {"liquidi infiammabili", "gpl/gas", "esplosivi/ATEX"})
    for _, t in K.find_tables(b.doc, "Locale/Area"):
        hdr = [K.ctext(x) for x in K.uniq_cells(t.rows[0])]
        if len(hdr) == 4:
            cs = K.uniq_cells(t.rows[1])
            K.set_cell(cs[0], "Intera attività")
            K.set_cell(cs[1], "a/b da confermare per singola area (V.1.1 c.2)" if rs else "Nessuno dei criteri a–h soddisfatto sui dati disponibili")
            K.choose(cs[2], "Rischio specifico" if rs else "Nessuno")
    b.innesco()
    b.checklist()
    # VRI-9 gestione
    f = n["formazione"]
    gest = {"Designazione addetti": ("addetti_antincendio_nominati", "Addetti antincendio nominati (art. 4 DM 2/9/2021)"),
            "Formazione addetti": (None, f"Livello {f['livello']} ({f['ore']} ore) — attestati da verificare"),
            "Piano di Emergenza": ("piano_emergenza_presente", "Piano di Emergenza presente"),
            "Prove di evacuazione": ("prove_evacuazione", "Prove di evacuazione citate"),
            "Registro dei controlli": ("registro_controlli_presente", "Registro dei controlli presente")}
    for _, t in K.find_tables(b.doc, "Adempimento"):
        for rw in t.rows[1:]:
            cs = K.uniq_cells(rw)
            lab = K.ctext(cs[0])
            for k, (key, txt) in gest.items():
                if lab.startswith(k):
                    if key is None or caso.get(key):
                        src = f" (fonte: {caso.dati[key].fonte})" if key and key in caso.dati else ""
                        K.set_cell(cs[1], txt + src + " — verificare date e aggiornamento")
    # VRI-10 scostamenti da NC
    nc = [v for v in voci if risposte.get(v.id, {}).get("esito") == "NC"]
    for _, t in K.find_tables(b.doc, "Scostamento rilevato"):
        completo = caso.esito.get("completezza", {}).get("percento", 0) == 100
        if not nc and not completo:
            continue   # sopralluogo incompleto: non si dichiara «nessuno scostamento»
        if not nc:
            cs = K.uniq_cells(t.rows[1])
            K.set_cell(cs[0], "Nessuno scostamento rilevato alla data di redazione"); K.choose(cs[1], "Nessuno")
            K.set_cell(cs[2], "nessuno"); K.choose(cs[3], "Bassa")
            for j in range(len(t.rows) - 1, 1, -1):
                K.delete_row(t, j)
        else:
            K.ensure_rows(t, 1, len(nc))
            for i, v in enumerate(nc, start=1):
                cs = K.uniq_cells(t.rows[i])
                r = risposte[v.id]
                K.set_cell(cs[0], f"{v.misura}: {v.testo.split(' / ')[0][:150]} — {r.get('nota') or 'non coerente'}")
                K.set_cell(cs[2], "classificazione (sostanziale / non sostanziale, art. 4 c.6 Reg.) e adempimento: a cura del professionista antincendio")
                K.choose(cs[3], "Alta/Urgente" if PRI_ALTA(v) else "Media")
            for j in range(len(t.rows) - 1, len(nc), -1):
                K.delete_row(t, j)
    for t in b.doc.tables:
        if len(t.rows) == 1 and K.ctext(t.rows[0].cells[0]).startswith("CONCLUSIONE: [nessuno"):
            if not nc and caso.esito.get("completezza", {}).get("percento", 0) != 100:
                continue
            K.set_cell(t.rows[0].cells[0], ("CONCLUSIONE: nessuno scostamento rilevante rispetto al progetto approvato alla data di redazione."
                                            if not nc else f"CONCLUSIONE: rilevati {len(nc)} scostamenti da classificare a cura del professionista antincendio (sostanziali / non sostanziali) prima di ogni valutazione di adempimento SCIA."))
    caso.esito["azioni"] = (caso.esito.get("azioni", []) + caso.esito.get("azioni_extra", []))
    b.azioni(); b.periodicita(); b.sottoscrizioni()
    b.label_fill("DATI DEL DOCUMENTO", {"Data di emissione": nz(b.d("data_emissione"), date.today().strftime("%d/%m/%Y")), "Revisione n.": b.revisione_str()})
    pend = b.finalize()
    b.salva(out)
    return pend


def PRI_ALTA(v):
    from ..checklist import PRIORITA_ALTA
    return bool(PRIORITA_ALTA.search(v.testo))
