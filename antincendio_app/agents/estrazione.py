"""Agente ESTRAZIONE: dal testo grezzo ai dati strutturati, con fonte per ogni dato."""
from __future__ import annotations
import re
from ..models import Caso

NUM = r"(\d{1,3}(?:[.\s]\d{3})+|\d+)(?:[,.](\d+))?"

def _n(m):
    s = m.group(1).replace(".", "").replace(" ", "")
    return float(s + ("." + m.group(2) if m.group(2) else ""))

PATTERNS = {
    "occupanti_lavoratori": [rf"{NUM}\s*(?:lavoratori|dipendenti|addetti|operai|impiegati|persone in organico)"],
    "occupanti_terzi": [rf"(?:clienti|ospiti|pubblico|visitatori|avventori|coperti|posti a sedere)[^\d\n]{{0,25}}{NUM}",
                        rf"{NUM}\s*(?:clienti|ospiti|avventori|coperti|posti a sedere)"],
    "superficie_mq": [rf"{NUM}\s*(?:mq|m2|m²|metri quadr\w+)", rf"superficie[^\d\n]{{0,30}}{NUM}"],
    "piani": [r"(\d+)\s*piani\s*fuori\s*terra", r"(?:su|di)\s*(\d+)\s*piani"],
    "kw_termico": [rf"(?:impianto termico|caldaia|generatore di calore|centrale termica)[^\d\n]{{0,60}}{NUM}\s*kW", rf"{NUM}\s*kW"],
    "qf_mj_m2": [rf"(?:carico d.?incendio|qf)[^\d\n]{{0,40}}{NUM}\s*MJ"],
}
TXT = {
    "ragione_sociale": r"(?:ragione sociale|azienda|ditta|societ[àa])\s*[:\-]\s*(.+)",
    "indirizzo": r"(?:sede(?: operativa)?|indirizzo|ubicazione)\s*[:\-]\s*(.+)",
    "ateco": r"ATECO\s*[:\-]?\s*([\d.]{4,8})",
    "datore_lavoro": r"datore di lavoro\s*[:\-]\s*(.+)",
    "rspp": r"RSPP\s*[:\-]\s*(.+)",
    "attivita_descrizione": r"(?:attivit[àa] svolta|descrizione attivit[àa]|oggetto dell.attivit[àa])\s*[:\-]\s*(.+)",
}
SOSTANZE = {
    "gpl/gas": r"\b(gpl|metano|gas (?:combustibil|infiammabil)\w*|bombol\w+)",
    "liquidi infiammabili": r"\b(solvent\w+|vernic\w+|diluent\w+|benzina|gasolio|alcool|infiammabil\w+|etanolo)",
    "olio/friggitrici": r"\b(friggitric\w+|olio (?:di )?frittura|cappa|canna fumaria)",
    "legno/carta/cartone": r"\b(legno|truciolat\w+|carta|cartone|imballagg\w+|pallet|bancali)",
    "materie plastiche/gomma": r"\b(plastic\w+|gomma|pneumatic\w+|polistirol\w+|schiuma)",
    "tessili": r"\b(tessil\w+|abbigliament\w+|tessut\w+)",
    "batterie/litio": r"\b(litio|batterie|accumulator\w+|carica batterie)",
    "polveri": r"\b(polver\w+|farina|segatura)",
    "lavorazioni a caldo": r"\b(saldatur\w+|taglio termico|fiamma libera|forno|molatur\w+|lavorazioni a caldo)",
    "esplosivi/ATEX": r"\b(atex|atmosfer\w+ esplosiv\w+|esplosiv\w+)",
}
PRESIDI = {
    "estintori": r"\bestintor\w+", "idranti/naspi": r"\b(idrant\w+|naspi)",
    "rivelazione/allarme incendio": r"\b(rivelazion\w+|rilevator\w+ (?:di )?fum\w+|centralina antincendio|allarme incendio|IRAI)",
    "sprinkler": r"\b(sprinkler|spegnimento automatico)",
    "illuminazione di emergenza": r"illuminazione (?:di )?emergenza|lampade? di emergenza",
    "segnaletica sicurezza": r"segnaletica|cartell\w+ (?:di )?(?:sicurezza|uscita)|usc\w*\s*(?:d\w*\s*)?sicurezza",
    "porte tagliafuoco": r"\b(?:porte? )?(?:tagliafuoco|REI \d+|EI ?\d+)",
    "evacuatori fumo": r"\b(evacuator\w+|EFC|aperture di smaltimento)",
}
GESTIONE = {
    "piano_emergenza_presente": r"piano di emergenza|piano emergenza|PE aziendale",
    "registro_controlli_presente": r"registro (?:dei )?controlli|registro antincendio",
    "addetti_antincendio_nominati": r"addett\w+ (?:al servizio )?antincendio|squadra antincendio",
    "prove_evacuazione": r"prov\w+ di evacuazione|esercitazion\w+ (?:di )?evacuazione",
}
TIPI_ATT = {
    "ristorazione": r"ristorant\w+|pizzeri\w+|trattori\w+|bar\b|cucina|somministrazione",
    "ufficio": r"\buffici?\b|studio professionale",
    "commercio": r"negozi\w*|commercio|vendita al dettaglio|supermercat\w+|magazzino vendita",
    "officina/produzione": r"officin\w+|produzione|stabiliment\w+|laboratori\w+ artigian\w+|carpenteri\w+|falegnamer\w+",
    "deposito/magazzino": r"depositi?\b|magazzin\w+|logistic\w+",
    "ricettivo": r"alberg\w+|hotel|b&b|bed and breakfast|affittacamere|struttura ricettiva|camere",
    "sanitario": r"ambulator\w+|clinic\w+|studio medico|casa di riposo|rsa\b|poliambulatorio",
    "scuola": r"scuol\w+|asilo|nido|formazione",
    "spettacolo/intrattenimento": r"discotec\w+|pub\b|karaoke|dj set|pista da ballo|locale di intrattenimento|cinema|teatro",
    "autorimessa": r"autorimess\w+|parcheggio coperto|garage|box auto",
}


