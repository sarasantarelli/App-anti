"""Compila il template VRI Minicodice (basso rischio, DM 3/9/2021 Allegato I)."""
from __future__ import annotations
import math
from pathlib import Path
from .. import docxkit as K
from .base import Base, nz, fmt_num

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "VRI_Minicodice_template_2.docx"


def compila(caso, voci, risposte, out, tieni_guide=False):
    b = Base(TEMPLATE, caso, voci, risposte, tieni_guide)
    n = caso.esito["normativo"]
    b.cover(); b.anagrafica()

    # VRI-2.1 -------------------------------------------------------------------
    scr = n["screening"]
    for _, t in K.find_tables(b.doc, "Voce Allegato I potenzialmente pertinente"):
        righe = scr or [{"voce": "—", "descrizione": "Nessuna voce dell'Allegato I individuata come pertinente (tipologia: "
                         + (", ".join(b.d("tipologia_attivita", []) or []) or "n.d.") + ")", "soglia": "—", "valore": "", "esito": "sotto"}]
        K.ensure_rows(t, 1, len(righe))
        for i, r in enumerate(righe, start=1):
            cs = K.uniq_cells(t.rows[i])
            K.set_cell(cs[0], f"n. {r['voce']} — {r['descrizione']}" if r["voce"] != "—" else r["descrizione"])
            K.set_cell(cs[1], f"{r['soglia']} (rilevato: {r['valore']})" if r.get("valore") else r["soglia"])
            K.choose(cs[2], "Sotto soglia (non soggetta)" if r["esito"] == "sotto" else "Sopra soglia")
    b.par_fill("Conclusione VRI-2.1", [f"NON soggetta a controllo DPR 151/2011 ({n['fonte_assoggettamento']}); "
                                        "la verifica è conservata agli atti con la planimetria quotata e il conteggio degli occupanti"])
    # VRI-2.2
    for _, t in K.find_tables(b.doc, "Verifica"):
        if len(t.rows) == 3 and "RTV" in K.ctext(t.rows[1].cells[0]):
            for i in (1, 2):
                cs = K.uniq_cells(t.rows[i])
                K.choose(cs[1], "No")
                K.set_cell(cs[2], "Nessuna indicata dal tecnico incaricato (verifica sugli elenchi delle RTV Sez. V e sulle regole tecniche pre-Codice)")
    b.par_fill("Conclusione VRI-2.2", ["verificato dal redattore sulla base dell'attività reale descritta in VRI-4"])
    # VRI-2.3
    req = {r["id"]: r for r in n["requisiti_allegato_I"]}
    for _, t in K.find_tables(b.doc, "Requisito (Allegato I, p.to 1, c.2)"):
        for i, key in enumerate(("C.a", "C.b", "C.c", "D", "RTV"), start=1):
            r = req[key]
            cs = K.uniq_cells(t.rows[i])
            K.tick(cs[2], "Soddisfatto")
            K.fill_tokens(cs[2], [f"{r['valore']} (soglia {r['soglia']})"])
    # VRI-4 ---------------------------------------------------------------------
    b.attivita(); b.locali(); b.affollamento(); b.sostanze(); b.qf_area()
    # VRI-6 aree rischio specifico
    for _, t in K.find_tables(b.doc, "Locale/Area"):
        hdr = [K.ctext(x) for x in K.uniq_cells(t.rows[0])]
        if len(hdr) == 3 and hdr[1].startswith("Criterio"):
            cs = K.uniq_cells(t.rows[1])
            K.set_cell(cs[0], "Intera attività")
            K.set_cell(cs[1], "Nessuno dei criteri a–h (V.1.1) soddisfatto sulla base dei dati: sostanze pericolose e lavorazioni pericolose assenti, qf ≤ 900 MJ/m²")
            K.choose(cs[2], "Nessuno")
    b.innesco()
    b.par_fill("Numero minimo di addetti antincendio", ["2 per turno di lavoro (minimo, a copertura di assenze)"])
    # VRI-9 ------------------------------------------------------------------------
    b.checklist()
    for _, t in K.find_tables(b.doc, "Misura"):
        if len(t.rows) == 9 and len(K.uniq_cells(t.rows[0])) == 4:
            for i in range(1, 9):
                cs = K.uniq_cells(t.rows[i])
                e = b.esito_misura(f"M.{i}")
                if e == "C":
                    K.choose(cs[2], "Conforme"); K.shade(cs[2], K.OK_FILL)
                elif e == "NC":
                    K.choose(cs[2], "NC"); K.shade(cs[2], K.NC_FILL)
    k = 0
    for p in b.doc.paragraphs:
        if p.text.strip().startswith("Soluzione adottata:"):
            k += 1
            if b.esito_misura(f"M.{k}") == "C":
                K.tick(p, "Conforme alle prescrizioni")
    b.azioni(); b.periodicita(); b.sottoscrizioni()
    pend = b.finalize()
    b.salva(out)
    return pend
