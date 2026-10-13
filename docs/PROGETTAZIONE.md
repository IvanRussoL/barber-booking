# Progettazione – Barber Booking
 
## 1. Problema e utenti
 
Un salone di barbiere/parrucchiere gestisce gli appuntamenti per telefono o di persona: è facile sbagliare gli orari, sovrapporre due clienti dallo stesso dipendente o dimenticare chi ha già versato un acconto. L'applicazione permette ai clienti di prenotare online scegliendo servizio, dipendente e orario, e di acquistare i prodotti del salone da ritirare in negozio; al salone permette di gestire agende, pagamenti, ordini e statistiche in un unico posto.
 
Gli utenti sono quattro:
 
- **Visitatore (non registrato)**: può consultare il sito, ma non prenotare.
- **Cliente**: persona registrata che prenota servizi e acquista prodotti, pagando online.
- **Dipendente**: parrucchiere o barbiere del salone, con un'agenda propria.
- **Proprietario**: gestisce il salone; può essere anche parrucchiere e ricevere prenotazioni.
## 2. Requisiti funzionali
 
### Visitatore
- Consulta servizi, prezzi, orari del salone e posizione sulla mappa.
- Si registra o accede.
- Consulta il catalogo dei prodotti in vendita (shampoo, balsamo, gel, cera, schiuma da barba, profumi) con i prezzi.
### Tutti gli utenti registrati
- Cambiano la propria password inserendo quella attuale e la nuova.
### Cliente
- Prenota scegliendo uno o più servizi (es. taglio + barba), il dipendente e uno slot libero.
- Sceglie al momento della prenotazione se pagare un acconto o l'importo completo, online.
- Consulta nella propria area personale lo **storico delle prenotazioni** con il dettaglio dei servizi e lo **storico dei pagamenti**, con il totale speso.
- Annulla solo le proprie prenotazioni, fino a 2 ore prima, con rimborso.
- Acquista prodotti con un carrello separato dalle prenotazioni, paga online l'importo completo e li ritira in negozio (nessuna spedizione).
- Consulta nella propria area personale lo **storico degli ordini** e il loro stato (da ritirare, ritirato, annullato).
- Il totale speso comprende servizi e prodotti, al netto dei rimborsi; con "Dettagli" vede separatamente la spesa per i servizi e quella per i prodotti.
### Dipendente
- Accede con un profilo personale e vede **solo la propria agenda**.
- Nella propria pagina consulta le **statistiche del proprio lavoro**: clienti giornalieri, settimanali e mensili, con grafici sull'andamento (se le prenotazioni aumentano o diminuiscono).
- Non può prenotare presso altri dipendenti o presso il proprietario.
- Non può annullare prenotazioni né registrare assenze.
- Non gestisce prodotti e ordini.
### Proprietario
- Gestisce servizi (con durate e prezzi), dipendenti e orari di lavoro.
- Consulta le statistiche generali: prenotazioni per dipendente, occupazione, fasce di punta, ricavi, funnel visite → prenotazioni.
- Registra il saldo pagato in sede.
- Modifica i dati del salone, compresa la posizione sulla mappa (riservato al proprietario).
- Se lavora anche come parrucchiere, riceve prenotazioni come un dipendente; non può prenotare presso i dipendenti.
- Registra assenze dei dipendenti e chiusure del salone; annulla prenotazioni con rimborso.
- Gestisce il catalogo dei prodotti (nome, prezzo, disponibilità).
- Vede gli ordini da ritirare, registra il ritiro e annulla gli ordini con rimborso (es. prodotto esaurito).
## 3. Regole di business
 
