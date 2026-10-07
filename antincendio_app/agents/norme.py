"""Agente NORME: indicizza (in locale) i testi normativi forniti in `norme/` e li rende citabili.

Il corpus è quello che l'utente fornisce (D.Lgs. 81/08, DM 3/8/2015, DM 1-2-3/9/2021, DPR 151/2011, dispense VVF…):
l'app non inventa articoli. Ricerca per parole chiave (TF-IDF) con citazione file/pagina.
"""
from __future__ import annotations
import math, re
from collections import Counter
from functools import lru_cache
from pathlib import Path

NORME_DIR = Path(__file__).resolve().parents[2] / "norme"
STOP = set("il lo la i gli le un una di del della dei delle da in con su per tra fra e ed o che si non è sono al allo alla ai agli alle dal dalla nel nella nei nelle sul sulla".split())


def _tok(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-zàèéìòù0-9]{3,}", t.lower()) if w not in STOP]


def _passaggi(path: Path):
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for i, pg in enumerate(pdf.pages, start=1):
                yield i, pg.extract_text() or ""
    elif ext == ".docx":
        import docx
        d = docx.Document(str(path))
        yield 1, "\n".join(p.text for p in d.paragraphs)
    elif ext in (".txt", ".md"):
        yield 1, path.read_text(errors="ignore")


@lru_cache(maxsize=1)
def _indice(mtimes: tuple):
    docs = []
    for f in sorted(NORME_DIR.glob("**/*")):
        if f.is_file() and f.suffix.lower() in (".pdf", ".docx", ".txt", ".md") and not f.name.upper().startswith("LEGGIMI"):
            try:
                for pg, testo in _passaggi(f):
                    righe = [r for r in testo.splitlines() if r.strip()]
                    for k in range(0, len(righe), 8):
                        blocco = " ".join(righe[k:k + 10])
                        if len(blocco) > 60:
                            docs.append((f.name, pg, blocco, Counter(_tok(blocco))))
            except Exception:
                continue
    df = Counter()
    for *_, c in docs:
        df.update(c.keys())
    return docs, df, len(docs)


def cerca(query: str, n: int = 3) -> list[dict]:
    if not NORME_DIR.exists():
        return []
    mt = tuple((str(p), p.stat().st_mtime) for p in sorted(NORME_DIR.glob("**/*")) if p.is_file())
    docs, df, N = _indice(mt)
    q = _tok(query)
    if not docs or not q:
        return []
    sc = []
    for f, pg, testo, c in docs:
        s = sum((1 + math.log(c[w])) * math.log(1 + N / (1 + df[w])) for w in q if c.get(w))
        if s > 0:
            sc.append((s, f, pg, testo))
    sc.sort(reverse=True)
    return [{"file": f, "pagina": pg, "testo": t[:420], "punteggio": round(s, 2)} for s, f, pg, t in sc[:n]]


def arricchisci(caso) -> None:
    """Allega ai rilievi con riferimento normativo il passo più pertinente del corpus fornito dall'utente."""
    if not NORME_DIR.exists() or not any(NORME_DIR.glob("**/*.*")):
        return
    for f in caso.findings:
        if f.riferimento and "Riscontro nel corpus" not in f.messaggio:
            r = cerca(f.riferimento + " " + f.messaggio[:120], 1)
            if r and r[0]["punteggio"] > 6:
                f.messaggio += f" [Riscontro nel corpus: {r[0]['file']} p.{r[0]['pagina']}: «{r[0]['testo'][:200]}…»]"
