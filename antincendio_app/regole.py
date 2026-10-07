"""Tabelle e regole di calcolo.

FONTE: i valori riportati sono quelli presenti nei template ufficiali dell'utente
(templates/VRI_Codice_Integrale_RTO_completa_2.docx e VRI_Minicodice_template_2.docx), che a loro volta
riproducono DM 3/8/2015 (Codice) e DM 3/9/2021. Ogni funzione cita la tabella. In caso di dubbio
prevale il testo ufficiale: l'agente di controllo segnala sempre i valori derivati da stime.
"""
from __future__ import annotations
import math, re

# ---------------------------------------------------------------- Rvita (Tab. G.3-1)
def rvita_str(docc: str, dalfa: int) -> str:
    return f"{docc}{dalfa}"

def rvita_ammesso(docc: str, dalfa: int) -> bool:
    """Combinazioni 'N.A.' della matrice G.3-1 (δα=4 non ammesso per B/C/E, δα≥3 non ammesso per D)."""
    if docc == "D":
        return dalfa <= 2
    if docc == "A":
        return True
    return dalfa <= 3

def gruppo_rvita(r: str) -> str:
    """Raggruppa Rvita per le tabelle di esodo/estintori."""
    d = re.match(r"(A|B|Ci{1,3}|C|D|E)(\d)", r)
    return r

def expand_rvita(spec: str) -> set[str]:
    """'A1, A2' / 'Cii1–Cii3' / 'D1, D2' -> insieme di profili."""
    out: set[str] = set()
    spec = spec.replace("–", "-").replace("—", "-")
    for part in re.split(r"[,;]| e ", spec):
        part = part.strip()
        m = re.match(r"^(A|B|Ci{1,3}|C|D|E)(\d)\s*-\s*(?:(A|B|Ci{1,3}|C|D|E))?(\d)$", part)
        if m:
            for k in range(int(m.group(2)), int(m.group(4)) + 1):
                out.add(f"{m.group(1)}{k}")
            continue
        m = re.match(r"^(A|B|Ci{1,3}|C|D|E)(\d)$", part)
        if m:
            out.add(part)
    return out

def rvita_in(r: str, insieme: set[str]) -> bool:
    if r in insieme:
        return True
    # 'C2' generico vale per Ci2/Cii2/Ciii2 (nota [2] matrice G.3-1)
    m = re.match(r"^(Ci{1,3})(\d)$", r)
    return bool(m and f"C{m.group(2)}" in insieme)

# ---------------------------------------------------------------- qf tabellare (UNI EN 1991-1-2 — template VRI-8.7)
QF_TAB = {  # destinazione: (medio, frattile 80%)
    "abitazione": (780, 948), "ospedale": (230, 280), "albergo": (310, 377),
    "biblioteca/archivio": (1500, 1824), "ufficio": (420, 511), "scuola": (285, 347),
    "commercio": (600, 730), "spettacolo": (300, 365), "trasporti": (100, 122),
}
TIPO_TO_QF = {"ufficio": "ufficio", "scuola": "scuola", "commercio": "commercio", "ricettivo": "albergo",
              "sanitario": "ospedale", "spettacolo/intrattenimento": "spettacolo"}

# potere calorifico (MJ/kg) per Percorso B — UNI EN 1991-1-2 App. E (valori orientativi, da verificare)
PCI = {"legno": 17.5, "carta": 17.0, "cartone": 17.0, "plastica": 40.0, "gomma": 40.0, "tessile": 19.0,
       "olio": 41.0, "gasolio": 43.0, "benzina": 44.0, "alcool": 27.0, "solvente": 30.0, "vernice": 25.0,
       "gpl": 46.0, "cibo": 17.0, "mobili": 17.5}

# ---------------------------------------------------------------- S.2 (Tab. S.2-6/7/8/3)
def delta_q1(A: float) -> float:
    for lim, v in ((500, 1.00), (1000, 1.20), (2500, 1.40), (5000, 1.60), (10000, 1.80)):
        if A < lim:
            return v
    return 2.00

DELTA_Q2 = {"I": 0.80, "II": 1.00, "III": 1.20}
DELTA_N = {"idranti_interni": ("δn1", 0.90), "idranti_int_est": ("δn2", 0.80),
           "sprinkler_idranti_int": ("δn3", 0.54), "altro_aut_idranti_int": ("δn4", 0.72),
           "sprinkler_idranti_int_est": ("δn5", 0.48), "altro_aut_idranti_int_est": ("δn6", 0.64),
           "gsa_ii_h24": ("δn7", 0.90), "fumi_iii": ("δn8", 0.90), "irai_iii": ("δn9", 0.85),
           "operativita_iv": ("δn10", 0.81)}

