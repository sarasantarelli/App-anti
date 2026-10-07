"""Compila il template Piano di Emergenza (DM 2/9/2021, art. 43 D.Lgs. 81/08, DM 3/8/2015 cap. S.5)."""
from __future__ import annotations
import re
from datetime import date
from pathlib import Path
from .. import docxkit as K
from .base import Base, nz, fmt_num

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "Piano_di_Emergenza_standalone_v12_1.docx"


def _gsa_livello(caso) -> str:
    st = caso.esito.get("strategia", {})
    if st.get("modo") == "codice":
        return st["misure"].get(5, {}).get("livello", "I")
    return "I"


def compila(caso, out, tieni_guide=False):
    b = Base(TEMPLATE, caso, [], {}, tieni_guide)
    n, r, dim = caso.esito["normativo"], caso.esito["rischio"], caso.esito["dimensionamento"]
    b.cover(); b.anagrafica()
    b.label_fill("FIGURE DI RIFERIMENTO", {"Medico competente": b.d("medico_competente")})
    # revisione "Rev. 0 del"
    b.label_fill("DOCUMENTO", {"Revisione n.": b.revisione_str()})
    b.label_fill("RECAPITI OPERATIVI", {
        "Recapiti unità": " / ".join(x for x in (b.d("tel_fisso"), b.d("tel_mobile"), b.d("email_azienda")) if x) or None,
        "ASL / ATS": b.d("asl_ats"), "RSPP (riferimento": f"{b.d('rspp')} — {b.d('rspp_tel')}" if b.d("rspp") and b.d("rspp_tel") else None,
        "Coordinatore emergenza (turno diurno)": f"{b.d('coord_diurno')} → cfr. PE-5.3" if b.d("coord_diurno") else None,
        "Coordinatore emergenza (turno notturno": f"{b.d('coord_notturno')} → cfr. PE-5.3" if b.d("coord_notturno") else None})
    for _, t in K.find_tables(b.doc, "PREVENZIONE INCENDI"):
        K.choose(K.uniq_cells(t.rows[1])[1], "Sì" if n["soggetta_dpr151"] else "No")
        c2 = K.uniq_cells(t.rows[2])[1]
        if n["soggetta_dpr151"]:
            if b.d("scadenza_rinnovo"):
                K.tick(c2, "Sì"); K.fill_tokens(c2, [str(b.d("scadenza_rinnovo"))])
        else:
            K.set_cell(c2, "N.A. — attività non soggetta a controllo VVF")
    liv = _gsa_livello(caso)
    for _, t in K.find_tables(b.doc, "GESTIONE SICUREZZA ANTINCENDIO"):
        K.choose(K.uniq_cells(t.rows[1])[1], {"I": "I — Base", "II": "II — Avanzato", "III": "III — Avanzato"}.get(liv, "I — Base"))
        mot = ("Minicodice (basso rischio): GSA di livello I (Allegato I DM 3/9/2021, M.3)" if n["ramo"] == "MINICODICE" else
               f"Rvita {r['rvita']}, Rbeni {r['rbeni']}, affollamento {int(n['occupanti'])}, sostanze pericolose: "
               f"{'sì' if b.d('sostanze_significative') else 'no'} (criteri Tab. S.5-2)")
        K.set_cell(K.uniq_cells(t.rows[2])[1], mot)
        sg = str(b.d("sistema_gestione") or "").lower()
        if sg:
            for key, lab in (("45001", "ISO 45001"), ("inail", "UNI-INAIL"), ("231", "MOG"), ("nessun", "Nessuno")):
                if key in sg:
                    K.tick(K.uniq_cells(t.rows[3])[1], lab)
    # addetti (tabella PE-5.3 e allegato)
    add = b.d("addetti") or []
    for _, t in K.find_tables(b.doc, "Turno / Orario") + K.find_tables(b.doc, "Nominativo"):
        hdr = [K.ctext(x) for x in K.uniq_cells(t.rows[0])]
        order = (0, 1) if hdr[0].startswith("Turno") else (1, 0)
        for i, a in enumerate(add, start=1):
            if i >= len(t.rows):
                K.clone_row(t, len(t.rows) - 1)
            cs = K.uniq_cells(t.rows[i])
            vals = (a.get("turno", ""), a.get("nome", ""))
            K.set_cell(cs[order[0]], vals[0] if order[0] == 0 else a.get("nome", ""))
            K.set_cell(cs[order[1]], vals[1] if order[1] == 1 else a.get("turno", ""))
            for col, key in ((2, "coord"), (3, "ai"), (4, "ps"), (5, "ge"), (6, "as")):
                if a.get(key):
                    K.set_cell(cs[col], "☒")
            if a.get("tel"):
                K.set_cell(cs[7], a["tel"])
    if not add:
        caso.add("PE", "attenzione", "Nessun addetto designato indicato: la tabella PE-5.3 (art. 4 DM 2/9/2021) resta da compilare con i nominativi.", "DM 2/9/2021 art. 4")
    # numeri utili
    nums = {"Centro Antiveleni": "tel_antiveleni", "Centro Antiustioni": "tel_antiustioni", "Azienda distributrice gas": "tel_gas",
            "Azienda distributrice elettricità": "tel_elettricita", "Azienda distributrice acqua": "tel_acqua",
            "Impiantista elettrico": "tel_impiantista", "Protezione Civile": "tel_protezione_civile"}
    for _, t in K.find_tables(b.doc, "Ente / Servizio"):
        for rw in t.rows[1:]:
            cs = K.uniq_cells(rw)
            lab = K.ctext(cs[0])
            for k, key in nums.items():
                if lab.startswith(k) and b.d(key):
                    K.set_cell(cs[1], str(b.d(key)))
            if lab.startswith("Gestore della struttura") and b.d("tel_referente"):
                K.set_cell(cs[1], str(b.d("tel_referente"))); K.set_cell(cs[2], "")
    # sequenza di disattivazione: ubicazioni
    ub = {"INTERCETTAZIONE DEL GAS": "ub_gas", "SEZIONAMENTO ENERGIA": "ub_elettrico", "SEZIONAMENTO VENTILAZIONE": "ub_ventilazione", "INTERCETTAZIONE ACQUA": "ub_acqua"}
    for t in b.doc.tables:
        for rw in t.rows:
            for cell in K.uniq_cells(rw):
                tx = K.ctext(cell)
                for k, key in ub.items():
                    if tx.startswith(k) and "___" in tx and b.d(key):
                        K.fill_tokens(cell, [str(b.d(key))])
                if tx.startswith("«Sono [nome cognome]"):
                    K.fill_tokens(cell, [None, str(b.d("ragione_sociale") or "[ragione sociale]") if b.d("ragione_sociale") else None,
                                         str(b.d("indirizzo")) if b.d("indirizzo") else None])
    # IRAI
    for _, t in K.find_tables(b.doc, "IRAI presente"):
        irai = b.d("irai_presente")
        if irai is not None:
            K.choose(K.uniq_cells(t.rows[0])[1], "Sì" if irai else "No")
        for rw, key in ((1, "irai_ubicazione"), (4, "irai_ditta")):
            if rw < len(t.rows) and b.d(key):
                K.set_cell(K.uniq_cells(t.rows[rw])[1], str(b.d(key)))
    # PE-9.1 dati edificio
    q = r.get("qfd")
    esito_pres = {
        "Profilo di rischio vita": f"{r['rvita']} — (δocc = {r['docc']} × δα = {r['dalfa']})",
        "Profilo Rbeni": f"{r['rbeni']} — {'vincolata' if r['vincolata'] else 'non vincolata'}, {'strategica' if r['strategica'] else 'non strategica'}",
        "Profilo Rambiente": f"{1 if r['rambiente_significativo'] else 0} — {'significativo' if r['rambiente_significativo'] else 'non significativo'}",
        "Carico di incendio": (f"{q['qfd']:.0f} MJ/m² — Classe REI richiesta: {'nessun requisito' if isinstance(q['rei'], str) else 'REI ' + str(q['rei'])}" if q else None),
        "N. piani": (f"{int(float(b.d('piani_n')))} fuori terra + {int(float(b.d('n_interrati', 0) or 0))} interrati — Quota PT: 0 m — Altezza antincendio: {b.d('altezza_antincendio') or 'n.d.'} m"
                     if b.d("piani_n") else None),
        "Vie di esodo": f"N. uscite: {fmt_num(b.d('n_uscite')) or '[N]'} — Larghezza minima richiesta: {dim.get('lo_richiesta_mm', '—')} mm — Les max: {dim.get('les_max', '—')} m — Lcc max: {dim.get('lcc_max', '—')} m",
        "Punto di raccolta principale": b.d("punto_raccolta"), "Punto di raccolta alternativo": b.d("punto_raccolta_alt") or "N.A."}
    ea = dim["estintori_A"]
    esito_pres["Impianti di estinzione"] = (f"Estintori n. {fmt_num(b.d('n_estintori')) or '[X]'} (min. {ea['n_min']}, ≥ {ea['cap_A']} A) — Idranti n. {fmt_num(b.d('n_idranti')) or 'N.A.'} — Sprinkler: {'Sì' if b.d('sprinkler') else 'No'}")
    if b.d("illuminazione_autonomia_min"):
        esito_pres["Illuminazione di emergenza"] = f"Conforme EN 1838 — autonomia: ≥ {fmt_num(b.d('illuminazione_autonomia_min'))} min"
    if b.d("irai_presente") is False:
        esito_pres["Rivelazione e allarme"] = "Non presente — allarme per sorveglianza degli occupanti (UNI 9795 N.A.)"
    for _, t in K.find_tables(b.doc, "Profilo di rischio vita"):
        for rw in t.rows:
            cs = K.uniq_cells(rw)
            lab = K.ctext(cs[0])
            for k, v in esito_pres.items():
                if lab.startswith(k) and v:
                    K.set_cell(cs[1], v)
    # PE-9.2 aree
    locali = b.d("locali") or [{"nome": "Intera attività", "mq": b.d("superficie_mq"), "dest": ", ".join(b.d("tipologia_attivita", []) or [])}]
    for _, t in K.find_tables(b.doc, "[Area produzione"):
        K.ensure_rows(t, 0, len(locali))
        for i, l in enumerate(locali):
            cs = K.uniq_cells(t.rows[i])
            K.set_cell(cs[0], str(l.get("nome")))
            K.set_cell(cs[1], str(l.get("dest") or "rischio ordinario") + (f" — qf,d {q['qfd']:.0f} MJ/m²" if q else ""))
            K.set_cell(cs[2], str(int(float(l.get("occ", 0)))) if l.get("occ") else fmt_num(n["occupanti"]) if len(locali) == 1 else "[N.]")
            K.set_cell(cs[4], f"Est. n. ≥ {ea['n_min']}, ≥ {ea['cap_A']} A" if len(locali) == 1 else "[Est. n., tipo]")
        for j in range(len(t.rows) - 1, len(locali) - 1, -1):
            if K.has_pending(t.rows[j].cells[0]) and j >= len(locali):
                K.delete_row(t, j)
    b.finalize_pe = True
    pend = b.finalize()
    b.salva(out)
    return pend
