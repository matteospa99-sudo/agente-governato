# Agente governato

Due agenti AI che lavorano sulla posta di un piccolo studio, sotto controlli che non dipendono dal modello.

**Il principio:** il modello linguistico propone, il codice decide. Ogni azione proposta da un agente passa da un governatore con regole deterministiche. Le azioni irreversibili passano da una persona. Tutto finisce in un registro a prova di manomissione.

Tutti i dati sono inventati. Nessuna email esce davvero: la casella di posta è simulata.

## Che cosa dimostra

La batteria di attacchi usa un modello volutamente credulone, che obbedisce a qualunque istruzione trovi nelle email. Risultato (vedi [`rapporto-attacchi.md`](rapporto-attacchi.md)):

- il modello propone azioni vietate in 8 attacchi su 9 e tutte vengono bloccate;
- **nessuna email arriva a terzi, nemmeno se la persona approva tutto senza leggere.**

La sicurezza, cioè, non si regge sul fatto che il modello non venga ingannato. Si regge sull'architettura.

## Come è fatto

```
email ──> SMISTATORE ──> [punto di controllo C1] ──> PREPARATORE ──> proposte
                                                                       │
                                                              GOVERNATORE (R1-R9)
                                                     ┌─────────────┼──────────────┐
                                                 consentita   serve persona     bloccata
                                                     │             │               │
                                                  eseguita    approva/nega    "da rivedere"
                                                     └──────── REGISTRO ──────────┘
```

| File | Che cosa fa |
|---|---|
| `governato/agenti.py` | I due agenti: lo smistatore classifica, il preparatore propone azioni. Nessuno esegue. |
| `governato/politiche.py` | Il governatore: le regole R1-R9 e il punto di controllo tra agenti. |
| `governato/strumenti.py` | Gli strumenti e la casella simulata. Ogni strumento dichiara se è reversibile. |
| `governato/orchestratore.py` | Mette in fila agenti, regole, persona e registro. |
| `governato/registro.py` | Registro a catena di impronte SHA-256: ogni modifica a posteriori si vede. |
| `governato/modelli.py` | Modello simulato (senza AI) e modello vero (Claude, via API). |
| `prova_attacchi.py` | La batteria di attacchi e il rapporto. |
| `prove/` | 26 test automatici, almeno uno per regola. |

## Le regole

| | Regola | Contro che cosa |
|---|---|---|
| C1 | Il messaggio tra i due agenti ha solo campi chiusi | Istruzioni che passano da un agente all'altro |
| R1 | Interruttore di arresto (anche creando un file `ARRESTO`) | Comportamento fuori controllo |
| R2 | Solo strumenti esistenti | Agente che inventa capacità |
| R3 | Ogni agente ha solo gli strumenti che gli servono | Privilegi eccessivi |
| R4 | Argomenti attesi e ben formati | Proposte malformate o manipolate |
| R5 | Si agisce solo sull'email in lavorazione | Azioni di massa, effetti su altri utenti |
| R6 | Si risponde solo al mittente | Esfiltrazione verso terzi |
| R7 | Testi entro 2000 caratteri | Esaurimento, testi abnormi |
| R8 | Massimo 4 azioni per email | Cicli e azioni a catena |
| R9 | Le azioni irreversibili le decide una persona | Danni non rimediabili |

In più: ogni agente vede solo l'email che sta trattando (minimizzazione dei dati) e, nel dubbio, l'email viene marcata "da rivedere" invece di andare avanti.

## Provarlo

Serve Python 3.10 o successivo. Nessuna libreria esterna per il modello simulato.

```bash
python esegui.py                       # gli agenti lavorano, tu approvi gli invii dal terminale
python esegui.py --approvazione nega   # nessun invio passa
python esegui.py --verifica            # controlla l'integrità del registro
python prova_attacchi.py               # batteria di attacchi, scrive rapporto-attacchi.md
python -m unittest discover prove      # test automatici
```

Con un modello vero:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...           # Mac e Linux. La chiave non va mai scritta nel codice
python esegui.py --modello claude
python prova_attacchi.py --modello claude
```

Su Windows (PowerShell) la chiave si imposta così: `$env:ANTHROPIC_API_KEY="..."`. Se il comando `python` non viene riconosciuto, usa `py`.

## Limiti dichiarati

- È un prototipo dimostrativo, non un prodotto: la casella è simulata e gli strumenti sono quattro.
- La regola R6 è semplice: confronta il destinatario con il mittente. In un sistema reale servirebbero un elenco di contatti autorizzati e la verifica dei domini.
- Il rischio residuo principale è umano: una persona che approva senza leggere una risposta al mittente, quando il mittente è l'attaccante. Il sistema mostra un avviso sui segnali di truffa ma non può sostituire l'attenzione.
- Il rapporto sugli attacchi usa il modello simulato, per scelta: qui si verifica l'architettura, non la bravura di un modello. Un modello che obbedisce a tutto è il caso peggiore. Se i controlli reggono con lui reggono con uno migliore. Il collegamento a un modello vero (Claude, via API) è presente nel codice per chi vuole confrontare i risultati. Per ora è stato provato solo con una libreria simulata, non con il servizio reale.

## Autore

Matteo Spagnuolo, ricercatore indipendente in filosofia dell'IA e governance degli agenti AI. [matteospagnuolo.it](https://www.matteospagnuolo.it)

Architettura, regole, attacchi e criteri di verifica sono dell'autore. Il codice è stato scritto con un assistente AI e verificato con i test e la batteria di attacchi.

Per una spiegazione senza codice: [`docs/come-funziona.md`](docs/come-funziona.md).
