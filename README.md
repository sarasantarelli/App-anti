# App-anti — Valutazione del Rischio Incendio autogestita

Genera **VRI** (Valutazione del Rischio Incendio, artt. 28 e 46 D.Lgs. 81/08) e **Piano di Emergenza** compilando i
**template ufficiali** (`templates/`): stessi colori, font e struttura, **Word modificabile + PDF**, pronti per essere
esibiti agli organi di vigilanza dopo sopralluogo e firma. **Nessuna chiave API**: lettura OCR, calcoli e redazione sono
locali (RapidOCR/ONNX, ffmpeg, Microsoft Word per i PDF).

```
documenti, foto, video del cliente ──► LETTURA ─► ESTRAZIONE (dato + fonte) ─► CONTROLLO dati mancanti
                                                                                   │
        ┌───────────────────────────── COORDINATORE ◄──────────────────────────────┘
        ▼
 RISCHIO (Rvita/Rbeni/Rambiente, qf,d) ─► NORMATIVO (ramo A/B/C, DPR 151, Allegato I) ─► STRATEGIA (S.1–S.10, esodo, estintori)
        ▼
 MISURE (check-list dal template → azioni correttive) ─► CONTROLLO incrociato ─► NORME (citazioni dal corpus) ─► COMPOSIZIONE docx/pdf ─► VERIFICA
```

| Agente | Compito |
|---|---|
| Coordinatore (`coordinatore.py`) | regista: ordine, cicli di ricalcolo, stato BOZZA / PRONTO PER LA FIRMA, relazione di tracciabilità |
| Lettura / Estrazione | PDF, Word, Excel, immagini, video → dati strutturati **con la fonte di ciascun dato** (non confermati finché il tecnico non li valida) |
| Normativo | percorso DM 3/9/2021 art. 2 (A/B/C), assoggettamento DPR 151/2011 (binario parallelo), requisiti Allegato I; sceglie il template |
| Rischio | δocc, δα, Rvita, Rbeni, Rambiente, qf (tabellare/analitico), qf,d e classe REI |
| Strategia / Misure | livelli S.1–S.10 valutando **i criteri letti dal template**; esodo (uscite, Lcc, Les, larghezze), estintori A/B/F, formazione e addetti |
| Controllo | completezza, incoerenze, soglie al limite, presidi richiesti ma non rilevati, confini di responsabilità |
| Norme | indicizza i testi in `norme/` e li cita (file/pagina) nei rilievi |

**Template scelto automaticamente:** `VRI_Minicodice` (basso rischio) · `VRI_Codice_Integrale_RTO` (non basso) ·
`VRI_Raccordo_CPI` (attività soggetta con pratica VVF) · sempre `Piano_di_Emergenza`.

## Regole di sicurezza del documento (per l'esibizione)
- Il documento è **BOZZA** finché il sopralluogo non è completo e non ci sono dati bloccanti mancanti; i campi non determinati restano **evidenziati in arancio** e non si scrive mai «nessuna non conformità» se la check-list è incompleta.
- Le voci precompilate da documenti restano «da confermare in sito». Le NC generano automaticamente le azioni correttive (VRI-11).
- La VRI **non sostituisce** progetto, SCIA o asseverazione del professionista antincendio: se l'attività è soggetta, il documento lo dichiara.
- Firme (DdL, RSPP, RLS) e responsabilità restano delle persone. Ogni dato ha la sua fonte; la *Relazione di controllo* ricostruisce il ragionamento.

## Come sceglie il modello (nessun «non basso» di default)
L'app **analizza il caso e poi sceglie**: attività soggetta ai controlli VVF → *Raccordo con la pratica*; altrimenti verifica i requisiti dell'Allegato I
(occupanti, superficie, quote, qf, sostanze, lavorazioni, RTV): tutti soddisfatti → *Minicodice*; anche uno solo contraddetto → *Codice integrale*.
Se un dato manca e nessun requisito è contraddetto, la scelta è **provvisoria** (Minicodice) e il documento non afferma «tutti i requisiti soddisfatti»:
dice quali dati servono per confermarla.

## Gestionale: sempre acceso, sempre salvato, aggiornabile
- **Collegamento sul Desktop** (`CREA_COLLEGAMENTO.bat`): un clic apre una finestra dedicata, senza finestra nera; il server resta in background (opzione: avvio automatico con Windows). `FERMA.bat` lo spegne.
- **Salvataggio continuo:** ogni campo e ogni esito del sopralluogo si salva subito; backup completo automatico ogni giorno (ultimi 14) in `backup/`, ripristinabile dalla scheda **Sistema**.
- **Storico:** ogni emissione dei documenti resta archiviata con la sua revisione; «Nuova revisione» aggiorna il registro delle revisioni (art. 29 c.3 D.Lgs. 81/08); «Duplica pratica» per l'aggiornamento annuale.
- **Aggiornamento:** scheda **Sistema → Aggiorna** (da internet o da file ZIP): sostituisce solo il programma, pratiche, norme e template restano intatti; l'app si riavvia da sola.

