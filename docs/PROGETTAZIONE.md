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
- Gli slot liberi si calcolano **per singolo dipendente**.
- Un dipendente non può avere due prenotazioni sovrapposte: il controllo avviene **nella stessa transazione** che crea la prenotazione, per evitare doppie prenotazioni in caso di richieste simultanee.
### Orari e disponibilità
- Il proprietario imposta il **calendario settimanale** del salone: per ogni giorno della settimana indica se è aperto o chiuso e quali turni ha (es. 09:00–13:00 e 15:00–23:00). Il calendario è unico per tutti i dipendenti.
- Valore di partenza: **lunedì chiuso**; gli altri giorni aperti con i turni 09:00–13:00 e 15:00–23:00. Il proprietario può cambiarlo (per esempio chiudere il martedì o la domenica).
- Il proprietario può inserire **eccezioni per una data precisa**: un giorno normalmente chiuso reso apribile (con i suoi turni) oppure un giorno normalmente aperto reso chiuso.
- Nei giorni chiusi e fuori dai turni non è possibile prenotare. La regola è verificata sul server in fase di calcolo degli slot e di creazione della prenotazione, non solo nell'interfaccia.
- Gli appuntamenti possono iniziare ogni **30 minuti**. Un appuntamento deve stare per intero dentro un turno: non può attraversare la pausa tra due turni né finire dopo la chiusura.
- **Finestra di prenotazione**: le prenotazioni si aprono a **blocchi fissi di 15 giorni consecutivi**, a partire dalla data di apertura del sito (impostata dal proprietario). Il cliente può prenotare solo le date del blocco corrente; terminato il blocco, se ne apre uno nuovo. I blocchi non dipendono dai mesi del calendario.
- **Assenze del dipendente** (malattia, ferie): il proprietario registra un periodo (giorni o ore) in cui non riceve prenotazioni; la sua card mostra un segno di indisponibilità.
- **Chiusure del salone** (ferie): periodo di più giorni consecutivi in cui nessuno riceve prenotazioni.
- Le chiusure del salone non fanno eccezione alla finestra: le date successive alla riapertura si prenotano quando il blocco che le contiene si apre.
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
## 5. Modello a oggetti (classi e ruolo dell'OOP)
 
## 6. Struttura del progetto Flask
 
## 7. Sicurezza e controllo accessi
 
## 8. Statistiche
 
## 9. Scelte tecniche e alternative scartate
 
## 10. Sviluppi futuri
- Interfaccia in più lingue (oggi solo italiano) e valute diverse dall'euro, per saloni in altri Paesi.
- Conferma dell'indirizzo email con un messaggio di verifica.
- Hash delle password con argon2, al posto di Werkzeug.