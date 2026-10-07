"""Agente STRATEGIA / MISURE: dal profilo di rischio alle misure S.1–S.10 con livelli di prestazione
(criteri letti dal template), dimensionamento di esodo ed estintori (Tab. S.4 e S.6 del Codice)."""
from __future__ import annotations
import math
from pathlib import Path
import docx
from ..models import Caso
from .. import regole as R
from ..criteri import Ctx, parse_criteri, attribuisci
from .normativo import occupanti_totali

AGENTE = "Strategia"
TEMPLATE_CODICE = Path(__file__).resolve().parents[2] / "templates" / "VRI_Codice_Integrale_RTO_completa_2.docx"
NOMI = {1: "Reazione al fuoco", 2: "Resistenza al fuoco", 3: "Compartimentazione", 4: "Esodo", 5: "Gestione sicurezza antincendio",
        6: "Controllo dell'incendio", 7: "Rivelazione e allarme", 8: "Controllo fumi e calore", 9: "Operatività antincendio",
        10: "Sicurezza impianti tecnologici"}


def contesto(c: Caso) -> Ctx:
    r = c.esito["rischio"]; n = c.esito["normativo"]
    sup = float(c.get("superficie_mq", 0) or 0)
    return Ctx(rvita=r["rvita"], rbeni=r["rbeni"], rambiente_signif=r["rambiente_significativo"], qf=r["qf"],
               sup_comp=float(c.get("sup_compartimento_max", 0) or 0) or sup, occupanti=n["occupanti"], superficie=sup,
               quota_min=c.get("quota_min"), quota_max=c.get("quota_max"),
               aperta_pubblico=bool(c.get("aperta_pubblico")) or float(c.get("occupanti_terzi", 0) or 0) > 0, disabili_prevalenti=bool(c.get("disabili_prevalenti")),
               sostanze_significative=c.get("sostanze_significative"), lavorazioni_pericolose=c.get("lavorazioni_pericolose"),
               posti_letto=float(c.get("posti_letto", 0) or 0), soggetta_dpr151=n["soggetta_dpr151"],
               compartimentata=c.get("compartimentata"), un_responsabile=c.get("un_responsabile", True),
               presenza_occupanti=True)


def s1_livello(rvita: str) -> tuple[str, str]:
    """Tab. S.1-2 (riassunta nel template): vie d'esodo / altri locali in funzione di Rvita."""
    g = rvita[0]
    if rvita[:2] == "Ci" or g == "C":
        vie, altri = "III", "II"
    elif g == "A":
        vie, altri = "I", "I"
    elif rvita == "B1":
        vie, altri = "II", "II"
    elif g == "D":
        vie, altri = "IV", "III"
    else:   # B2,B3,E
        vie, altri = "III", "II"
    return vie, altri


def strategia(c: Caso) -> Caso:
    ctx = contesto(c)
    ramo = c.esito["normativo"]["ramo"]
    out = {}
    if ramo == "MINICODICE":
        c.esito["strategia"] = {"modo": "minicodice", "nota": "Allegato I DM 3/9/2021: 8 misure prescrittive, nessun livello di prestazione."}
    else:
        crit = parse_criteri(docx.Document(str(TEMPLATE_CODICE)))
        for n in range(1, 11):
            if n == 1:
                vie, altri = s1_livello(ctx.rvita)
                out[n] = {"livello": vie, "dettaglio": f"vie d'esodo: livello {vie}; altri locali: livello {altri}", "dubbi": [], "conds": {}}
                continue
            tabs = crit.get(n) or []
            if not tabs:
                continue
            liv, det, dubbi = attribuisci(tabs[0], ctx)
            out[n] = {"livello": liv, "dettaglio": "", "dubbi": dubbi, "conds": {f"{a}|{b}": v for (a, b), v in det.items()}}
        c.esito["strategia"] = {"modo": "codice", "misure": out}
        incerte = []
        for n, o in out.items():
            if o["dubbi"]:
                incerte.append(f"S.{n} = {o['livello']} ({len(o['dubbi'])} condizioni da confermare)")
        if incerte:
            c.add(AGENTE, "info", "Livelli di prestazione proposti in via cautelativa; da confermare in sopralluogo (dati mancanti o giudizio del valutatore): "
                  + "; ".join(incerte) + ". Il dettaglio per condizione è nelle tabelle dei criteri del documento.", "Codice Tab. S.x-2")
    c.esito["dimensionamento"] = dimensiona(c, ctx)
    c.log.append("Strategia: livelli " + ", ".join(f"S.{n}={o['livello']}" for n, o in out.items()) if out else "Strategia: Minicodice (prescrittiva)")
    return c