### Prenotazioni
- Solo i **clienti registrati** possono prenotare.
- **Dipendenti e proprietario non possono prenotare** presso dipendenti o proprietario.
- Una prenotazione è assegnata a **un solo dipendente**, che esegue tutti i servizi scelti.
- Ogni servizio ha una **durata** e un prezzo, configurabili dal proprietario. La durata di una prenotazione con più servizi è la **somma** delle durate dei servizi scelti.
- Durate di esempio: taglio 30 minuti, barba 30 minuti, colore almeno 90 minuti. Quindi taglio + barba = 1 ora e taglio + barba + colore = 150 minuti.
- Le durate dei servizi sono **multipli di 30 minuti**, come la griglia degli appuntamenti, così l'agenda non ha buchi non prenotabili.
- **Tutti i dipendenti eseguono tutti i servizi**: il cliente può scegliere qualsiasi dipendente per qualsiasi combinazione di servizi.
- Gli slot liberi si calcolano **per singolo dipendente**.
- Un dipendente non può avere due prenotazioni sovrapposte: il controllo avviene **nella stessa transazione** che crea la prenotazione, per evitare doppie prenotazioni in caso di richieste simultanee.
### Orari e disponibilità
- Il proprietario imposta il **calendario settimanale** del salone: per ogni giorno della settimana indica se è aperto o chiuso e quali turni ha (es. 09:00–13:00 e 15:00–23:00). Il calendario è unico per tutti i dipendenti.
- Valore di partenza: **lunedì chiuso**; gli altri giorni aperti con i turni 09:00–13:00 e 15:00–23:00. Il proprietario può cambiarlo (per esempio chiudere il martedì o la domenica).
- Il proprietario può inserire **eccezioni per una data precisa**: un giorno normalmente chiuso reso apribile (con i suoi turni) oppure un giorno normalmente aperto reso chiuso.
- Nei giorni chiusi e fuori dai turni non è possibile prenotare. La regola è verificata sul server in fase di calcolo degli slot e di creazione della prenotazione, non solo nell'interfaccia.
- Gli appuntamenti possono iniziare ogni **30 minuti**. Un appuntamento deve stare per intero dentro un turno: non può attraversare la pausa tra due turni né finire dopo la chiusura.
- **Finestra di prenotazione**: il cliente può prenotare da oggi fino all'**ultimo giorno del mese che viene N mesi dopo quello corrente**, dove N lo sceglie il proprietario da 0 a 3. Esempio con N = 3: il 1° settembre si può prenotare fino al 31 dicembre. Il primo giorno di ogni mese si aggiunge un mese nuovo.
- **Assenze del dipendente** (malattia, ferie): il proprietario registra un periodo (giorni o ore) in cui non riceve prenotazioni; la sua card mostra un segno di indisponibilità.
- **Chiusure del salone** (ferie): periodo di più giorni consecutivi in cui nessuno riceve prenotazioni.
- Le chiusure del salone non fanno eccezione alla finestra: le date successive alla riapertura si prenotano quando si apre il mese che le contiene.
- Il proprietario sceglie il **fuso orario** del salone; le regole che dipendono dall'ora (annullamento a 2 ore, scadenza del pagamento, finestra di prenotazione) si calcolano in quel fuso.
- Il **calendario settimanale** e le **eccezioni per data** non si possono modificare nei giorni che hanno già prenotazioni confermate: il proprietario deve prima contattare i clienti (hanno telefono ed email) e annullare le prenotazioni, con rimborso. Le **assenze** dei dipendenti e le **chiusure per ferie** seguono invece la procedura con elenco e conferma descritta in "Annullamenti".
### Pagamenti
- Il pagamento online è obbligatorio, in modalità test.
- Il cliente sceglie se pagare un **acconto** (percentuale configurabile dal proprietario, resto in sede) oppure l'**importo completo**.
- Gli importi sono **calcolati sempre dal server**, mai presi dai dati inviati dal browser.
- Una prenotazione nasce `in_attesa_pagamento` e viene confermata solo dalla notifica del provider di pagamento (webhook con firma verificata, gestito in modo idempotente).
- Una prenotazione `in_attesa_pagamento` blocca lo slot per **30 minuti**; se il pagamento non arriva, decade e lo slot torna libero.
- Se il cliente **esce dalla procedura di pagamento**, la prenotazione in attesa viene annullata subito, lo slot torna libero e la sessione di pagamento viene chiusa, così non può più essere pagata.
- Se un pagamento arriva per una prenotazione già decaduta o annullata, viene **rimborsato automaticamente** e la prenotazione non viene confermata.
- Stati del pagamento: `acconto_pagato`, `saldato`. Il saldo in sede lo registra il proprietario.
### Prodotti e ordini
- Solo i **clienti registrati** possono acquistare prodotti.
- Il carrello dei prodotti è **separato dalle prenotazioni**: ogni pagamento riguarda una prenotazione oppure un ordine, mai entrambi.
- Un prodotto si può acquistare solo se è **disponibile**; la disponibilità (sì/no) la imposta il proprietario.
- I prodotti si pagano **solo online e per intero**, senza acconto.
- Per il pagamento valgono le stesse regole delle prenotazioni: l'ordine nasce `in_attesa_pagamento`, viene confermato solo dal webhook, decade dopo 30 minuti senza pagamento e, se il pagamento arriva tardi, viene rimborsato automaticamente.
- I prodotti si **ritirano in negozio**; il ritiro lo registra il proprietario.
- Il cliente non può annullare un ordine. Solo il proprietario lo annulla, rimborsando **esattamente quanto pagato**.
- Il prezzo di ogni prodotto è fissato nell'ordine al momento dell'acquisto e non cambia se il proprietario modifica il catalogo.
### Annullamenti, assenze e chiusure
- Il cliente annulla **solo le proprie** prenotazioni, fino a **2 ore prima** dell'inizio dell'appuntamento.
- **Solo il proprietario** annulla prenotazioni per conto del salone e registra le assenze dei dipendenti e le chiusure del salone. I dipendenti non possono farlo.
- In ogni annullamento il cliente è rimborsato di **esattamente quanto ha pagato** (solo l'acconto, o l'importo completo).
- Se un'assenza o una chiusura copre prenotazioni già confermate, il sistema mostra al proprietario l'elenco delle prenotazioni coinvolte e le annulla, con rimborso, **solo dopo la sua conferma esplicita**.
### Accessi
- Il cliente vede e annulla **solo le proprie** prenotazioni.
- Il cliente vede **solo i propri** ordini.
- Il dipendente vede **solo la propria** agenda e le proprie statistiche.
- Il primo proprietario si crea da riga di comando, non da una pagina pubblica.
## 4. Modello dei dati (tabelle e relazioni)

Convenzione: tutte le colonne DATETIME sono salvate in **UTC**. Il server le converte nel fuso orario del salone solo per mostrarle e per i calcoli su turni, griglia e finestra di prenotazione. I valori predefiniti di `creato_il` li scrive MySQL con `UTC_TIMESTAMP()`, quindi sono in UTC qualunque sia il fuso orario della connessione.

### Tabella `utenti`

Contiene tutte le persone che accedono al sito: clienti, dipendenti e proprietario.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco dell'utente |
| `email` | VARCHAR(255), obbligatoria, univoca | Indirizzo email usato per il login; non possono esistere due utenti con la stessa email |
| `password_hash` | VARCHAR(255), obbligatoria | Hash della password generato con Werkzeug; la password in chiaro non viene mai salvata |
| `nome` | VARCHAR(100), obbligatoria | Nome della persona |
| `cognome` | VARCHAR(100), obbligatoria | Cognome della persona |
| `telefono` | VARCHAR(20), obbligatoria | Numero di telefono con prefisso internazionale (es. +39...), usato dal salone per contattare l'utente |
| `ruolo` | ENUM('cliente', 'dipendente', 'proprietario'), obbligatoria, predefinito 'cliente' | Determina i permessi dell'utente ed è la base del controllo degli accessi; lo assegna solo il server, mai un modulo inviato dal browser |
| `riceve_prenotazioni` | BOOLEAN, obbligatoria, predefinito no | Indica se la persona è un professionista prenotabile con una propria agenda (dipendenti e proprietario che lavora in sala); la modifica solo il proprietario |
| `attivo` | BOOLEAN, obbligatoria, predefinito sì | Se vale no l'account non può accedere e non è prenotabile; si disattiva invece di cancellare, per conservare lo storico |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento di creazione dell'account, scritto automaticamente dal database |

### Tabella `servizi`

Contiene i servizi offerti dal salone, con durata e prezzo attuali. Li gestisce solo il proprietario.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del servizio |
| `nome` | VARCHAR(100), obbligatoria, univoca | Nome mostrato ai clienti (es. "Taglio"); univoco per evitare due servizi con lo stesso nome |
| `descrizione` | VARCHAR(255), facoltativa | Breve descrizione mostrata nella pagina dei servizi |
| `durata_minuti` | INT, obbligatoria, maggiore di 0 e multiplo di 30 | Durata del servizio in minuti; multiplo di 30 per restare allineata alla griglia degli appuntamenti senza lasciare buchi non prenotabili; la durata di una prenotazione è la somma delle durate dei servizi scelti |
| `prezzo_centesimi` | INT, obbligatoria, maggiore o uguale a 0 | Prezzo attuale in centesimi di euro (2500 = 25,00 €), nell'unità richiesta da Stripe; evita gli errori di arrotondamento dei numeri decimali |
| `attivo` | BOOLEAN, obbligatoria, predefinito sì | Se vale no il servizio non è più prenotabile; si disattiva invece di cancellare, per conservare lo storico delle prenotazioni |

