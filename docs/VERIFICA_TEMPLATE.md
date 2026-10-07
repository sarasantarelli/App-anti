# Verifica dei template e della norma — esito e punti aperti

Eseguibile in ogni momento: `python -m antincendio_app verifica-template`.

## 1. Cosa è stato verificato
| Verifica | Esito |
|---|---|
| Requisiti Allegato I DM 3/9/2021 (≤100 occupanti, ≤1.000 m², quote −5/+24 m) | Confermati da fonte web (sintesi del decreto) |
| Requisiti aggiuntivi dell'Allegato I (qf ≤ 900 MJ/m², nessuna sostanza pericolosa significativa, nessuna lavorazione pericolosa) | Confermati da fonte web; **il template Minicodice non li dimostra nella VRI-2.3** (vedi §2.1). L'app li verifica comunque tutti prima di scegliere il Minicodice |
| Tabelle di calcolo (G.3, S.2-6/7/8/3, S.4-15/18/25/27/28/29, S.6-5/6, criteri S.x-2) | Lette **dai template ufficiali** (fonte unica); coerenti tra loro. Non confrontate carattere per carattere con il testo del DM 3/8/2015 (il sito del testo era bloccato dal proxy dell'ambiente) |
| Percorso di qualificazione (art. 2 DM 3/9/2021: rami A/B/C) | Coerente con la metodologia VRI fornita |

## 2. Anomalie dei template (da correggere a monte)
1. **Minicodice, VRI-2.3**: dimostra solo affollamento, superficie, quote, non-assoggettamento e assenza di RTV. Il Codice (VRI-2.1) verifica anche C.d qf ≤ 900, C.e sostanze, C.f lavorazioni. Allineare, altrimenti la VRI-2.3 sembra incompleta a un ispettore.
2. **Piano di Emergenza — rimandi vuoti** «()» in 8 punti (es. PE-7.2, PE-7.3, PE-7.1): perdita di un riferimento incrociato.
3. **Piano di Emergenza — rimandi a «VRI §1.1 / §1.3 / Cap. 5»**: nelle VRI le sezioni si chiamano VRI-4 (attività/affollamento), VRI-6 (aree a rischio specifico), VRI-9 (strategia): i rimandi non esistono.
4. **Refusi**: «Idirizzo sede» (copertina Codice), «ITERVENTO PRELIMINARE» (PE-8.2), «piú» (VRI-7bis). L'app li corregge nei documenti generati (il template resta intatto).
5. **Intestazione Codice**: contiene il segnaposto «AZIENDA» (l'app lo sostituisce con la ragione sociale).

## 3. Da confermare sul testo ufficiale (non verificabile da qui)
- **«Accordo Stato-Regioni 17/04/2025»** citato nei template per i livelli di formazione (Livello 1: 4 h, Livello 2: 8 h + 4 h di aggiornamento, Livello 3: 16 h). La ricerca web non ne ha restituito il testo; i riferimenti sono quelli dei template (che l'app riproduce). Controllare estremi e contenuti prima di esibire.
- **Elenco attività DPR 151/2011**: l'app fa uno *screening* sulle voci più comuni (65, 66, 67, 68, 69, 70, 71, 74, 75, 34, 36, 43, 12, altezza >24 m). Non è l'Allegato I completo: l'esito è sempre dichiarato «stimato».
- **Numerazione e testo delle RTV Sezione V** del Codice: l'app segnala quando per la tipologia esiste di norma una RTV ma non ne indica il numero; lo inserisce il tecnico («RTV applicabile»).
- **Tab. G.3-2 (δα)**: l'app propone δα in modo cautelativo dai materiali presenti; è sempre sovrascrivibile («δα imposto dal tecnico»).

Aggiungi i testi ufficiali in `norme/`: l'agente *Norme* li cita (file e pagina) nella Relazione di controllo.