def dimensiona(c: Caso, ctx: Ctx) -> dict:
    rv = ctx.rvita
    occ, sup = ctx.occupanti, ctx.superficie
    piani = int(c.get("piani_n", 1) or 1)
    dens = (occ / sup) if sup else 0
    g = R._gen(rv)
    d = {"rvita": rv, "occupanti": occ, "densita": round(dens, 3)}
    lcc = R.LCC.get(rv) or R.LCC.get(g)
    les = R.LES.get(rv) or R.LES.get(g)
    d["lcc_max"] = lcc[1] if lcc else None
    d["lcc_max_occ"] = lcc[0] if lcc else None
    d["les_max"] = les
    d["uscite_min"] = R.uscite_minime(occ, rv, dens, lcc_ok=True)
    lu = R.lu_oriz(rv)
    d["lu_oriz"] = lu
    if lu:
        d["lo_calcolata_mm"] = round(lu * occ)
        d["largh_min_mm"] = R.largh_min_assoluta(int(occ))
        d["lo_richiesta_mm"] = max(d["lo_calcolata_mm"], d["largh_min_mm"])
    if piani > 1:
        lv = R.lu_vert(rv, piani)
        d["lu_vert"] = lv
        d["lv_calcolata_mm"] = round(lv * occ) if lv else None
    d["estintori_A"] = R.estintori_a(rv, sup, piani)
    lit = float(c.get("litri_infiammabili", 0) or 0)
    d["estintori_B"] = R.estintori_b(lit)
    d["classe_F"] = bool(c.get("cucina_cottura"))
    # Minicodice (Allegato I): 1 estintore ogni 500 m² (o frazione), distanza max 30 m, >=21A/55B
    d["minicodice_estintori_n"] = max(piani, math.ceil(sup / 500)) if sup else None
    return d


def verifiche_esodo(c: Caso) -> list[dict]:
    """Confronta i dati RILEVATI in sopralluogo con i minimi calcolati (S.4). Ritorna esiti OK/NC e azioni."""
    d = c.esito["dimensionamento"]
    out = []
    def chk(chiave, label, ok, msg, azione):
        out.append({"chiave": chiave, "voce": label, "ok": ok, "msg": msg, "azione": azione})
    nus = c.get("n_uscite")
    if nus not in (None, ""):
        ok = float(nus) >= d["uscite_min"]
        chk("uscite", "Numero uscite", ok, f"presenti {float(nus):g}, richieste ≥ {d['uscite_min']}",
            f"Realizzare/rendere disponibili almeno {d['uscite_min']} uscite indipendenti (presenti {float(nus):g})")
    if c.get("lcc_misurata") not in (None, "") and d.get("lcc_max"):
        ok = float(c.get("lcc_misurata")) <= d["lcc_max"]
        chk("lcc", "Corridoio cieco", ok, f"misurato {float(c.get('lcc_misurata')):g} m, massimo {d['lcc_max']} m (Rvita {d['rvita']})",
            f"Ridurre il corridoio cieco entro {d['lcc_max']} m o prevedere ulteriore uscita")
    if c.get("les_misurata") not in (None, "") and d.get("les_max"):
        ok = float(c.get("les_misurata")) <= d["les_max"]
        chk("les", "Lunghezza di esodo", ok, f"misurata {float(c.get('les_misurata')):g} m, massima {d['les_max']} m (Rvita {d['rvita']})",
            f"Ridurre la lunghezza d'esodo entro {d['les_max']} m (nuove uscite/percorsi)")
    if c.get("largh_installata_mm") not in (None, "") and d.get("lo_richiesta_mm"):
        ok = float(c.get("largh_installata_mm")) >= d["lo_richiesta_mm"]
        chk("largh", "Larghezza vie di esodo", ok, f"installata {float(c.get('largh_installata_mm')):g} mm, richiesta ≥ {d['lo_richiesta_mm']} mm",
            f"Adeguare la larghezza delle vie/uscite ad almeno {d['lo_richiesta_mm']} mm")
    na = c.get("n_estintori")
    if na not in (None, ""):
        ea = d["estintori_A"]
        ok = float(na) >= ea["n_min"]
        chk("estintori", "Estintori classe A", ok, f"presenti {float(na):g}, minimo teorico {ea['n_min']} (distanza max {ea['dist_max']} m, ≥ {ea['cap_A']} A)",
            f"Integrare gli estintori portatili a ≥ {ea['n_min']} (≥ {ea['cap_A']} A) rispettando la distanza massima di {ea['dist_max']} m")
    return out