### Tabella `prenotazioni`

Contiene gli appuntamenti: chi prenota, presso quale dipendente, quando e in quale stato. I servizi scelti sono nella tabella di collegamento `prenotazioni_servizi`.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco della prenotazione |
| `cliente_id` | INT, obbligatoria, chiave esterna verso `utenti.id` | Il cliente che ha prenotato; il codice verifica che abbia ruolo cliente |
| `dipendente_id` | INT, obbligatoria, chiave esterna verso `utenti.id` | Il professionista che esegue tutti i servizi; il codice verifica che riceva prenotazioni e sia attivo |
| `inizio` | DATETIME, obbligatoria | Data e ora di inizio, allineata alla griglia di 30 minuti |
| `fine` | DATETIME, obbligatoria, successiva a `inizio` | Data e ora di fine, fissata alla creazione come inizio + somma delle durate; usata per il controllo anti-sovrapposizione |
| `stato` | ENUM('in_attesa_pagamento', 'confermata', 'scaduta', 'annullata'), obbligatoria, predefinito 'in_attesa_pagamento' | Ciclo di vita della prenotazione; diventa 'confermata' solo tramite il webhook del pagamento |
| `modalita_pagamento` | ENUM('acconto', 'completo'), obbligatoria | Scelta del cliente al momento della prenotazione; gli importi li calcola il server |
| `scade_il` | DATETIME, obbligatoria | Momento oltre il quale una prenotazione in attesa di pagamento decade e libera lo slot (creazione + 30 minuti) |
| `annullata_il` | DATETIME, facoltativa | Momento dell'annullamento; vuota se la prenotazione non è annullata |
| `annullata_da` | ENUM('cliente', 'salone'), facoltativa | Chi ha annullato; serve per lo storico e le statistiche |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento di creazione della prenotazione |

Indici: (`dipendente_id`, `inizio`) per il calcolo degli slot e il controllo delle sovrapposizioni; `cliente_id` per lo storico del cliente.

### Tabella `prenotazioni_servizi`

Collega ogni prenotazione ai servizi scelti e conserva durata e prezzo applicati al momento della prenotazione.

| Colonna | Tipo | Significato |
|---|---|---|
| `prenotazione_id` | INT, obbligatoria, chiave esterna verso `prenotazioni.id` | La prenotazione a cui appartiene il servizio |
| `servizio_id` | INT, obbligatoria, chiave esterna verso `servizi.id` | Il servizio scelto |
| `durata_minuti` | INT, obbligatoria | Durata del servizio al momento della prenotazione |
| `prezzo_centesimi` | INT, obbligatoria | Prezzo al momento della prenotazione; non cambia se il proprietario modifica i prezzi in seguito. Il totale della prenotazione è la somma di questa colonna |

Chiave primaria composta (`prenotazione_id`, `servizio_id`): lo stesso servizio non può comparire due volte nella stessa prenotazione.

### Tabella `orari_settimanali`

Contiene il calendario settimanale del salone, unico per tutti i dipendenti: una riga per ogni turno. Un giorno senza righe è chiuso.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del turno |
| `giorno_settimana` | TINYINT, obbligatoria, da 1 (lunedì) a 7 (domenica) | Giorno della settimana, con la stessa numerazione di `isoweekday()` di Python |
| `ora_inizio` | TIME, obbligatoria | Inizio del turno, nell'ora locale del salone (non in UTC) |
| `ora_fine` | TIME, obbligatoria, successiva a `ora_inizio` | Fine del turno, nell'ora locale del salone |

Il codice verifica che i turni dello stesso giorno non si sovrappongano e che inizio e fine cadano sulla griglia di 30 minuti.

### Tabella `eccezioni_date`

Contiene le date in cui il calendario settimanale non vale: un giorno normalmente aperto reso chiuso, o un giorno normalmente chiuso reso aperto. Se una data è qui, conta solo l'eccezione.

| Colonna | Tipo | Significato |
|---|---|---|
| `data` | DATE, chiave primaria | Il giorno dell'eccezione, nella data locale del salone; chiave primaria perché ogni data può avere una sola eccezione |
| `aperto` | BOOLEAN, obbligatoria | Se vale no il salone è chiuso quel giorno; se vale sì è aperto con i turni indicati in `eccezioni_turni` |
| `nota` | VARCHAR(255), facoltativa | Motivo dell'eccezione (es. "Apertura straordinaria per le feste"), utile al proprietario |

### Tabella `eccezioni_turni`

Contiene i turni delle date eccezionali in cui il salone è aperto: una riga per ogni turno.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del turno |
| `data` | DATE, obbligatoria, chiave esterna verso `eccezioni_date.data` | La data eccezionale a cui appartiene il turno |
| `ora_inizio` | TIME, obbligatoria | Inizio del turno, nell'ora locale del salone |
| `ora_fine` | TIME, obbligatoria, successiva a `ora_inizio` | Fine del turno, nell'ora locale del salone |

Il codice verifica che i turni esistano solo per date con `aperto` = sì, che non si sovrappongano e che cadano sulla griglia di 30 minuti.
Se una data viene eliminata da `eccezioni_date`, i suoi turni vengono cancellati automaticamente dal database (`ON DELETE CASCADE`).

### Tabella `indisponibilita`

Contiene i periodi in cui non si ricevono prenotazioni: assenze di un dipendente (malattia, ferie) e chiusure dell'intero salone. Le registra solo il proprietario.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del periodo |
| `dipendente_id` | INT, facoltativa, chiave esterna verso `utenti.id` | Il dipendente assente; se è vuota il periodo è una chiusura dell'intero salone |
| `inizio` | DATETIME, obbligatoria | Inizio del periodo; può essere un giorno intero o solo alcune ore |
| `fine` | DATETIME, obbligatoria, successiva a `inizio` | Fine del periodo |
| `nota` | VARCHAR(255), facoltativa | Breve nota per il proprietario (es. "Ferie estive") |

Indice: (`dipendente_id`, `inizio`) per il calcolo degli slot.

### Tabella `pagamenti`

