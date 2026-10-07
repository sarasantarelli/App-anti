"""Rilevamento dell'ambiente locale (Windows / macOS / Linux): strumenti opzionali e loro alternative.

- ffmpeg (fotogrammi dei video): di sistema, altrimenti quello incluso nel pacchetto `imageio-ffmpeg` (nessuna installazione).
- PDF: LibreOffice (consigliato) → in alternativa Microsoft Word (via docx2pdf, solo se installato) → altrimenti solo Word/.docx.
"""
from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path

WIN_SOFFICE = [r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
MAC_SOFFICE = ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]


def trova_ffmpeg() -> str | None:
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def trova_soffice() -> str | None:
    for n in ("soffice", "libreoffice"):
        p = shutil.which(n)
        if p:
            return p
    for p in WIN_SOFFICE + MAC_SOFFICE:
        if Path(p).exists():
            return p
    return None


def word_disponibile() -> bool:
    try:
        import docx2pdf  # noqa: F401
    except Exception:
        return False
    return platform.system() in ("Windows", "Darwin")


def converti_pdf(docx_path: Path, outdir: Path) -> Path | None:
    docx_path, outdir = Path(docx_path), Path(outdir)
    target = outdir / (docx_path.stem + ".pdf")
    so = trova_soffice()
    if so:
        try:
            subprocess.run([so, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx_path)],
                           check=True, capture_output=True, timeout=300)
            if target.exists():
                return target
        except Exception:
            pass
    if word_disponibile():
        try:
            from docx2pdf import convert
            convert(str(docx_path), str(target))
            if target.exists():
                return target
        except Exception:
            pass
    return None


def diagnostica() -> list[dict]:
    """Elenco di controlli con esito e rimedio (usato da `diagnostica` e dalla UI)."""
    def ck(nome, ok, dettaglio, rimedio="", obbligatorio=False):
        return {"nome": nome, "ok": bool(ok), "dettaglio": dettaglio, "rimedio": rimedio, "obbligatorio": obbligatorio}
    r = [ck("Python", sys.version_info >= (3, 10), platform.python_version(), "Installa Python 3.10 o superiore da python.org", True)]
    for mod, pip, ob in (("docx", "python-docx", True), ("fastapi", "fastapi", True), ("uvicorn", "uvicorn", True), ("pdfplumber", "pdfplumber", True),
                         ("openpyxl", "openpyxl", True), ("rapidocr_onnxruntime", "rapidocr-onnxruntime", False)):
        try:
            __import__(mod); r.append(ck(pip, True, "installato", obbligatorio=ob))
        except Exception:
            r.append(ck(pip, False, "mancante", f"pip install {pip}", ob))
    tpl = Path(__file__).resolve().parents[1] / "templates"
    for f in ("VRI_Minicodice_template_2.docx", "VRI_Codice_Integrale_RTO_completa_2.docx", "VRI_Raccordo_CPI_template.docx", "Piano_di_Emergenza_standalone_v12_1.docx"):
        r.append(ck("template " + f, (tpl / f).exists(), "presente" if (tpl / f).exists() else "mancante", "ripristina il file in templates/", True))
    ff = trova_ffmpeg()
    r.append(ck("ffmpeg (video)", ff, ff or "non trovato", "pip install imageio-ffmpeg (incluso nell'installazione guidata)"))
    so = trova_soffice()
    r.append(ck("PDF (LibreOffice)", so or word_disponibile(), so or ("Microsoft Word via docx2pdf" if word_disponibile() else "non disponibile: si ottengono solo i .docx"),
                "installa LibreOffice (gratuito, libreoffice.org) per ottenere anche i PDF"))
    return r
