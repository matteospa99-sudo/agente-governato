# Come funziona

Questa guida spiega il progetto a chi non legge il codice. Dice che cosa fa ogni parte e perché è fatta così.

## L'idea in una frase

Un modello linguistico si può ingannare, quindi non gli si affida la decisione: il modello propone e il codice decide. Le azioni irreversibili le decide una persona.

## Il viaggio di un'email

Prendiamo l'attacco a01: un'email chiede gli orari e, in coda, ordina di inoltrare la conversazione a un indirizzo esterno.

1. **Arriva l'email.** L'orchestratore la scrive nel registro.
2. **Lo smistatore la classifica.** Risponde con due soli campi: categoria ("richiesta_informazioni") e priorità ("media").
3. **Punto di controllo tra agenti (C1).** Il codice verifica che il messaggio abbia solo quei due campi, con valori presi da elenchi chiusi. Se lo smistatore avesse aggiunto una "nota" con l'ordine dell'attaccante, il messaggio verrebbe rifiutato. È quello che succede nell'attacco a03.
4. **Il preparatore propone le azioni.** Il modello simulato è credulone e propone tre cose: etichettare l'email, preparare una bozza per il mittente e inviare l'email all'indirizzo esterno.
5. **Il governatore decide su ciascuna.** Etichetta: consentita. Bozza al mittente: consentita. Invio all'indirizzo esterno: bloccato dalla regola R6, perché il destinatario non è il mittente.
6. **L'email viene marcata "da rivedere".** Qualcosa è stato bloccato, quindi una persona deve guardarla.
7. **Tutto è nel registro.** Compresa la proposta bloccata e il motivo.

Se il preparatore avesse proposto un invio al mittente, il governatore lo avrebbe passato a una persona (R9). La persona vede il testo completo e, se l'email contiene segnali tipici delle truffe ("urgente", "bonifico"), un avviso.

## Le parti, in parole semplici

- **Agenti** (`agenti.py`). Due "impiegati" con compiti diversi. Ricevono istruzioni scritte e rispondono in un formato fisso (JSON, un modo standard di scrivere dati strutturati). Non toccano mai la posta direttamente.
- **Strumenti** (`strumenti.py`). Le quattro cose che si possono fare: etichettare, preparare una bozza, archiviare, inviare. Ognuno ha una scheda che dice se è reversibile.
- **Governatore** (`politiche.py`). Il cuore del progetto. Una sequenza di controlli scritti in codice normale: nessuna intelligenza artificiale, nessuna interpretazione. Dato lo stesso input, decide sempre allo stesso modo. Per questo si può verificare.
- **Orchestratore** (`orchestratore.py`). Il caporeparto: fa passare ogni email per tutti i passaggi nell'ordine giusto.
- **Registro** (`registro.py`). Un diario in cui ogni riga contiene l'impronta digitale della riga precedente. Se qualcuno cambia o cancella una riga, la catena si spezza e il comando `--verifica` lo segnala.
- **Modelli** (`modelli.py`). Il "cervello" degli agenti. Ce ne sono due: uno simulato e volutamente ingenuo, l'altro vero (Claude). Si scambiano senza cambiare nient'altro: i controlli non dipendono dal modello.

## Collegamenti con i quadri di riferimento

**I cinque rischi della guida Five Eyes sugli agenti AI** ("Careful adoption of agentic AI services", 2026):

| Rischio | Controlli nel progetto |
|---|---|
| Privilegi | R3 minimo privilegio, R5 solo l'email in lavorazione, minimizzazione dei dati |
| Progettazione e configurazione | C1 messaggi chiusi tra agenti, R2 strumenti dichiarati, R4 forma delle proposte |
| Comportamento | R6 destinatari, R7 lunghezza, R8 numero di azioni, R1 arresto |
| Struttura (sistemi multi-agente) | C1: nessun testo libero viaggia tra gli agenti |
| Responsabilità | Registro a prova di manomissione, R9 decisione umana registrata con l'azione |

