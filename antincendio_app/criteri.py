"""Valutatore dei criteri di attribuzione dei livelli di prestazione (Tab. S.x-2).

I criteri NON sono scritti nel codice: sono letti dal template dell'utente (tabelle
'Livello | Condizione da verificare | Esito'), così se il template viene aggiornato l'app lo segue.
Ogni condizione è valutata a True / False / None (None = non determinabile dai dati: da verificare in sopralluogo).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from docx.table import Table
from . import docxkit as K
from .regole import expand_rvita, rvita_in


@dataclass
class Ctx:
    """Dati di ingresso per la valutazione delle condizioni."""
    rvita: str = "A2"
    rbeni: int = 1
    rambiente_signif: bool = False
    qf: float | None = None
    sup_comp: float | None = None            # superficie lorda del compartimento maggiore
    occupanti: float = 0
    superficie: float = 0
    quota_min: float | None = None
    quota_max: float | None = None
    aperta_pubblico: bool = True
    disabili_prevalenti: bool = False
    sostanze_significative: bool | None = None
    lavorazioni_pericolose: bool | None = None
    posti_letto: float = 0
    soggetta_dpr151: bool = False
    compartimentata: bool | None = None
    un_responsabile: bool | None = True
    presenza_occupanti: bool = True

    @property
    def densita(self):
        return (self.occupanti / self.superficie) if self.superficie else None


@dataclass
class Livello:
    nome: str
    condizioni: list[tuple[int, str]] = field(default_factory=list)   # (indice riga, testo)
    any_mode: bool = False
    fallback: bool = False
    discrezionale: bool = False


def _num(s):
    return float(s.replace(".", "").replace(",", "."))


def valuta(txt: str, c: Ctx):
    t = txt.strip()
    tl = t.lower().replace("’", "'").replace(", con", " con")
    if re.match(r"^(attribuito a tutte|tutte le attività)", tl):
        return True
    if "non ammesso nelle attività soggette" in tl:
        return not c.soggetta_dpr151
    if "non ricompres" in tl and "criteri" in tl:
        return "FALLBACK"
    if tl.startswith("su richiesta") or tl.startswith("per il livello"):
        return None
    m = re.match(r"rvita compresi in (.+)", tl, re.I)
    if m:
        return rvita_in(c.rvita, expand_rvita(t[m.start(1):]))
    if re.match(r"rvita = ", tl) or "applicabile in particolare con rvita" in tl:
        sp = re.split(r"rvita\s*=\s*", t, flags=re.I)[-1]
        return rvita_in(c.rvita, expand_rvita(sp.split("…")[0].replace("…", "")))
    m = re.match(r"rbeni pari a (\d)(?: o (\d))?", tl)
    if m:
        return c.rbeni in {int(x) for x in m.groups() if x}
    m = re.match(r"rbeni compreso in (\d), (\d)", tl)
    if m:
        return c.rbeni in {int(m.group(1)), int(m.group(2))}
    if tl.startswith("rambiente non significativo"):
        return not c.rambiente_signif
    m = re.match(r"qf ≤ ([\d.,]+) mj", tl)
    if m:
        return None if c.qf is None else c.qf <= _num(m.group(1))
    m = re.match(r"piani a quota compresa tra (-?\d+) m e (-?\d+) m", tl)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if c.quota_min is None or c.quota_max is None:
            return None
        return lo <= c.quota_min and c.quota_max <= hi
    m = re.match(r"densità di affollamento ≤ ([\d,\.]+)", tl)
    if m:
        return None if c.densita is None else c.densita <= _num(m.group(1))
    if "non prevalentemente destinata a occupanti con disabilità" in tl:
        return not c.disabili_prevalenti
    if tl.startswith("attività non aperta al pubblico"):
        return not c.aperta_pubblico
    if tl.startswith("non si detengono") and "sostanz" in tl:
        return None if c.sostanze_significative is None else (not c.sostanze_significative)
    if tl.startswith("non si effettuano lavorazioni"):
        return None if c.lavorazioni_pericolose is None else (not c.lavorazioni_pericolose)
    m = re.match(r"per compartimenti con qf > 200.*superficie lorda ≤ ([\d.,]+)", tl)
    if m:
        if c.qf is None or c.sup_comp is None: return None
        return True if c.qf <= 200 else c.sup_comp <= _num(m.group(1))
    m = re.match(r"per compartimenti con qf ≤ 200.*superficie lorda (?:qualsiasi|≤ ([\d.,]+))", tl)
    if m:
        if c.qf is None: return None
        if c.qf > 200: return True
        return True if not m.group(1) else (c.sup_comp or c.superficie) <= _num(m.group(1))
    m = re.match(r"superficie lorda di ciascun compartimento ≤ ([\d.,]+)", tl)
    if m:
        return None if c.sup_comp is None else c.sup_comp <= _num(m.group(1))
    m = re.match(r"se aperta al pubblico: affollamento > (\d+)", tl)
    if m:
        return c.aperta_pubblico and c.occupanti > int(m.group(1))
    m = re.match(r"se non aperta al pubblico: affollamento > (\d+)", tl)
    if m:
        return (not c.aperta_pubblico) and c.occupanti > int(m.group(1))
    m = re.match(r"posti letto > (\d+) con rvita in (.+)", tl)
    if m:
        return c.posti_letto > int(m.group(1)) and rvita_in(c.rvita, expand_rvita(t[t.lower().find("rvita in") + 8:]))
    m = re.match(r"sostanze pericolose.*affollamento > (\d+)", tl)
    if m:
        return None if c.sostanze_significative is None else (c.sostanze_significative and c.occupanti > int(m.group(1)))
    m = re.match(r"lavorazioni pericolose.*affollamento > (\d+)", tl)
    if m:
        return None if c.lavorazioni_pericolose is None else (c.lavorazioni_pericolose and c.occupanti > int(m.group(1)))
    if tl.startswith("compartimentata rispetto") or tl.startswith("compartimentata e strutturalmente"):
        return c.compartimentata
    if tl.startswith("attività di un solo responsabile con rbeni"):
        return None if c.un_responsabile is None else (c.un_responsabile and c.rbeni == 1)
    if tl.startswith("attività di un solo responsabile con rvita"):
        return None if c.un_responsabile is None else (c.un_responsabile and c.rvita.startswith("A") and c.rbeni == 1)
    if tl.startswith("non adibita a presenza occupanti"):
        return not c.presenza_occupanti
    if re.match(r"(alto|elevato) affollamento", tl) or tl.startswith("elevato affollamento"):
        return None   # giudizio del valutatore (valutazione del rischio)
    return None


def parse_criteri(doc) -> dict[int, list[Livello]]:
    """{n_misura: [Livello,...]} letto dalle tabelle 'Livello | Condizione da verificare | Esito'."""
    return _parse(doc)[0]


def parse_criteri_tabelle(doc) -> dict[int, tuple]:
    o, t = _parse(doc)
    return {n: (t[n], o[n][0]) for n in o}


def _parse(doc):
    cur, out, tabs = None, {}, {}
    for b in K.blocks(doc):
        if not isinstance(b, Table):
            m = re.match(r"^\s*S\.(\d+)\s*[—-]", b.text)
            if m:
                cur = int(m.group(1))
            continue
        hdr = [K.ctext(c) for c in K.uniq_cells(b.rows[0])]
        if cur is None or len(hdr) < 3 or hdr[0] != "Livello" or not hdr[1].startswith("Condizione"):
            continue
        liv, cur_l = [], None
        for ri, row in enumerate(b.rows[1:], start=1):
            cs = K.uniq_cells(row)
            nome = K.ctext(cs[0]); testo = K.ctext(cs[1])
            if nome:
                cur_l = Livello(nome=nome); liv.append(cur_l)
            if cur_l is None:
                continue
            if testo.lower().startswith("per il livello") and "sufficiente una" in testo.lower():
                cur_l.any_mode = True
                continue
            cur_l.condizioni.append((ri, testo))
        for l in liv:
            if len(l.condizioni) == 1 and "non ricompres" in l.condizioni[0][1].lower():
                l.fallback = True
            if any(t.lower().startswith("su richiesta") for _, t in l.condizioni):
                l.discrezionale = True
        out.setdefault(cur, []).append(liv)
        tabs[cur] = b
    return out, tabs


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


def attribuisci(livelli: list[Livello], c: Ctx):
    """Ritorna (livello_proposto, dettaglio, dubbi)."""
    det, dubbi = {}, []
    sod = {}
    for L in livelli:
        res = []
        for ri, txt in L.condizioni:
            v = valuta(txt, c)
            res.append((ri, txt, v))
            det[(L.nome, ri)] = v
            if v is None and not L.discrezionale and not txt.lower().startswith("per il livello"):
                dubbi.append(f"Livello {L.nome}: «{txt}» non determinabile dai dati")
        vals = [v for _, _, v in res if v != "FALLBACK"]
        if L.fallback:
            sod[L.nome] = "fallback"
        elif L.discrezionale and not [v for v in vals if v is not None]:
            sod[L.nome] = "discrezionale"
        elif L.any_mode:
            sod[L.nome] = any(v is True for v in vals)
        else:
            sod[L.nome] = all(v is True for v in vals) if vals else False
    ordered = sorted(livelli, key=lambda l: ROMAN.get(l.nome, 9))
    # 1) livelli 'ANY' (escalation): il più alto soddisfatto prevale
    esc = [l for l in ordered if l.any_mode and sod[l.nome] is True]
    if esc:
        return esc[-1].nome, det, dubbi
    # 2) il più basso livello con tutti i criteri soddisfatti
    for l in ordered:
        if sod[l.nome] is True:
            return l.nome, det, dubbi
    # 3) fallback ("non ricompresi negli altri")
    for l in ordered:
        if sod[l.nome] == "fallback":
            return l.nome, det, dubbi
    return ordered[-1].nome, det, dubbi + ["Nessun livello soddisfatto: richiede valutazione del professionista"]
