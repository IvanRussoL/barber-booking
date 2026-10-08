# Progettazione – Barber Booking
 
## 1. Problema e utenti
 
Un salone di barbiere/parrucchiere gestisce gli appuntamenti per telefono o di persona: è facile sbagliare gli orari, sovrapporre due clienti dallo stesso dipendente o dimenticare chi ha già versato un acconto. L'applicazione permette ai clienti di prenotare online scegliendo servizio, dipendente e orario, e al salone di gestire agende, pagamenti e statistiche in un unico posto.
 
Gli utenti sono quattro:
 
- **Visitatore (non registrato)**: può consultare il sito, ma non prenotare.
- **Cliente**: persona registrata che prenota e paga online.
- **Dipendente**: parrucchiere o barbiere del salone, con un'agenda propria.
- **Proprietario**: gestisce il salone; può essere anche parrucchiere e ricevere prenotazioni.
## 2. Requisiti funzionali
 
### Visitatore
- Consulta servizi, prezzi, orari del salone e posizione sulla mappa.
- Si registra o accede.
### Cliente
- Prenota scegliendo uno o più servizi (es. taglio + barba), il dipendente e uno slot libero.
- Sceglie al momento della prenotazione se pagare un acconto o l'importo completo, online.
- Consulta nella propria area personale lo **storico delle prenotazioni** con il dettaglio dei servizi e lo **storico dei pagamenti**, con il totale speso.
- Annulla solo le proprie prenotazioni, fino a 2 ore prima, con rimborso.
### Dipendente
- Accede con un profilo personale e vede **solo la propria agenda**.
- Nella propria pagina consulta le **statistiche del proprio lavoro**: clienti giornalieri, settimanali e mensili, con grafici sull'andamento (se le prenotazioni aumentano o diminuiscono).
- Non può prenotare presso altri dipendenti o presso il proprietario.
- Non può annullare prenotazioni né registrare assenze.
### Proprietario
- Gestisce servizi (con durate e prezzi), dipendenti e orari di lavoro.
- Consulta le statistiche generali: prenotazioni per dipendente, occupazione, fasce di punta, ricavi, funnel visite → prenotazioni.
- Registra il saldo pagato in sede.
- Modifica i dati del salone, compresa la posizione sulla mappa (riservato al proprietario).
- Se lavora anche come parrucchiere, riceve prenotazioni come un dipendente; non può prenotare presso i dipendenti.
- Registra assenze dei dipendenti e chiusure del salone; annulla prenotazioni con rimborso.
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
- **Finestra di prenotazione**: il cliente può prenotare da oggi fino all'**ultimo giorno del mese corrente**. Il primo giorno di ogni mese si apre il mese nuovo.
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
### Annullamenti, assenze e chiusure
- Il cliente annulla **solo le proprie** prenotazioni, fino a **2 ore prima** dell'inizio dell'appuntamento.
- **Solo il proprietario** annulla prenotazioni per conto del salone e registra le assenze dei dipendenti e le chiusure del salone. I dipendenti non possono farlo.
- In ogni annullamento il cliente è rimborsato di **esattamente quanto ha pagato** (solo l'acconto, o l'importo completo).
- Se un'assenza o una chiusura copre prenotazioni già confermate, il sistema mostra al proprietario l'elenco delle prenotazioni coinvolte e le annulla, con rimborso, **solo dopo la sua conferma esplicita**.
### Accessi
- Il cliente vede e annulla **solo le proprie** prenotazioni.
- Il dipendente vede **solo la propria** agenda e le proprie statistiche.
- Il primo proprietario si crea da riga di comando, non da una pagina pubblica.
## 4. Modello dei dati (tabelle e relazioni)

Convenzione: tutte le colonne DATETIME sono salvate in **UTC**. Il server le converte nel fuso orario del salone solo per mostrarle e per i calcoli su turni, griglia e finestra di prenotazione.

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

### Tabella `orari_settimanali`