Contiene i movimenti di denaro legati alle prenotazioni e agli ordini di prodotti: pagamenti online, saldi in sede e rimborsi, una riga per movimento. Per le prenotazioni, gli stati `acconto_pagato` e `saldato` non si salvano: si calcolano confrontando la somma dei movimenti completati con il totale della prenotazione.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del movimento |
| `prenotazione_id` | INT, facoltativa, chiave esterna verso `prenotazioni.id` | La prenotazione a cui si riferisce il movimento; vuota se il movimento riguarda un ordine |
| `ordine_id` | INT, facoltativa, chiave esterna verso `ordini.id` | L'ordine di prodotti a cui si riferisce il movimento; vuota se il movimento riguarda una prenotazione |
| `tipo` | ENUM('online', 'in_sede', 'rimborso'), obbligatoria | Pagamento online tramite il provider, saldo registrato dal proprietario in sede, oppure rimborso |
| `importo_centesimi` | INT, obbligatoria, maggiore di 0 | Importo in centesimi, calcolato sempre dal server; per i rimborsi è l'importo restituito |
| `stato` | ENUM('in_attesa', 'completato', 'fallito'), obbligatoria, predefinito 'in_attesa' | Un pagamento online diventa 'completato' solo tramite il webhook; un saldo in sede nasce già 'completato' |
| `riferimento_provider` | VARCHAR(255), facoltativa, univoca | Identificativo della sessione di pagamento o del rimborso presso il provider (Stripe o PayPal); vuoto per i saldi in sede. Essendo univoco, un webhook ripetuto ritrova la stessa riga invece di crearne una nuova |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento in cui il movimento è stato registrato |

Vincoli (CHECK): deve essere compilata esattamente una tra `prenotazione_id` e `ordine_id`; i saldi in sede (`tipo` = 'in_sede') riguardano solo le prenotazioni, perché i prodotti si pagano solo online.

### Tabella `impostazioni`

Contiene i dati e le regole configurabili del salone. Ha una sola riga, modificabile solo dal proprietario.
La riga viene creata da `schema.sql` con valori di partenza che il proprietario modifica dal sito; lo stesso script inserisce il calendario settimanale di partenza descritto nella sezione 3.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | TINYINT, chiave primaria, vale sempre 1 | Garantisce che esista una sola riga di impostazioni |
| `nome_salone` | VARCHAR(100), obbligatoria | Nome mostrato sul sito |
| `indirizzo` | VARCHAR(255), obbligatoria | Indirizzo mostrato ai visitatori |
| `telefono` | VARCHAR(20), obbligatoria | Telefono del salone, con prefisso internazionale |
| `fuso_orario` | VARCHAR(64), obbligatoria, predefinito 'Europe/Rome' | Nome del fuso orario (formato IANA, usato dal modulo `zoneinfo` di Python); serve a convertire le date salvate in UTC e a calcolare le regole che dipendono dall'ora |
| `latitudine` | DECIMAL(9,6), obbligatoria | Latitudine del salone per la mappa |
| `longitudine` | DECIMAL(9,6), obbligatoria | Longitudine del salone per la mappa |
| `percentuale_acconto` | TINYINT, obbligatoria, da 1 a 99 | Percentuale del totale da pagare online se il cliente sceglie l'acconto; l'importo in centesimi lo calcola il server |
| `mesi_prenotabili` | TINYINT, obbligatoria, da 0 a 3, predefinito 3 | Quanti mesi dopo quello corrente sono prenotabili: con 0 solo il mese corrente, con 3 fino alla fine del terzo mese successivo |

### Tabella `eventi`

Contiene le visite alle pagine e i click, per le statistiche e il funnel visite → prenotazioni. Non salva indirizzi IP né l'identità dell'utente.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | BIGINT, chiave primaria, auto-incrementale | Identificativo dell'evento; BIGINT perché è la tabella che cresce più in fretta |
| `tipo` | VARCHAR(50), obbligatoria | Tipo di evento: 'visita_pagina' o 'click'; il server accetta solo i tipi di un elenco fisso |
| `pagina` | VARCHAR(255), obbligatoria | Percorso della pagina (es. '/servizi'), senza parametri, per non registrare dati personali |
| `elemento` | VARCHAR(100), facoltativa | Per i click, quale pulsante o link è stato premuto |
| `sessione` | VARCHAR(64), obbligatoria | Identificativo casuale del visitatore, salvato nella sessione; serve a contare i visitatori unici |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento dell'evento |

Indice: (`tipo`, `creato_il`) per le statistiche per periodo.

### Tabella `prodotti`

Contiene i prodotti in vendita nel salone. Li gestisce solo il proprietario.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del prodotto |
| `nome` | VARCHAR(100), obbligatoria, univoca | Nome mostrato ai clienti (es. "Cera opaca 100 ml") |
| `descrizione` | VARCHAR(255), facoltativa | Breve descrizione mostrata nel catalogo |
| `foto` | VARCHAR(100), facoltativa | Nome del file della foto, generato dal server con un identificativo casuale; vuota se il prodotto non ha foto |
| `prezzo_centesimi` | INT, obbligatoria, maggiore di 0 | Prezzo attuale in centesimi di euro, come per i servizi |
| `disponibile` | BOOLEAN, obbligatoria, predefinito sì | Se vale no il prodotto compare nel catalogo come esaurito e non si può aggiungere al carrello |
| `attivo` | BOOLEAN, obbligatoria, predefinito sì | Se vale no il prodotto non compare più nel catalogo; si disattiva invece di cancellare, per conservare lo storico degli ordini |

### Tabella `ordini`

Contiene gli acquisti di prodotti dei clienti. I prodotti acquistati sono nella tabella di collegamento `ordini_prodotti`.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco dell'ordine |
| `cliente_id` | INT, obbligatoria, chiave esterna verso `utenti.id` | Il cliente che ha acquistato; il codice verifica che abbia ruolo cliente |
| `stato` | ENUM('in_attesa_pagamento', 'confermato', 'ritirato', 'scaduto', 'annullato'), obbligatoria, predefinito 'in_attesa_pagamento' | Ciclo di vita dell'ordine; diventa 'confermato' (pagato, da ritirare) solo tramite il webhook del pagamento |
| `scade_il` | DATETIME, obbligatoria | Momento oltre il quale un ordine in attesa di pagamento decade (creazione + 30 minuti) |
| `ritirato_il` | DATETIME, facoltativa | Momento in cui il proprietario ha registrato il ritiro |
| `annullato_il` | DATETIME, facoltativa | Momento dell'annullamento; vuota se l'ordine non è annullato |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento di creazione dell'ordine |

Indici: `cliente_id` per lo storico del cliente; `stato` per l'elenco degli ordini da ritirare.

### Tabella `ordini_prodotti`

Collega ogni ordine ai prodotti acquistati e conserva prezzo e quantità al momento dell'acquisto.

| Colonna | Tipo | Significato |
|---|---|---|
| `ordine_id` | INT, obbligatoria, chiave esterna verso `ordini.id` | L'ordine a cui appartiene la riga |
| `prodotto_id` | INT, obbligatoria, chiave esterna verso `prodotti.id` | Il prodotto acquistato |
| `quantita` | INT, obbligatoria, da 1 a 10 | Numero di pezzi acquistati |
| `prezzo_centesimi` | INT, obbligatoria | Prezzo di un pezzo al momento dell'acquisto; non cambia se il proprietario modifica il catalogo |

