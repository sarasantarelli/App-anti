"""Estrazione delle check-list DAI template e generazione delle azioni correttive.

Le voci di verifica (Allegato I del Minicodice, check-list S.1–S.10 del Codice) non sono duplicate nel codice:
sono lette dal template. L'esito (C / NC / N.A.) deriva dal sopralluogo; l'app precompila solo ciò che i documenti
consentono di sostenere e lo dichiara come «da documentazione — verificare in sito».
"""
from __future__ import annotations
import hashlib, re
from dataclasses import dataclass
from docx.table import Table
from . import docxkit as K


@dataclass
class Voce:
    id: str
    template: str
    tab: int
    riga: int
    misura: str       # M.1 / S.4 ...
    gruppo: str
    testo: str
    applic: str       # Sempre / qf>900
    fmt: str          # 'CNC' (Minicodice) | 'SNA' (Codice)


def _id(tpl, testo, used):
    h = hashlib.sha1(re.sub(r"\s+", " ", testo).strip().lower().encode()).hexdigest()[:8]
    base = f"{tpl}:{h}"
    n, i = base, 1
    while n in used:
        i += 1; n = f"{base}.{i}"
    used.add(n)
    return n


def estrai(doc, tpl: str) -> list[Voce]:
    voci, used, misura, ti = [], set(), "", -1
    for b in K.blocks(doc):
        if not isinstance(b, Table):
            m = re.match(r"^\s*((?:M|S)\.\d+(?:\s*[–,-]\s*(?:S\.)?\d+)?)\s*—", b.text)
            if m:
                misura = re.sub(r"\s+", "", m.group(1))
            continue
        ti += 1
        hdr = [K.ctext(c) for c in K.uniq_cells(b.rows[0])]
        fmt = None
        if hdr and hdr[0].startswith("Prescrizione / punto di verifica") and len(hdr) >= 5:
            fmt = "CNC"
        elif hdr and hdr[0].startswith("Requisito da verificare") and len(hdr) >= 5:
            fmt = "SNA"
        elif hdr and hdr[0].startswith("Misura / punto di verifica") and len(hdr) == 4:
            fmt = "RACC"
        if not fmt:
            continue
        gruppo = ""
        for ri, row in enumerate(b.rows[1:], start=1):
            cs = K.uniq_cells(row)
            if len(cs) == 1:
                gruppo = K.ctext(cs[0]); continue
            testo = K.ctext(cs[0]).replace("\n", " / ")
            applic = K.ctext(cs[1]) if fmt == "CNC" else "Sempre"
            voci.append(Voce(_id(tpl, testo, used), tpl, ti, ri, misura, gruppo, testo, applic, fmt))
    return voci


# ------------------------------------------------------------------ suggerimenti da documentazione
RULES = [
    (r"estintor", "estintori", "Estintori citati nella documentazione"),
    (r"idrant|naspi", "idranti/naspi", "Idranti/naspi citati nella documentazione"),
    (r"rivelazione|IRAI", "rivelazione/allarme incendio", "Impianto di rivelazione/allarme citato nella documentazione"),
    (r"sprinkler|automatic", "sprinkler", "Impianto automatico citato nella documentazione"),
    (r"illuminazione di sicurezza|illuminazione di emergenza", "illuminazione di emergenza", "Illuminazione di emergenza citata nella documentazione"),
    (r"segnaletica", "segnaletica sicurezza", "Segnaletica di sicurezza citata nella documentazione"),
    (r"tagliafuoco|EI\b|REI", "porte tagliafuoco", "Porte/elementi tagliafuoco citati nella documentazione"),
    (r"smaltimento|evacuator|SEFC|aperture", "evacuatori fumo", "Aperture/evacuatori fumo citati nella documentazione"),
]
GEST = [
    (r"Piano di Emergenza", "piano_emergenza_presente", "Piano di emergenza citato nella documentazione"),
    (r"Registro dei controlli", "registro_controlli_presente", "Registro dei controlli citato nella documentazione"),
    (r"addetti antincendio|Designazione degli addetti", "addetti_antincendio_nominati", "Addetti antincendio citati nella documentazione"),
    (r"Prove di evacuazione", "prove_evacuazione", "Prove di evacuazione citate nella documentazione"),
]


def suggerisci(v: Voce, caso) -> dict | None:
    qf = (caso.esito.get("rischio") or {}).get("qf")
    if v.applic.strip().lower().startswith("qf>900") and qf is not None and qf <= 900:
        return {"esito": "NA", "nota": f"qf = {qf:g} MJ/m² ≤ 900: prescrizione non applicabile", "auto": True}
    pres = caso.get("presidi_rilevati", []) or []
    fonte = caso.dati["presidi_rilevati"].fonte if "presidi_rilevati" in caso.dati else ""
    for pat, k, msg in RULES:
        if re.search(pat, v.testo, re.I) and k in pres:
            return {"esito": None, "nota": f"{msg} ({fonte}): confermare in sopralluogo.", "auto": False}
    for pat, k, msg in GEST:
        if re.search(pat, v.testo, re.I) and caso.get(k):
            f = caso.dati[k].fonte
            return {"esito": None, "nota": f"{msg} ({f}): verificare contenuto, data e aggiornamento.", "auto": False}
    return None


PRIORITA_ALTA = re.compile(r"uscit|esodo|illuminazione|estintor|tagliafuoco|allarme|rivelazione|gas|elettric|sgancio|bombol", re.I)


def azioni_da_nc(voci: list[Voce], risposte: dict) -> list[dict]:
    az = []
    for v in voci:
        r = risposte.get(v.id)
        if not r or r.get("esito") != "NC":
            continue
        pr = int(r.get("priorita") or (1 if PRIORITA_ALTA.search(v.testo) else 2))
        az.append({"priorita": pr, "azione": (r.get("azione") or f"Ripristinare la conformità: {v.testo.split(' / ')[0][:160]}"),
                   "misura": v.misura, "responsabile": r.get("responsabile") or "Datore di lavoro", "scadenza": r.get("scadenza") or "",
                   "origine": v.id, "stato": "Aperta"})
    az.sort(key=lambda a: (a["priorita"], a["misura"]))
    return az
