"""Agente RISCHIO: profili Rvita / Rbeni / Rambiente e carico d'incendio qf,d (DM 3/8/2015 cap. G.3, S.2)."""
from __future__ import annotations
import re
from ..models import Caso
from .. import regole as R

AGENTE = "Rischio"


def _qf(c: Caso):
    v = c.get("qf_mj_m2")
    sup = float(c.get("superficie_mq", 0) or 0)
    if v not in (None, ""):
        return float(v), "dato fornito/rilevato", "dato"
    tip = c.get("tipologia_attivita", []) or []
    for t in tip:
        k = R.TIPO_TO_QF.get(t)
        if k:
            med, fr = R.QF_TAB[k]
            return float(fr), f"Percorso A — valore tabellare «{k}», frattile 80% (UNI EN 1991-1-2)", "tabellare"
    # Percorso B da materiali con quantità
    tot, righe = 0.0, []
    for s in c.get("sostanze_dettaglio", []) or []:
        try:
            q = float(str(s.get("quantita", "")).replace(",", "."))
        except ValueError:
            continue
        if (s.get("unita") or "kg").lower().startswith("l") and False:
            pass
        nome = (s.get("nome") or "").lower()
        h = next((v for k, v in R.PCI.items() if k in nome), None)
        if h:
            tot += q * h; righe.append(f"{s.get('nome')}: {q:g} × {h:g}")
    if tot and sup:
        return tot / sup, "Percorso B — Σ(massa × potere calorifico)/A: " + "; ".join(righe), "analitico"
    return None, "non determinabile", "n.d."


def profili(c: Caso) -> Caso:
    c.findings = [f for f in c.findings if f.agente != AGENTE]
    tip = c.get("tipologia_attivita", []) or []
    sost = set(c.get("sostanze", []) or [])
    pubblico = bool(c.get("aperta_pubblico")) or float(c.get("occupanti_terzi", 0) or 0) > 0
    # δocc ------------------------------------------------------------
    if "ricettivo" in tip:
        docc, mot = "Ciii", "occupanti possibilmente addormentati, gestione di breve durata (ricettivo)"
    elif "sanitario" in tip and float(c.get("posti_letto", 0) or 0) > 0:
        docc, mot = "D", "occupanti che ricevono cure mediche con degenza"
    elif pubblico:
        docc, mot = "B", "occupanti in veglia NON familiari con i luoghi (presenza di pubblico/terzi)"
    else:
        docc, mot = "A", "occupanti in veglia familiari con i luoghi (solo lavoratori)"
    # qf ------------------------------------------------------------------
    qf, qf_fonte, qf_tipo = _qf(c)
    # δα (cautelativo, Tab. G.3-2) ---------------------------------------------
    if sost & {"liquidi infiammabili", "gpl/gas", "polveri", "esplosivi/ATEX"} and (c.get("sostanze_significative") or "esplosivi/ATEX" in sost):
        dalfa, dm = 4, "liquidi/gas infiammabili, polveri combustibili o ATEX in quantità significativa (Tab. G.3-2: δα=4)"
    elif sost & {"materie plastiche/gomma", "tessili", "batterie/litio"}:
        dalfa, dm = 3, "plastici/tessili sintetici/apparecchiature elettriche o batterie (Tab. G.3-2: δα=3)"
    elif qf is not None and qf <= 200:
        dalfa, dm = 1, "qf ≤ 200 MJ/m² (Tab. G.3-2: δα=1)"
    elif qf is None:
        dalfa, dm = 3, "qf non determinato: scelta cautelativa (in assenza di calcolo si sceglie il valore più alto ragionevole)"
        c.add(AGENTE, "attenzione", "Carico d'incendio non determinabile: δα assunto cautelativamente = 3. Inserire qf o i materiali.", "Codice G.3.3")
    else:
        dalfa, dm = 2, "materiali con contributo moderato all'incendio (Tab. G.3-2: δα=2)"
    ov = c.get("dalfa_override")
    if ov:
        dalfa, dm = int(ov), "valore imposto dal tecnico"
    nota = ""
    if not R.rvita_ammesso(docc, dalfa):
        old = dalfa
        dalfa = 2 if docc == "D" else 3
        nota = (f"La combinazione {docc}{old} è «N.A.» nella matrice G.3-1: adottato δα={dalfa} (nota [1]: "
                "riducibile se l'attività è servita da controllo dell'incendio/rivelazione adeguati — da motivare).")
        c.add(AGENTE, "attenzione", nota, "Codice Tab. G.3-1 nota [1]")
    rvita = R.rvita_str(docc, dalfa)
    if c.get("rvita_override"):
        rvita = str(c.get("rvita_override"))
    # Rbeni / Rambiente ------------------------------------------------------
    vinc, strat = bool(c.get("vincolata")), bool(c.get("strategica"))
    rbeni = {(False, False): 1, (True, False): 2, (False, True): 3, (True, True): 4}[(vinc, strat)]
    civile = bool(set(tip) & {"sanitario", "scuola", "ricettivo"})
    ric = bool(c.get("ricettori_sensibili"))
    autom = False
    rambiente = [("Ambiti protetti da impianti automatici di completa estinzione", autom),
                 ("Attività civile (strutture sanitarie, scolastiche, alberghiere)", civile),
                 ("Ricettori sensibili esterni / materiali D.Lgs. 152/2006 rilevanti", ric)]
    ramb_sign = any(v for _, v in rambiente)
    # qf,d (S.2.9) ----------------------------------------------------------------
    sup = float(c.get("superficie_mq", 0) or 0)
    sup_comp = float(c.get("sup_compartimento_max", 0) or 0) or sup
    qfd = None
    if qf is not None and sup_comp:
        dq1 = R.delta_q1(sup_comp)
        cl = "III" if (dalfa == 4 or c.get("lavorazioni_pericolose") or c.get("sostanze_significative")) else ("I" if dalfa == 1 else "II")
        dq2 = R.DELTA_Q2[cl]
        sdn = 1.0
        qfd = dq1 * dq2 * sdn * qf
        qfd_info = {"dq1": dq1, "classe_dq2": cl, "dq2": dq2, "sdn": sdn, "qf": qf, "qfd": qfd, "rei": R.classe_rei(qfd), "sup_comp": sup_comp}
    else:
        qfd_info = None
    c.esito["rischio"] = {
        "docc": docc, "docc_motivo": mot, "dalfa": dalfa, "dalfa_motivo": dm, "rvita": rvita, "rvita_nota": nota,
        "rbeni": rbeni, "vincolata": vinc, "strategica": strat,
        "rambiente_condizioni": rambiente, "rambiente_significativo": ramb_sign,
        "qf": qf, "qf_fonte": qf_fonte, "qf_tipo": qf_tipo, "qfd": qfd_info,
    }
    if qf_tipo == "tabellare":
        c.add(AGENTE, "info", f"qf stimato con {qf_fonte}: sostituire con rilievo dei materiali se l'attività si discosta dal caso medio.", "Codice S.2.9 (Percorso A)")
    c.log.append(f"Rischio: Rvita={rvita}, Rbeni={rbeni}, Rambiente={'significativo' if ramb_sign else 'non significativo'}, qf={qf}")
    return c