Chiave primaria composta (`ordine_id`, `prodotto_id`): lo stesso prodotto compare una sola volta nell'ordine, con la sua quantità. Il totale dell'ordine è la somma di `quantita` × `prezzo_centesimi`.

## 5. Modello a oggetti (classi e ruolo dell'OOP)
Le classi sono divise in quattro gruppi, ognuno con un solo compito. Le rotte Flask restano sottili: leggono la richiesta, chiamano un servizio e mostrano il risultato.

### Modelli

Classi definite con `@dataclass` che rappresentano una riga del database (es. `Utente`, `Servizio`, `Prenotazione`). Contengono i dati e pochi metodi semplici che li riguardano (es. la durata totale di una prenotazione). Non eseguono query.

| Modello | Tabella | Differenze rispetto alle colonne della sezione 4 |
|---|---|---|
| `Utente` | `utenti` | Nessuna |
| `Servizio` | `servizi` | Nessuna |
| `Prenotazione` | `prenotazioni` | Contiene la lista dei suoi `ServizioPrenotato`; metodi per durata totale e prezzo totale (somme dei servizi) |
| `ServizioPrenotato` | `prenotazioni_servizi` | Include anche il nome del servizio, letto da `servizi`, per mostrarlo nello storico |
| `Turno` | `orari_settimanali`, `eccezioni_turni` | Solo `ora_inizio` e `ora_fine`: il giorno lo indica chi chiede i turni |
| `EccezioneData` | `eccezioni_date` | Contiene la lista dei suoi `Turno` |
| `Indisponibilita` | `indisponibilita` | Nessuna |
| `Pagamento` | `pagamenti` | Nessuna |
| `Impostazioni` | `impostazioni` | Nessuna |
| `Prodotto` | `prodotti` | Nessuna |
| `Ordine` | `ordini` | Contiene la lista dei suoi `ProdottoOrdinato`; metodo per il totale (somma di quantità × prezzo) |
| `ProdottoOrdinato` | `ordini_prodotti` | Include anche il nome del prodotto, letto da `prodotti`, per mostrarlo nello storico |

La tabella `eventi` non ha un modello: si scrive con un semplice INSERT e si legge solo per le statistiche, caricandola direttamente in un DataFrame di pandas.

Ho scelto una sola classe `Utente` con il campo `ruolo`, senza sottoclassi per cliente, dipendente e proprietario: i tre ruoli hanno gli stessi dati, il proprietario può anche ricevere prenotazioni come un dipendente, e i permessi li decide il controllo degli accessi, non la classe. Ho usato l'ereditarietà solo dove le classi hanno comportamenti diversi: `PaymentProvider` e le eccezioni.


### Repository

Una classe per ogni gruppo di tabelle (es. `UtenteRepository`, `PrenotazioneRepository`). Contengono tutte le query SQL, sempre parametrizzate, e trasformano le righe del database in modelli. Sono l'unico posto del progetto in cui si scrive SQL.

### Servizi

Contengono le regole di business della sezione 3: calcolo degli slot liberi, creazione della prenotazione con controllo anti-sovrapposizione nella stessa transazione, annullamenti e rimborsi. Usano i repository e non dipendono da Flask, quindi si testano con pytest senza avviare il sito.

| Servizio | Compito |
|---|---|
| `AuthService` | Registrazione e login: hash della password, controllo che l'account sia attivo |
| `DisponibilitaService` | Slot liberi di un dipendente in una data, considerando finestra del mese, turni, indisponibilità e prenotazioni esistenti (comprese quelle in attesa di pagamento non scadute) |
| `PrenotazioneService` | Creazione della prenotazione con controllo anti-sovrapposizione nella stessa transazione, annullamento (regola delle 2 ore per il cliente), decadenza delle prenotazioni scadute |
| `OrdineService` | Creazione dell'ordine dal carrello con prezzi calcolati dal server e controllo di disponibilità e quantità, registrazione del ritiro, annullamento con rimborso, decadenza degli ordini scaduti |
| `PagamentoService` | Avvio del pagamento tramite `PaymentProvider` per prenotazioni e ordini, gestione idempotente del webhook, saldo in sede, calcolo dello stato del pagamento, rimborsi |
| `SaloneService` | Operazioni del proprietario su servizi, prodotti (con il salvataggio sicuro delle foto tramite Pillow), orari, eccezioni, assenze e chiusure, con le regole della sezione 3 |
| `StatisticheService` | Lettura di eventi e prenotazioni con pandas e creazione dei grafici con matplotlib |

Ho raccolto le operazioni del proprietario in un solo servizio perché sono brevi e simili: dividerle creerebbe classi quasi vuote. Se una diventerà complessa, la sposterò in un servizio a parte.

### Provider di pagamento

Classe astratta `PaymentProvider` (modulo `abc`) che definisce le operazioni di pagamento comuni a tutti i provider (es. creare una sessione di pagamento, verificare una notifica, rimborsare). Ha due implementazioni: `StripeProvider` per l'uso reale in modalità test e `FakeProvider` per i test automatici. I servizi usano solo la classe astratta, quindi aggiungere un provider (es. PayPal nella fase 7b) non richiede di modificarli.

### Eccezioni personalizzate

Il modulo `eccezioni.py` definisce una classe base, `BarberBookingError`, e le eccezioni specifiche che ne derivano (es. `SlotNonDisponibileError`). I servizi le sollevano quando una regola di business è violata; un gestore centrale registrato con `@app.errorhandler` le trasforma in un messaggio per l'utente o in un codice HTTP. Creo una nuova eccezione solo se va gestita in modo diverso dalle altre.
 
## 6. Struttura del progetto Flask
### Cartelle

```
barber-booking/
├── app/
│   ├── __init__.py        # create_app(): crea e configura l'applicazione
│   ├── modelli/           # classi @dataclass
│   ├── repository/        # query SQL
│   ├── servizi/           # regole di business
│   ├── pagamenti/         # PaymentProvider e implementazioni
│   ├── rotte/             # Blueprint, uno per area
│   ├── templates/         # pagine Jinja
│   ├── static/            # CSS, JavaScript, immagini del sito, foto dei prodotti
│   ├── eccezioni.py
│   └── db.py              # connessione a MySQL
├── database/
│   └── schema.sql         # creazione delle tabelle
├── tests/
├── docs/
├── DEVLOG.md
├── README.md
├── requirements.txt
├── .env                   # segreti, escluso da Git
└── run.py                 # avvio in sviluppo
```