Contiene il calendario settimanale del salone, unico per tutti i dipendenti: una riga per ogni turno. Un giorno senza righe è chiuso.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del turno |
| `giorno_settimana` | TINYINT, obbligatoria, da 1 (lunedì) a 7 (domenica) | Giorno della settimana, con la stessa numerazione di `isoweekday()` di Python |
| `ora_inizio` | TIME, obbligatoria | Inizio del turno, nell'ora locale del salone (non in UTC) |
| `ora_fine` | TIME, obbligatoria, successiva a `ora_inizio` | Fine del turno, nell'ora locale del salone |

Il codice verifica che i turni dello stesso giorno non si sovrappongano e che inizio e fine cadano sulla griglia di 30 minuti.

Chiave primaria composta (`prenotazione_id`, `servizio_id`): lo stesso servizio non può comparire due volte nella stessa prenotazione.

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

Contiene i movimenti di denaro legati alle prenotazioni: pagamenti online, saldi in sede e rimborsi, una riga per movimento. Gli stati `acconto_pagato` e `saldato` non si salvano: si calcolano confrontando la somma dei movimenti completati con il totale della prenotazione.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | INT, chiave primaria, auto-incrementale | Identificativo numerico univoco del movimento |
| `prenotazione_id` | INT, obbligatoria, chiave esterna verso `prenotazioni.id` | La prenotazione a cui si riferisce il movimento |
| `tipo` | ENUM('online', 'in_sede', 'rimborso'), obbligatoria | Pagamento online tramite il provider, saldo registrato dal proprietario in sede, oppure rimborso |
| `importo_centesimi` | INT, obbligatoria, maggiore di 0 | Importo in centesimi, calcolato sempre dal server; per i rimborsi è l'importo restituito |
| `stato` | ENUM('in_attesa', 'completato', 'fallito'), obbligatoria, predefinito 'in_attesa' | Un pagamento online diventa 'completato' solo tramite il webhook; un saldo in sede nasce già 'completato' |
| `riferimento_provider` | VARCHAR(255), facoltativa, univoca | Identificativo della sessione di pagamento o del rimborso presso il provider (Stripe o PayPal); vuoto per i saldi in sede. Essendo univoco, un webhook ripetuto ritrova la stessa riga invece di crearne una nuova |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento in cui il movimento è stato registrato |

### Tabella `impostazioni`

Contiene i dati e le regole configurabili del salone. Ha una sola riga, modificabile solo dal proprietario.

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

### Tabella `eventi`

Contiene le visite alle pagine e i click, per le statistiche e il funnel visite → prenotazioni. Non salva indirizzi IP né l'identità dell'utente.

| Colonna | Tipo | Significato |
|---|---|---|
| `id` | BIGINT, chiave primaria, auto-incrementale | Identificativo dell'evento; BIGINT perché è la tabella che cresce più in fretta |
| `tipo` | VARCHAR(50), obbligatoria | Tipo di evento (es. 'visita_pagina', 'click', 'prenotazione_creata'); il server accetta solo i tipi di un elenco fisso |
| `pagina` | VARCHAR(255), obbligatoria | Percorso della pagina (es. '/servizi'), senza parametri, per non registrare dati personali |
| `elemento` | VARCHAR(100), facoltativa | Per i click, quale pulsante o link è stato premuto |
| `sessione` | VARCHAR(64), obbligatoria | Identificativo anonimo e casuale del visitatore, salvato nella sessione; serve a contare i visitatori unici e a ricostruire il funnel |
| `creato_il` | DATETIME, obbligatoria, predefinito data e ora attuali | Momento dell'evento |

Indice: (`tipo`, `creato_il`) per le statistiche per periodo.

## 5. Modello a oggetti (classi e ruolo dell'OOP)
 
## 6. Struttura del progetto Flask
 
## 7. Sicurezza e controllo accessi
 
## 8. Statistiche
 
## 9. Scelte tecniche e alternative scartate
 
## 10. Sviluppi futuri
- Interfaccia in più lingue (oggi solo italiano) e valute diverse dall'euro, per saloni in altri Paesi.
- Conferma dell'indirizzo email con un messaggio di verifica.
- Hash delle password con argon2, al posto di Werkzeug.