def classe_rei(qfd: float):
    for lim, c in ((200, "Nessun requisito"), (300, 15), (600, 45), (900, 60), (1200, 90), (1800, 120), (2400, 180)):
        if qfd <= lim:
            return c
    return 240

# ---------------------------------------------------------------- S.4 (Tab. S.4-15/18/25/27/28/29)
LCC = {"A1": (100, 45), "A2": (100, 30), "A3": (100, 15), "A4": (50, 10), "B1": (50, 25), "E1": (50, 25),
       "B2": (50, 20), "E2": (50, 20), "B3": (50, 15), "E3": (50, 15), "D1": (50, 20), "D2": (50, 15),
       "Cii1": (50, 20), "Ciii1": (50, 20), "Cii2": (50, 15), "Ciii2": (50, 15), "Cii3": (50, 10), "Ciii3": (50, 10)}
LES = {"A1": 70, "A2": 60, "A3": 45, "A4": 30, "B1": 60, "E1": 60, "B2": 50, "E2": 50, "B3": 40, "E3": 40,
       "D1": 30, "Cii1": 40, "Ciii1": 40, "Cii2": 30, "Ciii2": 30, "Cii3": 20, "Ciii3": 20, "D2": 20}
LU_ORIZ = {"A1": 3.40, "A2": 3.80, "A3": 4.60, "A4": 12.30, "B1": 3.60, "C1": 3.60, "E1": 3.60,
           "B2": 4.10, "C2": 4.10, "D1": 4.10, "E2": 4.10, "B3": 6.20, "C3": 6.20, "D2": 6.20, "E3": 6.20}
LU_VERT = {  # per numero di piani serviti: 1..5, 6+
    "A1": [4.00, 3.60, 3.25, 3.00, 2.75, 2.55], "A2": [4.55, 4.00, 3.60, 3.25, 3.00, 2.75],
    "A3": [5.50, 4.75, 4.20, 3.75, 3.35, 3.10], "B1": [4.25, 3.80, 3.40, 3.10, 2.85, 2.65],
    "B2": [4.90, 4.30, 3.80, 3.45, 3.15, 2.90], "B3": [7.30, 6.40, 5.70, 5.15, 4.70, 4.30],
    "A4": [14.60, 11.40, 9.35, 7.95, 6.90, 6.10]}

def _gen(r: str) -> str:
    """Ci2/Cii2/Ciii2 -> C2 (tabelle LU)."""
    return re.sub(r"^Ci{1,3}(\d)$", r"C\1", r)

def _norm_ci(r: str) -> str:
    return r

def lu_oriz(r: str):
    g = _gen(r)
    return LU_ORIZ.get(g)

def lu_vert(r: str, piani: int):
    g = _gen(r)
    key = {"C1": "B1", "E1": "B1", "C2": "B2", "D1": "B2", "E2": "B2", "C3": "B3", "D2": "B3", "E3": "B3"}.get(g, g)
    row = LU_VERT.get(key)
    return row[min(max(piani, 1), 6) - 1] if row else None

def largh_min_assoluta(occ: int) -> int:
    return 1200 if occ > 1000 else (1000 if occ > 300 else 900)

def uscite_minime(occ: float, rvita: str, densita: float, lcc_ok: bool = True) -> int:
    if occ > 500:
        return 3
    if rvita[:1] == "B" and densita > 0.4 and occ > 150:
        return 2
    if occ > 50:
        return 2
    return 1 if lcc_ok else 2

# ---------------------------------------------------------------- S.6 (Tab. S.6-5/6)
ESTINTORI_A = [({"A1", "A2"}, 40, 13), ({"A3", "B1", "B2", "C1", "C2", "D1", "D2", "E1", "E2"}, 30, 21),
               ({"A4", "B3", "C3", "E3"}, 20, 27)]

def estintori_a(rvita: str, sup: float, piani: int = 1):
    g = _gen(rvita)
    for ins, d, cap in ESTINTORI_A:
        if g in ins:
            n_geo = math.ceil(sup / (math.pi * d * d))
            return {"dist_max": d, "cap_A": cap, "n_min": max(piani, n_geo)}
    return {"dist_max": 30, "cap_A": 21, "n_min": max(piani, math.ceil(sup / (math.pi * 900)))}