Le cartelle dentro `app/` seguono i gruppi di classi della sezione 5.

### Blueprint

Le rotte sono divise in Blueprint, uno per area. Ogni Blueprint ha un prefisso nell'URL e, se è riservato, un controllo in `before_request` che Flask esegue prima di ogni sua rotta: così ogni rotta aggiunta in seguito è protetta senza doverlo ricordare (regola "nega per default").

| Blueprint | Prefisso | Accesso | Contenuto |
|---|---|---|---|
| `pubblico` | `/` | Tutti | Home, servizi, catalogo prodotti, mappa |
| `auth` | `/auth` | Tutti | Login, registrazione, logout |
| `account` | `/account` | Tutti gli utenti loggati | Cambio password |
| `cliente` | `/cliente` | Clienti loggati | Prenotazione, carrello, area personale, storico |
| `dipendente` | `/dipendente` | Dipendenti, e proprietario con `riceve_prenotazioni` attivo | Agenda e statistiche personali |
| `proprietario` | `/proprietario` | Solo il proprietario | Gestione del salone, ordini, statistiche generali |
| `webhook` | `/webhook` | Provider di pagamento | Notifiche di pagamento |

Gli endpoint chiamati da JavaScript con fetch stanno nel Blueprint della loro area e ne ereditano il controllo. Un visitatore non loggato che apre una rotta riservata viene mandato al login; un utente con il ruolo sbagliato riceve 403.

Il Blueprint `webhook` non usa login né protezione CSRF, perché le richieste arrivano dal provider e non da un modulo del sito: la protezione è la verifica della firma di ogni notifica.

### Application factory

L'applicazione Flask non è creata a livello di modulo, ma dalla funzione `create_app()` in `app/__init__.py`, che riceve la configurazione, registra i Blueprint e il gestore delle eccezioni e restituisce l'app. Così i test creano un'app separata con un database di prova e il `FakeProvider`, senza toccare la configurazione reale.

Le foto dei prodotti caricate dal proprietario sono escluse da Git: sono dati, non codice.
 
## 7. Sicurezza e controllo accessi

### Autenticazione e sessione

- **Password**: salvate solo come hash con Werkzeug (`generate_password_hash`, `check_password_hash`), lunghezza minima di 8 caratteri.
- **Login senza librerie esterne**: ho scelto di gestirlo con la sessione di Flask. Dopo il controllo della password la sessione viene svuotata e riceve solo l'`id` dell'utente. Svuotarla impedisce di riusare una sessione creata prima del login (session fixation). Il logout svuota la sessione.
- **Utente ricaricato a ogni richiesta**: un `before_request` dell'app legge l'utente dal database tramite l'`id` in sessione. Così un account disattivato o un ruolo cambiato hanno effetto subito, senza aspettare un nuovo login.
- **Messaggio di errore generico** ("email o password non corretti"): non rivela se un'email è registrata.
- **Cookie di sessione** con `HttpOnly` (non leggibile da JavaScript), `SameSite=Lax` (non inviato da altri siti nelle richieste POST) e `Secure` in produzione (solo HTTPS).
- **Rate limiting con Flask-Limiter**: al massimo 5 tentativi di login al minuto per indirizzo IP, e un limite anche sulla registrazione. L'IP serve solo a contare i tentativi e non viene salvato nel database.
- **Ruoli assegnati solo dal server**: la registrazione pubblica crea sempre un cliente; i dipendenti li crea il proprietario; il primo proprietario si crea con un comando da terminale (`flask crea-proprietario`), non da una pagina del sito.
- **Cambio password**: richiede la password attuale, così chi trova una sessione aperta su un computer altrui non può cambiarla. I dipendenti ricevono dal proprietario una password iniziale e possono cambiarla al primo accesso.

### Controllo accessi

Il controllo avviene sempre sul server e su due livelli; nascondere link o pulsanti serve solo all'interfaccia.

- **Ruolo**: ogni Blueprint riservato verifica l'utente nel proprio `before_request`. Anonimo → redirect al login; ruolo sbagliato → 403.
- **Proprietà dei dati**: l'identità dell'utente si prende sempre dalla sessione, mai dall'URL o da un modulo. Le query del cliente includono il suo `id` nella condizione (es. `WHERE id = %s AND cliente_id = %s`), così una prenotazione o un ordine di un altro cliente risulta semplicemente non trovato (404). Allo stesso modo l'agenda e le statistiche di un dipendente si leggono con il suo `id` di sessione. Questo impedisce di accedere ai dati altrui cambiando un numero nell'URL (IDOR).
- **Grafici e report**: generati in memoria e restituiti da rotte protette, mai salvati in `static/`.
- **Test degli accessi**: un test pytest scorre tutte le rotte registrate nell'app e verifica che quelle riservate rispondano correttamente ad anonimo, cliente e dipendente. Una rotta nuova finisce nel test automaticamente.

### Protezione delle richieste

- **CSRF**: `CSRFProtect` di Flask-WTF protegge tutti i moduli e le richieste POST. Le chiamate fetch inviano il token in un'intestazione, letto da un tag `<meta>` della pagina. Unica eccezione: il Blueprint `webhook`.
- **SQL injection**: tutte le query usano parametri (`%s`) passati separatamente al driver, mai stringhe composte con i dati dell'utente.
- **XSS**: Jinja applica l'escape automatico a tutti i dati nelle pagine; il filtro `|safe` non si usa mai su dati inseriti dagli utenti. In JavaScript i dati ricevuti si inseriscono con `textContent`, non con `innerHTML`.
- **Validazione sul server**: ogni dato ricevuto è controllato dal server (tipi, lunghezze, valori ammessi), anche quando il modulo HTML ha già i suoi controlli, perché quelli del browser si aggirano facilmente.
- **Upload delle foto**: dimensione massima della richiesta (`MAX_CONTENT_LENGTH`); solo JPEG, PNG e WebP, riconosciuti aprendo il file con Pillow e non dall'estensione; nome del file generato dal server; immagine risalvata da Pillow per eliminare contenuti nascosti e metadati.

### Segreti e configurazione

- **Segreti solo nel file `.env`**, escluso da Git e letto all'avvio con `python-dotenv`: `SECRET_KEY` di Flask, credenziali del database, chiavi di Stripe e segreto del webhook. Nel repository c'è solo `.env.example`, con i nomi delle variabili e valori finti, per mostrare cosa configurare.
- **`SECRET_KEY` lunga e casuale**, generata con il modulo `secrets` di Python: firma il cookie di sessione, quindi chi la conosce può falsificare un login.
- **Utente MySQL dedicato all'app**, con permessi solo sul database del progetto, mai `root`.
- **Modalità debug solo in sviluppo**: il debugger di Flask permette di eseguire codice dal browser, quindi in produzione è spento e gli errori mostrano una pagina generica, senza dettagli tecnici.
- **Solo chiavi di test di Stripe**: il progetto non usa mai chiavi reali.