## Senza installare nulla: GitHub Codespaces
Apri https://codespaces.new/sarasantarelli/App-anti?ref=claude/fire-safety-assessment-app-0c719q → **Create codespace**. Dopo qualche minuto l'app si apre nel browser
(porta 8000 **privata**: solo tu, con il tuo account GitHub). Limiti: i dati stanno nel cloud di GitHub (valuta la riservatezza dei clienti), il PDF si fa con
LibreOffice (non Word), il codespace si sospende dopo inattività e ha un monte ore gratuito mensile. Per un uso quotidiano e riservato resta meglio l'installazione sul PC.

## Uso sul PC (Windows: nessuna competenza tecnica)
1. Scarica/copia la cartella del progetto sul PC (es. `C:\App-anti`).
2. **Doppio clic su `INSTALLA.bat`** (una volta: crea l'ambiente Python, installa i componenti, controlla che ci sia Microsoft Word per i PDF).
3. **Doppio clic su `AVVIA.bat`**: si apre il browser su http://localhost:8000. I dati restano nella cartella `data/` del PC; nulla esce dal computer.
macOS/Linux: `./avvia.sh`. Controllo dell'installazione: `python -m antincendio_app diagnostica`.

## Norme, libri di valutazione, dispense (scheda «Norme e libri»)
Carica PDF/Word/TXT dalla scheda **Norme e libri** (o copiali in `norme/`). Vengono indicizzati una sola volta (i PDF scansionati con OCR) e usati per
**citare file e pagina** nei rilievi della *Relazione di controllo* e per la ricerca a parole chiave. I valori di calcolo restano quelli dei template:
se un libro contiene tabelle/regole da applicare, vanno trasferite nell'app (chiedilo: si codificano in `regole.py` con test).

## Uso
**Web:** `python -m antincendio_app serve` → http://localhost:8000 — carica i file, rivedi *Esito → Dati → Sopralluogo → Azioni → Documenti*.
**Riga di comando:** `python -m antincendio_app genera ./cartella_cliente --dati dati.json --out ./out`
**Audit dei template:** `python -m antincendio_app verifica-template` (vedi `docs/VERIFICA_TEMPLATE.md`)

Installazione locale: Python 3.10+, `pip install -r requirements.txt`, per i PDF **Microsoft Word** (su Windows/macOS; in alternativa LibreOffice), per i video ffmpeg è incluso nei componenti.
Su Windows la via più semplice è Docker Desktop: `docker compose up --build` (poi http://localhost:8000).

## Pubblicazione (accesso da fuori di questo PC)
L'app è un'immagine Docker autonoma. Tre strade, dalla più semplice:
1. **Render** (consigliata): nuovo *Blueprint* → seleziona questo repository (`render.yaml`). La password d'accesso viene generata e mostrata nel pannello.
2. **Qualsiasi VPS / PC sempre acceso**: `APP_PASSWORD=<password> docker compose up -d --build`; per HTTPS usa Caddy/Nginx oppure Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:8000`).
3. **GitHub Actions** pubblica l'immagine su `ghcr.io/<owner>/app-anti:latest` a ogni push su `main`: usabile da Fly.io, Railway, Azure, ecc.

Sicurezza (contiene dati di clienti): imposta **sempre** `APP_PASSWORD` (HTTP Basic, solo su HTTPS); ID pratica casuali; i dati si
cancellano dopo `RETENTION_HOURS` (default 72 h); upload limitato da `MAX_UPLOAD_MB`. Valuta l'informativa GDPR verso i clienti.

## Limiti dichiarati
- Foto/video: senza modello di visione si leggono i **testi** (cartelli, targhe estintori, planimetrie quotate), non gli oggetti.
- Lo screening DPR 151/2011 copre le voci più comuni, non l'intero Allegato I; l'esito è sempre «stimato».
- I template hanno alcune incoerenze (docs/VERIFICA_TEMPLATE.md); gli estremi dell'Accordo Stato-Regioni 17/04/2025 vanno confermati.
- Il giudizio finale (δα, aree a rischio specifico, livelli S.x dove i criteri sono discrezionali) è del professionista: l'app propone in modo cautelativo e lo dichiara.

## Aggiornare i template
Sostituisci i file in `templates/` mantenendo i nomi e la struttura (tabelle e titoli): criteri, check-list e tabelle di calcolo
sono **letti dal template**, quindi il comportamento segue le tue modifiche. Dopo la modifica: `python -m pytest`.

## Struttura
`antincendio_app/agents/` agenti · `compositore/` compilazione dei 4 template · `checklist.py` voci di verifica dai template ·
`criteri.py` valutatore dei criteri S.x-2 · `regole.py` tabelle di calcolo · `web/` interfaccia · `scripts/sweep.py` giro di prove su scenari sintetici (`python scripts/sweep.py 120 7`) · `tests/` test automatici.