def estrai(caso: Caso) -> Caso:
    cand: dict[str, list[tuple]] = {}
    for ev in caso.evidenze:
        t, f = ev.get("testo", ""), ev["file"]
        for k, pats in PATTERNS.items():
            for p in pats:
                for m in re.finditer(p, t, re.I):
                    try:
                        v = _n(m) if m.lastindex and m.lastindex >= 2 and m.group(1) and m.re.groups >= 2 else float(re.sub(r"[.\s]", "", m.group(1)))
                    except Exception:
                        continue
                    if k == "piani" and v > 30: continue
                    if k == "superficie_mq" and v < 10: continue
                    cand.setdefault(k, []).append((v, f))
        for k, p in TXT.items():
            m = re.search(p, t, re.I)
            if m:
                cand.setdefault(k, []).append((m.group(1).strip()[:160], f))
        for k, p in SOSTANZE.items():
            if re.search(p, t, re.I): cand.setdefault("sostanze", []).append((k, f))
        for k, p in PRESIDI.items():
            if re.search(p, t, re.I): cand.setdefault("presidi_rilevati", []).append((k, f))
        for k, p in GESTIONE.items():
            if re.search(p, t, re.I): cand.setdefault(k, []).append((True, f))
        for k, p in TIPI_ATT.items():
            if re.search(p, t, re.I): cand.setdefault("tipologia_attivita", []).append((k, f))

    caso.esito["candidati"] = {k: [list(x) for x in v] for k, v in cand.items()}

    def put(k, v, fonte):
        if k not in caso.dati or not caso.dati[k].confermato:
            caso.set(k, v, fonte, confermato=False)

    for k in ("occupanti_lavoratori", "occupanti_terzi", "superficie_mq", "qf_mj_m2", "piani", "kw_termico"):
        if k in cand:
            vals = cand[k]
            v, f = max(vals, key=lambda x: x[0])      # cautelativo: valore massimo
            put(k, v, f)
            distinct = sorted({x[0] for x in vals})
            if len(distinct) > 1:
                caso.add("Estrazione", "attenzione",
                         f"Valori discordanti per «{k}»: {distinct} (fonti: {sorted({x[1] for x in vals})}). "
                         f"Assunto il massimo ({v:g}) in via cautelativa: il tecnico deve confermare.")
    # liquidi (litri) accanto a solventi/vernici/infiammabili
    lit = []
    for ev in caso.evidenze:
        for m in re.finditer(r"(?:solvent\w+|vernic\w+|diluent\w+|infiammabil\w+|benzina|gasolio|alcool)[^.\n]{0,80}?" + NUM + r"\s*(?:litri|l\b)", ev.get("testo", ""), re.I):
            lit.append(_n(m))
    if lit:
        put("litri_infiammabili", sum(lit), "documenti (somma dei litri citati)")
    # nome piani
    for k in ("ragione_sociale", "indirizzo", "ateco", "datore_lavoro", "rspp", "attivita_descrizione"):
        if k in cand: put(k, cand[k][0][0], cand[k][0][1])
    for k in GESTIONE:
        if k in cand: put(k, True, cand[k][0][1])
    for k in ("sostanze", "presidi_rilevati", "tipologia_attivita"):
        if k in cand:
            vals = sorted({x[0] for x in cand[k]})
            put(k, vals, ", ".join(sorted({x[1] for x in cand[k]})))
    caso.log.append(f"Estrazione: {len(cand)} categorie di dati rilevate da {len(caso.evidenze)} file")
    return caso
