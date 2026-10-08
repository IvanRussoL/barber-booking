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
## 4. Modello dei dati (tabelle e relazioni)
## 5. Modello a oggetti (classi e ruolo dell'OOP)
## 6. Struttura del progetto Flask
## 7. Sicurezza e controllo accessi
## 8. Statistiche
## 9. Scelte tecniche e alternative scartate
## 10. Sviluppi futuri