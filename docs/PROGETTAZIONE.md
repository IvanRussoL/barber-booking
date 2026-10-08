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
- Annulla solo le proprie prenotazioni.

### Dipendente
- Accede con un profilo personale e vede **solo la propria agenda**.
- Nella propria pagina consulta le **statistiche del proprio lavoro**: clienti giornalieri, settimanali e mensili, con grafici sull'andamento (se le prenotazioni aumentano o diminuiscono).
- Non può prenotare presso altri dipendenti o presso il proprietario.

### Proprietario
- Gestisce servizi (con durate e prezzi), dipendenti e orari di lavoro.
- Consulta le statistiche generali: prenotazioni per dipendente, occupazione, fasce di punta, ricavi, funnel visite → prenotazioni.
- Registra il saldo pagato in sede.
- Modifica i dati del salone, compresa la posizione sulla mappa (riservato al proprietario).
- Se lavora anche come parrucchiere, riceve prenotazioni come un dipendente; non può prenotare presso i dipendenti.

## 3. Regole di business

### Prenotazioni
- Il salone è **chiuso il lunedì**: nessuna prenotazione è possibile in quel giorno. La regola è verificata sul server in fase di calcolo degli slot e di creazione della prenotazione, non solo nell'interfaccia.
- Solo i **clienti registrati** possono prenotare.
- **Dipendenti e proprietario non possono prenotare** presso dipendenti o proprietario.
- Ogni servizio ha una **durata** e un prezzo; la durata di una prenotazione con più servizi è la somma delle durate.
- Gli slot liberi si calcolano **per singolo dipendente**.
- Un dipendente non può avere due prenotazioni sovrapposte: il controllo avviene **nella stessa transazione** che crea la prenotazione, per evitare doppie prenotazioni in caso di richieste simultanee.
#### Orari e disponibilità
- Orario unico per tutti i dipendenti: **09:00–13:00 e 15:00–23:00**, da martedì a domenica (lunedì chiuso).
- Gli appuntamenti iniziano a ore piene (slot da 1 ora).
- Una prenotazione è assegnata a **un solo dipendente**, che esegue tutti i servizi scelti.
- **Assenze del dipendente** (malattia, ferie): il proprietario registra un periodo (giorni o ore) in cui non riceve prenotazioni; la sua card mostra un segno di indisponibilità.
- **Chiusure del salone** (ferie): nel periodo nessuno riceve prenotazioni.

### Pagamenti
- Il pagamento online è obbligatorio, in modalità test.
- Il cliente sceglie se pagare un **acconto** (percentuale configurabile dal proprietario, resto in sede) oppure l'**importo completo**.
- Gli importi sono **calcolati sempre dal server**, mai presi dai dati inviati dal browser.
- Una prenotazione nasce `in_attesa_pagamento` e viene confermata solo dalla notifica del provider di pagamento (webhook con firma verificata, gestito in modo idempotente).
- Stati del pagamento: `acconto_pagato`, `saldato`. Il saldo in sede lo registra il proprietario.
- Una prenotazione `in_attesa_pagamento` blocca lo slot per **10 minuti**; se il pagamento non arriva, decade e lo slot torna libero.
- Il cliente può **annullare fino a 2 ore prima** dell'inizio.
### Accessi
- Il cliente vede e annulla **solo le proprie** prenotazioni.
- Il dipendente vede **solo la propria** agenda e le proprie statistiche.
- Il primo proprietario si crea da riga di comando, non da una pagina pubblica.
## 4. Modello dei dati (tabelle e relazioni)
## 5. Modello a oggetti (classi e ruolo dell'OOP)
## 6. Struttura del progetto Flask
## 7. Sicurezza e controllo accessi
## 8. Statistiche
## 9. Scelte tecniche e alternative scartate
## 10. Sviluppi futuri