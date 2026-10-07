"""Agente INNESCO: stima prudenziale delle 13 sorgenti di accensione (UNI EN 1127-1, Tab. V.2-2 del Codice)
a partire da testi di documenti, foto/video e dati inseriti. Non sostituisce il sopralluogo: dichiara la fonte."""
from __future__ import annotations
import re
from ..models import Caso

CATEGORIE = ["Superfici calde", "Fiamme, gas, particelle calde", "Scintille di origine meccanica",
             "Materiale ed impianti elettrici", "Correnti vaganti, protezione catodica", "Elettricità statica", "Fulmini",
             "Radiofrequenze", "Onde elettromagnetiche", "Radiazioni ionizzanti", "Ultrasuoni",
             "Compressione adiabatica ed onde d’urto", "Reazioni esotermiche"]

# (regex, livello, nota)
REGOLE = {
    0: [(r"friggitric|forno|cappa|piastra|stufa|caldai|radiator|lampad\w+ (?:a )?(?:incandescenza|alogen)", "media", "apparecchi a superficie calda presenti (cottura/riscaldamento)")],
    1: [(r"saldatur|fiamma libera|taglio termico|cannello", "alta", "lavorazioni con fiamma/scintille di saldatura"),
        (r"\bgpl\b|metano|bruciator|fornell|caldaia|candel|fumo", "media", "combustione/gas presenti: bruciatori, fornelli o caldaie")],
    2: [(r"molatur|smeriglia|taglio|trapan|carrell|utensil", "media", "utensili/attrezzature con possibile produzione di scintille")],
    3: [(r".", "media", "impianto elettrico presente in ogni attività: DiCo, quadri, verifiche DPR 462/2001 da accertare")],
    4: [(r"protezione catodica|correnti vaganti|interrat\w+ metallic", "bassa", "strutture metalliche interrate")],
    5: [(r"travas|polver|solvent|vernic|liquid\w+ infiammabil|segatura|farina", "media", "travaso/trattamento di liquidi o polveri: possibile accumulo di cariche")],
    6: [(r".", "bassa", "esposizione a fulmini: valutazione LPS (CEI EN 62305) da accertare")],
    7: [(r"radiofrequenz|trasmettitor|antenna", "bassa", "sorgenti a radiofrequenza")],
    8: [(r"laser|saldatura ad arco|ultraviolet", "bassa", "sorgenti ottiche/laser")],
    9: [(r"raggi x|radiazion\w+ ionizzant|radiolog", "bassa", "apparecchi radiologici")],
    10: [(r"ultrasuon|saldatrice ad ultrasuoni", "bassa", "apparecchi a ultrasuoni")],
    11: [(r"compressor|aria compressa|pneumatic", "bassa", "compressori/aria compressa")],
    12: [(r"stracc\w+ imbev|autocombust|ossidant|incompatibil|olio di lino|batterie al litio|litio", "media", "possibili reazioni esotermiche/autocombustione")],
}


def valuta(c: Caso) -> list[dict]:
    corpus = " ".join([str(c.get("attivita_descrizione", "")), str(c.get("lavorazioni_rischio", ""))]
                      + [e.get("testo", "") for e in c.evidenze] + list(c.get("sostanze", []) or [])
                      + list(c.get("presidi_rilevati", []) or []))
    out = []
    for i, cat in enumerate(CATEGORIE):
        liv, nota = None, ""
        for rx, l, n in REGOLE[i]:
            if re.search(rx, corpus, re.I):
                if liv is None or ["bassa", "media", "alta"].index(l) > ["bassa", "media", "alta"].index(liv):
                    liv, nota = l, n
        out.append({"categoria": cat, "livello": liv, "nota": nota})
    c.esito["innesco"] = out
    return out
