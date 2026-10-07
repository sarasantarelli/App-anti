"""Agente NORMATIVO: percorso di qualificazione (DM 3/9/2021 art. 2), assoggettamento DPR 151/2011,
requisiti Allegato I (basso rischio), scelta del template. Metodologia VRI: il DPR 151 è un binario PARALLELO,
non il punto di partenza."""
from __future__ import annotations
from ..models import Caso
from .. import regole as R

AGENTE = "Normativo"


def occupanti_totali(c: Caso) -> float:
    base = sum(float(c.get(k, 0) or 0) for k in ("occupanti_lavoratori", "occupanti_appaltatori", "occupanti_terzi"))
    return max(base, float(c.get("occupanti_picco", 0) or 0))


def qualifica(c: Caso) -> Caso:
    occ = occupanti_totali(c)
    sup = float(c.get("superficie_mq", 0) or 0)
    qmin, qmax = c.get("quota_min"), c.get("quota_max")
    tip = c.get("tipologia_attivita", []) or []
    qf = c.esito.get("rischio", {}).get("qf")

    scr = R.screening_dpr151({
        "occupanti": occ, "superficie": sup, "tipologie": tip, "posti_letto": c.get("posti_letto"),
        "kg_carta": c.get("kg_carta"), "kg_legno": c.get("kg_legno"), "kg_plastica": c.get("kg_plastica"),
        "kg_combustibili": sum(float(c.get(k, 0) or 0) for k in ("kg_carta", "kg_legno", "kg_plastica")),
        "litri_infiammabili": c.get("litri_infiammabili"), "kw_termico": c.get("kw_termico"), "quota_max": qmax})
    override = c.get("soggetta_dpr151")
    if override in (True, False, "si", "no", "Sì", "No"):
        soggetta = override in (True, "si", "Sì")
        fonte = "indicazione del tecnico"
    else:
        soggetta = any(r["esito"] == "SOPRA" for r in scr)
        fonte = "screening automatico sulle soglie dell'Allegato I (non esaustivo)"
        c.add(AGENTE, "attenzione",
              "L'assoggettamento al DPR 151/2011 è stato stimato con uno screening sulle principali voci: "
              "il professionista deve verificarlo sull'elenco completo dell'Allegato I (es. impianti, gas, ATEX, "
              "liquidi infiammabili, lavorazioni specifiche).", "DPR 151/2011 All. I")
    if "sostanze" in c.dati and any(s in (c.get("sostanze") or []) for s in ("esplosivi/ATEX", "gpl/gas")):
        c.add(AGENTE, "attenzione", "Rilevati gas/ATEX nei documenti: verificare voci specifiche dell'Allegato I DPR 151 (gas, depositi, ATEX).", "DPR 151/2011 All. I")

    rtv, rts = c.get("rtv_applicabile"), c.get("rt_settore")
    req = []
    def R_(id_, testo, soglia, valore, ok):
        req.append({"id": id_, "testo": testo, "soglia": soglia, "valore": valore, "ok": ok})
    R_("C.a", "Affollamento complessivo", "≤ 100 occupanti", f"{occ:g}", occ <= 100 if occ else None)
    R_("C.b", "Superficie lorda complessiva", "≤ 1.000 m²", f"{sup:g} m²", sup <= 1000 if sup else None)
    R_("C.c", "Quota dei piani", "tra -5 m e +24 m",
       f"da {qmin:g} m a {qmax:g} m" if qmin is not None and qmax is not None else "n.d.",
       (qmin >= -5 and qmax <= 24) if qmin is not None and qmax is not None else None)
    R_("C.d", "Materiali combustibili non in quantità significative", "qf ≤ 900 MJ/m² (soglia indicativa)",
       f"{qf:g} MJ/m²" if qf is not None else "n.d.", (qf <= 900) if qf is not None else None)
    ss = c.get("sostanze_significative")
    R_("C.e", "Assenza di sostanze/miscele pericolose in quantità significative", "vedi VRI-5/VRI-6",
       "assenti" if ss is False else ("presenti" if ss else "n.d."), (not ss) if ss is not None else None)
    lp = c.get("lavorazioni_pericolose")
    R_("C.f", "Assenza di lavorazioni pericolose ai fini dell'incendio", "vedi VRI-4/VRI-6",
       "assenti" if lp is False else ("presenti" if lp else "n.d."), (not lp) if lp is not None else None)
    R_("D", "Attività non soggetta a controllo DPR 151/2011", "coerenza con A", "non soggetta" if not soggetta else "SOGGETTA", not soggetta)
    R_("RTV", "Assenza di RTV del Codice / regola tecnica di settore", "DM 3/9/2021 art. 2", "nessuna" if not (rtv or rts) else (rtv or rts), not (rtv or rts))

    mancanti = [r for r in req if r["ok"] is None]
    for r in mancanti:
        c.add(AGENTE, "attenzione", f"Requisito {r['id']} «{r['testo']}» non verificabile: dato mancante. "
              "Trattato come NON soddisfatto (cautelativo) fino a conferma.", "DM 3/9/2021 All. I")
    tutti = all(r["ok"] is True for r in req)

    if soggetta and rtv:
        ramo, descr = "A", "RAMO A — attività soggetta con RTV del Codice applicabile"
    elif rts:
        ramo, descr = "B", "RAMO B — regola tecnica di settore pre-Codice"
    elif tutti:
        ramo, descr = "MINICODICE", "RAMO C — requisiti dell'Allegato I al DM 3/9/2021 TUTTI soddisfatti: si applica il Minicodice (basso rischio)"
    else:
        ramo, descr = "C", "RAMO C — RTO residuale (DM 3/8/2015 sez. G e S): almeno un requisito di basso rischio non soddisfatto"
    RTV_HINT = {"ufficio": "uffici", "commercio": "attività commerciali", "ricettivo": "attività ricettive turistico-alberghiere",
                "scuola": "attività scolastiche", "autorimessa": "autorimesse", "sanitario": "strutture sanitarie",
                "spettacolo/intrattenimento": "locali di trattenimento e pubblico spettacolo (V.15)"}
    hint = [RTV_HINT[t] for t in tip if t in RTV_HINT]
    if soggetta and hint and not rtv:
        c.add(AGENTE, "attenzione", "Per questa tipologia (" + ", ".join(hint) + ") il Codice prevede di norma una Regola Tecnica Verticale (Sezione V): "
              "indicare nel campo «RTV applicabile» quella pertinente alla voce di Allegato I, per passare al RAMO A.", "DM 3/9/2021 art. 2; Codice Sez. V")
    if soggetta and ramo in ("MINICODICE", "C"):
        c.add(AGENTE, "critico", "Attività soggetta ai controlli VVF senza RTV/RT indicata: richiede il professionista antincendio "
              "iscritto agli elenchi del Ministero dell'Interno (progetto, SCIA, asseverazione). La VRI non li sostituisce.", "DPR 151/2011; D.Lgs. 139/2006")

    if soggetta or ramo in ("A", "B"):
        template = "raccordo"
    elif ramo == "MINICODICE":
        template = "minicodice"
    else:
        template = "codice"

    basso = ramo == "MINICODICE"
    c.esito["normativo"] = {
        "occupanti": occ, "superficie": sup, "soggetta_dpr151": soggetta, "fonte_assoggettamento": fonte,
        "screening": scr, "requisiti_allegato_I": req, "ramo": ramo, "ramo_descrizione": descr,
        "template": template, "rischio_basso": basso,
        "formazione": R.formazione(basso, occ, speciale=soggetta and occ > 300),
    }
    c.log.append(f"Normativo: {descr}; soggetta DPR151={soggetta}; template={template}")
    return c