def estintori_b(litri: float):
    if litri <= 0: return None
    if litri <= 50: return {"cap_B": 70, "n": 1}
    if litri <= 100: return {"cap_B": 89, "n": 2}
    if litri < 200: return {"cap_B": 113, "n": 3, "alt": "144 B x 2"}
    return {"cap_B": 233, "n": 3, "nota": "≥3, definire con la valutazione del rischio"}

# ---------------------------------------------------------------- formazione (template VRI-10)
def formazione(basso: bool, occupanti: float, speciale: bool = False):
    if basso:
        return {"livello": 1, "ore": 4, "agg": "—"}
    if occupanti > 300 or speciale:
        return {"livello": 3, "ore": 16, "agg": "aggiornamento come da Accordo Stato-Regioni vigente"}
    return {"livello": 2, "ore": 8, "agg": "aggiornamento quinquennale di 4 ore"}

# ---------------------------------------------------------------- DPR 151/2011 — screening (da verificare su Allegato I)
def screening_dpr151(c: dict) -> list[dict]:
    """c: occupanti, superficie, tipologie, posti_letto, kg_carta, kg_legno, kg_plastica, litri_infiammabili, kw_termico, quota_max"""
    r = []
    occ, sup = c.get("occupanti", 0) or 0, c.get("superficie", 0) or 0
    tip = set(c.get("tipologie", []))
    def add(n, d, soglia, val, sopra):
        r.append({"voce": n, "descrizione": d, "soglia": soglia, "valore": val, "esito": "SOPRA" if sopra else "sotto"})
    if "spettacolo/intrattenimento" in tip:
        add(65, "Locali di spettacolo e trattenimento", ">100 persone o >200 m²", f"{occ:g} p / {sup:g} m²", occ > 100 or sup > 200)
    if "ricettivo" in tip:
        add(66, "Strutture ricettive turistico-alberghiere", ">25 posti letto", c.get("posti_letto", "n.d."), (c.get("posti_letto") or 0) > 25)
    if "scuola" in tip:
        add(67, "Scuole di ogni ordine, grado e tipo", ">100 persone presenti", f"{occ:g}", occ > 100)
    if "sanitario" in tip:
        add(68, "Strutture sanitarie", ">25 posti letto; ambulatori >500 m²", f"{sup:g} m²", sup > 500 or (c.get("posti_letto") or 0) > 25)
    if "commercio" in tip:
        add(69, "Locali adibiti ad esposizione e/o vendita", "superficie lorda >400 m²", f"{sup:g} m²", sup > 400)
    if "deposito/magazzino" in tip:
        add(70, "Locali adibiti a depositi", ">1000 m² con merci combustibili >5.000 kg", f"{sup:g} m²", sup > 1000 and (c.get("kg_combustibili") or 0) > 5000)
    if occ > 0 and ({"ufficio", "officina/produzione"} & tip):
        add(71, "Aziende ed uffici", ">300 persone", f"{occ:g}", occ > 300)
    if c.get("kw_termico"):
        add(74, "Impianti per la produzione di calore", ">116 kW", f"{c['kw_termico']} kW", c["kw_termico"] > 116)
    if "autorimessa" in tip:
        add(75, "Autorimesse", ">300 m² o >9 autoveicoli", f"{sup:g} m²", sup > 300)
    if c.get("kg_carta"):
        add(34, "Depositi di carta, cartone, archivi", ">5.000 kg", f"{c['kg_carta']} kg", c["kg_carta"] > 5000)
    if c.get("kg_legno"):
        add(36, "Depositi di legnami", ">50.000 kg", f"{c['kg_legno']} kg", c["kg_legno"] > 50000)
    if c.get("kg_plastica"):
        add(43, "Depositi di gomma, materie plastiche", ">5.000 kg", f"{c['kg_plastica']} kg", c["kg_plastica"] > 5000)
    if c.get("litri_infiammabili"):
        add(12, "Depositi/rivendite liquidi infiammabili e/o combustibili", ">1 m³", f"{c['litri_infiammabili']} L", c["litri_infiammabili"] > 1000)
    if (c.get("quota_max") or 0) > 24:
        add("77", "Edifici civili: altezza antincendio", ">24 m", f"{c['quota_max']} m", True)
    return r