### Pagamenti

- **Importi calcolati dal server**: il browser invia solo cosa si vuole acquistare (servizi, prodotti e quantità, modalità acconto o completo); prezzi, acconto e totale li calcola il server dal database.
- **Dati della carta mai sul nostro server**: il pagamento avviene sulla pagina di Stripe Checkout, quindi l'app non vede né salva numeri di carta.
- **Conferma solo dal webhook**: la pagina di ritorno dopo il pagamento mostra un messaggio, ma non conferma nulla. Prenotazioni e ordini diventano confermati solo quando arriva la notifica di Stripe.
- **Firma del webhook verificata**: ogni notifica viene controllata con il segreto del webhook; una notifica senza firma valida viene scartata.
- **Importo ricontrollato**: alla conferma, l'importo pagato deve coincidere con quello atteso salvato in `pagamenti`; se è diverso, la prenotazione o l'ordine non viene confermato.
- **Idempotenza**: il pagamento si ritrova tramite `riferimento_provider`, che è univoco; una notifica ripetuta trova il pagamento già completato e non produce effetti.
- **Rimborsi decisi dal server**: l'importo rimborsato è sempre quanto risulta pagato nei movimenti, mai un valore inviato dal browser.
 
## 8. Statistiche

### Quali statistiche

Contano solo le prenotazioni `confermate`. Il periodo da analizzare (es. un mese) lo sceglie chi consulta le statistiche.

**Proprietario**

| Statistica | Calcolo | Grafico |
|---|---|---|
| Prenotazioni per dipendente | Prenotazioni confermate nel periodo, per dipendente | Barre |
| Occupazione | Ore prenotate del dipendente ÷ ore di apertura del salone nel periodo, in percentuale | Barre |
| Fasce di punta | Prenotazioni confermate per giorno della settimana e ora di inizio | Barre per ora |
| Ricavi | Movimenti completati meno rimborsi, per mese, separando servizi e prodotti; conta la data del pagamento | Barre affiancate |
| Prodotti più venduti | Pezzi venduti per prodotto, negli ordini confermati o ritirati | Barre orizzontali |
| Funnel | Visitatori unici → aperture della pagina di prenotazione → prenotazioni create → prenotazioni pagate | Barre decrescenti |

**Dipendente**

| Statistica | Calcolo | Grafico |
|---|---|---|
| Clienti per giorno, settimana e mese | Le proprie prenotazioni confermate nel periodo | Linea dell'andamento |

L'occupazione è calcolata sull'orario del salone e non considera le assenze: un dipendente in ferie per parte del periodo risulta meno occupato. Ho scelto questa semplificazione per non ricalcolare le disponibilità di ogni dipendente.
 
### Raccolta dei dati

- **Visite alle pagine**: registrate dal server quando risponde a una delle pagine tracciate (home, servizi, prodotti, pagina di prenotazione). Non servono JavaScript né richieste in più. File statici, chiamate fetch, webhook e aree riservate non vengono registrati.
- **Click**: i pulsanti da tracciare hanno un attributo `data-traccia` con il loro nome; al click JavaScript invia con fetch una richiesta POST a una rotta pubblica, con il token CSRF. Il server accetta solo nomi di un elenco fisso e la rotta ha un limite di richieste (Flask-Limiter), così la tabella non si riempie di dati inventati.
- **Visitatori unici**: alla prima visita il server salva nella sessione un identificativo casuale, scritto in ogni evento; i visitatori unici sono gli identificativi diversi nel periodo.
- **Funnel**: visitatori unici e aperture della pagina di prenotazione vengono da `eventi`; prenotazioni create e pagate si contano direttamente da `prenotazioni`, senza duplicarle negli eventi. Il funnel confronta i totali del periodo, non il percorso del singolo visitatore: ho accettato questa approssimazione per semplicità.
- **Lettura con pandas**: `StatisticheService` carica i dati del periodo in DataFrame con query parametrizzate e calcola raggruppamenti e totali.

### Grafici

- **Stile scuro coerente con il sito**: un'unica funzione imposta per tutti i grafici lo sfondo scuro, il testo chiaro e i colori di accento (verde menta `#2dd4bf`, rosa `#ff6b8b`).
- **Generati in memoria**: matplotlib disegna il grafico in un buffer PNG, che una rotta protetta restituisce come immagine. Si usa il backend `Agg`, che non apre finestre ed è adatto a un server.
- **Nessuna cache condivisa**: le risposte con i grafici indicano al browser di non conservarle (`Cache-Control: no-store`), perché contengono dati riservati del salone.

### Privacy delle statistiche

- La tabella `eventi` non contiene IP, identità dell'utente né parametri degli URL.
- Gli eventi più vecchi di 12 mesi vengono cancellati con un comando da terminale. Ho scelto 12 mesi perché bastano per le statistiche, senza conservare dati più a lungo del necessario.
- L'identificativo dei visitatori sta nel cookie di sessione del sito. Prima della fase 8 verificherò sulle indicazioni del Garante se per questo uso serve un banner o un'informativa.

## 9. Scelte tecniche e alternative scartate
Il criterio che ho seguito è la soluzione più semplice che rispetta i requisiti. Il DEVLOG riporta ogni decisione con data e motivazione completa; qui sono riassunte le principali.