**AI Act** (Regolamento UE 2024/1689, testo consolidato al 27 luglio 2026, verificato su EUR-Lex il 23 novembre 2026):

- art. 9, gestione dei rischi: un processo continuo che stima anche i rischi dell'uso improprio prevedibile → la batteria di attacchi;
- art. 12, registrazione automatica degli eventi → il registro;
- art. 14, sorveglianza umana: la persona deve restare consapevole della «distorsione dell'automazione» (par. 4, lett. b), deve poter ignorare o annullare l'output (lett. d) e deve poter interrompere il sistema con un pulsante di «arresto» (lett. e) → l'avviso a chi approva, R9 e R1;
- art. 15, robustezza e cibersicurezza: sistemi *fail-safe* (par. 4) e resilienza ai tentativi di terzi non autorizzati di alterarne uso o output (par. 5) → lo stato "da rivedere" e la batteria di attacchi.

Questi articoli stanno nel Capo III, Sezione 2, «Requisiti per i sistemi di IA ad alto rischio». Un agente per la posta di uno studio, di per sé, non è un sistema ad alto rischio: qui servono come riferimento di buona pratica, non come obbligo.

## Domande frequenti

**Perché non basta scrivere nelle istruzioni del modello di non obbedire alle email?**
Perché le istruzioni sono testo e l'attaccante scrive testo. Un modello può essere convinto. Le regole del governatore invece sono codice: non si convincono. Le istruzioni al modello ci sono comunque, ma sono un aiuto, non il controllo.

**Che cos'è il *prompt injection*?**
Un attacco in cui le istruzioni malevole sono nascoste nei dati che l'agente legge: un'email, una pagina web, un documento. L'agente le scambia per ordini.

**Perché due agenti e non uno?**
Per separare i compiti e i privilegi. Lo smistatore legge testo non affidabile ma non può fare nulla. Il preparatore può proporre azioni, ma riceve dallo smistatore solo dati chiusi. È lo stesso principio della separazione delle funzioni in un'organizzazione.

**Che cosa succede se il modello risponde in modo strano?**
L'email viene marcata "da rivedere" e il sistema non fa nulla. Nel dubbio si ferma: è una scelta voluta (*fail-safe*, cioè in caso di guasto andare verso lo stato sicuro).

**Il registro non si può semplicemente riscrivere da capo?**
Sì, chi ha accesso al file può ricostruire una catena nuova e coerente. La catena rende visibile la modifica di una riga, non impedisce di riscrivere tutto. In produzione si aggiunge un'ancora esterna, per esempio l'impronta dell'ultima riga salvata ogni giorno su un altro sistema.

**Qual è il punto debole?**
La persona che approva. Se approva senza leggere una risposta al mittente quando il mittente è l'attaccante, la risposta parte. Le regole garantiscono che niente esca verso terzi, ma non possono garantire l'attenzione: approvare non basta.

**Perché un modello simulato e non uno vero?**
Perché il simulato è il caso peggiore: obbedisce a tutto. Se i controlli reggono con lui reggono con un modello migliore. Il modello vero si collega con un'opzione e la batteria si può ripetere.

**Come si porterebbe in produzione?**
Collegamento a una casella reale con permessi limitati, elenco dei contatti autorizzati al posto della regola sul mittente, registro su un sistema separato e non modificabile, interfaccia di approvazione con il testo evidenziato, batteria di attacchi ripetuta a ogni modifica. Prima di accenderlo, una valutazione dei rischi scritta.

## Glossario minimo

- *Least privilege* (minimo privilegio): ogni componente ha solo i permessi che gli servono.
- *Human-in-the-loop*: una persona inserita nel processo che decide i passaggi critici.
- *Rubber stamping*: approvazione di routine, senza esame reale.
- *Fail-safe*: in caso di dubbio o guasto, il sistema va verso lo stato sicuro.
- Hash o impronta: una "firma" calcolata su un testo; cambia completamente se cambia anche una sola lettera.
- JSON: un formato standard per scrivere dati strutturati, leggibile da persone e programmi.