| Area | Scelta | Alternativa scartata | Motivo |
|---|---|---|---|
| Framework | Flask | — | Richiesto dalla consegna del corso |
| Database | MySQL con query SQL scritte a mano | ORM (SQLAlchemy) | MySQL richiesto dalla consegna; query scritte a mano perché visibili e parametrizzate, senza strati nascosti |
| Architettura | Modelli, repository, servizi, provider | Logica e SQL nelle rotte | Responsabilità separate, logica testabile senza Flask |
| Avvio dell'app | Application factory (`create_app()`) | App globale in un file | Configurazione separata per i test |
| Controllo accessi | Blueprint con `before_request` | Decoratore su ogni rotta | Nessuna rotta può restare senza controllo |
| Login | Sessione di Flask gestita a mano | Flask-Login | Pochi passaggi, nessuna libreria in più |
| Date | DATETIME in UTC, turni in ora locale | Tutto in ora locale | Nessuna ambiguità con l'ora legale |
| Prezzi | Interi in centesimi | FLOAT o DECIMAL | Nessun arrotondamento, formato richiesto da Stripe |
| Doppie prenotazioni | Controllo nella transazione con `SELECT ... FOR UPDATE` su cliente e dipendente, isolamento `READ COMMITTED` | Controllo solo prima dell'inserimento | Richieste simultanee servite una alla volta, e ognuna vede le prenotazioni appena confermate dalle altre |
| Pagamenti | Conferma dal webhook firmato, movimenti in `pagamenti` | Conferma dalla pagina di ritorno | Il browser non decide l'esito |
| Provider | Classe astratta con implementazione reale e finta | Chiamate dirette a Stripe | Test senza servizi esterni, provider sostituibile |
| Errori | Eccezioni personalizzate e `@app.errorhandler` | Codici di errore restituiti | Regola violata riconoscibile, gestione in un punto |
| Carrello | Sessione di Flask | Tabella `carrelli` | Nessun dato da ripulire |
| Statistiche | pandas e matplotlib, grafici in memoria | File su disco | Nessun dato riservato in cartelle pubbliche |

### Librerie

Le versioni sono bloccate in `requirements.txt`.

| Libreria | Uso |
|---|---|
| Flask (con Werkzeug e Jinja) | Applicazione web, rotte, template, hash delle password |
| mysql-connector-python | Connessione a MySQL e query parametrizzate |
| python-dotenv | Lettura dei segreti dal file `.env` |
| Flask-WTF | Protezione CSRF (`CSRFProtect`) |
| Flask-Limiter | Limite di richieste su login, registrazione e tracciamento dei click |
| stripe | Sessioni di Checkout, verifica dei webhook, rimborsi |
| pandas | Calcolo delle statistiche |
| matplotlib | Grafici delle statistiche |
| Pillow | Controllo e salvataggio delle foto dei prodotti |
| pytest | Test automatici |

Dalla libreria standard di Python uso inoltre `dataclasses` (modelli), `abc` (classe astratta dei provider), `zoneinfo` (fusi orari), `secrets` (valori casuali per chiavi e identificativi) e `calendar` (ultimo giorno del mese).
 
## 10. Sviluppi futuri
- Interfaccia in più lingue (oggi solo italiano) e valute diverse dall'euro, per saloni in altri Paesi.
- Conferma dell'indirizzo email con un messaggio di verifica.
- Hash delle password con argon2, al posto di Werkzeug.
- Giacenza numerica dei prodotti (pezzi in magazzino) al posto della disponibilità sì/no.
- Termine per il ritiro degli ordini, con annullamento e rimborso automatici alla scadenza.
- Recupero della password dimenticata tramite email.

## 11. Versione consegnata (14 ottobre 2026)

Per la consegna del corso ho realizzato una versione ridotta del progetto. Le sezioni 1-10 restano il progetto completo; questa sezione dice cosa è implementato oggi. Le date e le motivazioni delle modifiche sono nel DEVLOG.

### Implementato

- Registrazione dei clienti, login e logout; primo proprietario creato con `flask crea-proprietario`.
- Blueprint `pubblico`, `auth`, `cliente`, `dipendente`, `proprietario` con il controllo degli accessi in `before_request` e il test che scorre tutte le rotte.
- CRUD dei servizi per il proprietario (creazione, modifica, disattivazione e riattivazione) e listino pubblico.
- Calcolo degli slot liberi sul calendario settimanale e sulle eccezioni per data, con assenze e chiusure lette da `indisponibilita`.
- Prenotazione con controllo anti-sovrapposizione per professionista e per cliente, nella stessa transazione.
- Pagamento simulato con `FakeProvider`: acconto o importo completo, scadenza di 30 minuti, conferma idempotente, rimborso automatico dei pagamenti tardivi, uscita dal pagamento.
- Area cliente con storico, importo pagato, totale speso e annullamento fino a 2 ore prima con rimborso; protezione dai dati altrui (404).
- Agenda del professionista con lo storico (svolte e annullate); annullamento con rimborso da parte del salone: il proprietario per tutti, il dipendente per la propria agenda.
- Pagina Dipendenti del proprietario con recapiti, lavoro nel periodo, agenda di ciascuno e totale del salone.
- Orari delle singole date (chiusure, orari ridotti, aperture) decisi dal proprietario; festività e vigilie italiane segnate "da definire" e prenotabili con un avviso finché non decide.
- Home con carosello (video e foto), stato di apertura, orari e contatti; `seed.py` con dati di prova e uno storico di 4 mesi.
- Statistiche (fase 8, in parte): per il proprietario prenotazioni per professionista, andamento, fasce di punta, incasso netto e valore medio; per il professionista l'andamento dei propri appuntamenti. Periodo di 7, 30 o 365 giorni; grafici matplotlib generati in memoria e serviti da rotte protette con `Cache-Control: no-store`.

### Rimandato agli sviluppi futuri

- `StripeProvider` (Checkout, Google Pay, PayPal) e Blueprint `webhook` (fase 7 e 7b).
- Prodotti, carrello e ordini (fase 7c).
- Tracciamento di visite e click (tabella `eventi`), funnel e occupazione (resto della fase 8).
- Pagine del proprietario per il calendario settimanale, assenze, chiusure lunghe, creazione dei dipendenti e saldo in sede: oggi si modificano solo dal database.
- Blueprint `account` con il cambio password; rate limiting del login con Flask-Limiter.

### Scelte cambiate o aggiunte durante lo sviluppo

- **Isolamento `READ COMMITTED`** per tutte le connessioni: con il `REPEATABLE READ` predefinito il controllo dopo il `FOR UPDATE` non vedeva le prenotazioni appena confermate (verificato con un test di concorrenza).
- **Blocco anche sulla riga del cliente**, prima di quella del dipendente: un cliente non può avere due appuntamenti sovrapposti con professionisti diversi.
- **Moduli con `novalidate`**: gli errori li mostra sempre il server, con i messaggi in italiano.
- **Prezzo dei servizi maggiore di zero**: lo schema accetta 0, ma un pagamento di 0 euro sarebbe rifiutato da `pagamenti`.
- **Tema grafico chiaro e caldo** (osso, espresso, corallo, ottone) al posto del tema scuro con verde menta e rosa: più adatto a un salone. Contrasti dei testi verificati (almeno 4,5:1).
- **Il dipendente può annullare le prenotazioni della propria agenda**, con rimborso: le sezioni 2 e 3 lo escludevano. Il salone annulla fino all'inizio dell'appuntamento, senza il limite delle 2 ore del cliente.
- **Festività "da definire"**: date calcolate dal programma, non salvate; diventano normali eccezioni per data quando il proprietario decide.
