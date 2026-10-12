# DEVLOG – Barber Booking

Diario delle scelte di sviluppo: cosa ho fatto, perché e quali alternative ho scartato.

## 2026-10-08 · Fase 1 – Setup

- **Ambiente virtuale `venv`**: isola le librerie del progetto e rende riproducibile l'installazione. Alternative scartate: `pipenv` e `poetry` (più strumenti da spiegare, `venv` è incluso in Python).
- **Database MySQL con `mysql-connector-python`**: richiesto dalla consegna del corso e driver visto a lezione. Alternativa scartata: SQLite (più semplice, ma fuori dalla consegna).
- **`.gitignore` creato prima del primo commit**: il repository diventerà pubblico e la cronologia di Git conserva tutto; così segreti (`.env`) e venv non entrano mai nella storia.
- **Email dei commit `noreply` di GitHub**: evita di esporre l'email personale nel repository pubblico.
- **Repository privata durante lo sviluppo**, pubblica a progetto finito.
- **Flask + mysql-connector-python, versioni bloccate in `requirements.txt`**: framework leggero e driver visto nel corso; versioni fissate per riprodurre l'ambiente. Alternative scartate: Django (troppo integrato, nasconde ciò che voglio mostrare), ORM come SQLAlchemy (fuori dal perimetro del corso).
- **Progettazione scritta prima del codice (`docs/PROGETTAZIONE.md`)**: i requisiti per ruolo diventano la base di rotte, permessi e test degli accessi, e il documento serve per la presentazione. Alternativa scartata: partire subito dal codice e ricostruire la documentazione a posteriori.

## 2026-10-08 · Progettazione – Modello dei dati (sezione 4)

- **DATETIME in UTC, TIME e DATE dei turni in ora locale del salone**: gli istanti (prenotazioni, pagamenti, eventi) in UTC si confrontano senza ambiguità anche al cambio dell'ora legale; i turni sono regole di calendario ("si apre alle 9") e in UTC slitterebbero di un'ora a ogni cambio. La conversione usa `zoneinfo` con il fuso salvato in `impostazioni`. Alternative scartate: tutto in ora locale (l'ora che si ripete a fine ottobre è ambigua), tutto in UTC (turni che cambiano con l'ora legale).
- **Griglia di 30 minuti e durate dei servizi multiple di 30**: ogni combinazione di servizi riempie slot interi, quindi l'agenda non ha buchi non prenotabili e il calcolo degli slot resta semplice. Alternativa scartata: griglia di 15 minuti con durate libere (più slot da calcolare e buchi residui).
- **Tutti i dipendenti eseguono tutti i servizi**: non serve una tabella che colleghi dipendenti e servizi. Alternativa scartata: competenze per dipendente (più complessità senza un requisito che la chieda; possibile sviluppo futuro).
- **Calendario settimanale unico con eccezioni per data**: poche righe coprono la settimana normale, le eccezioni coprono festività e aperture straordinarie. Alternative scartate: un calendario per dipendente (le assenze bastano a gestire le differenze), una riga per ogni data (andrebbe generata di continuo).
- **Finestra di prenotazione da oggi alla fine del mese corrente**: l'ho scelta per semplicità; il periodo si ricava dalla data di oggi nel fuso del salone, senza date di partenza da configurare, ed è immediato da capire per clienti e proprietario. Limite accettato: a fine mese la finestra si accorcia. Alternative scartate: blocchi fissi di 15 giorni da una data di apertura (prima scelta, abbandonata perché richiedeva l'impostazione `data_apertura` senza vantaggi reali), finestra mobile "oggi + N giorni" (apre un giorno nuovo ogni mezzanotte).
- **Prezzi in centesimi interi (`prezzo_centesimi`)**: gli interi non hanno errori di arrotondamento, a differenza dei numeri decimali in virgola mobile, e sono l'unità che chiede Stripe, quindi non serve nessuna conversione. Alternative scartate: FLOAT (arrotondamenti sbagliati), DECIMAL (corretto, ma andrebbe convertito per Stripe).
- **`fine` salvata in `prenotazioni`**: il controllo anti-sovrapposizione diventa una sola condizione (`inizio < fine_altra AND fine > inizio_altra`) senza ricalcolare le durate dai servizi. Alternativa scartata: calcolare la fine ogni volta dalla somma delle durate (query più complessa e più lenta).
- **Stato della prenotazione separato dallo stato del pagamento**: la prenotazione ha il suo ciclo di vita (in attesa, confermata, scaduta, annullata), mentre lo stato del pagamento si ricava dai movimenti. Alternativa scartata: un unico campo che mescola i due (combinazioni come "confermata con acconto" moltiplicherebbero gli stati).
- **Fotografia di prezzo e durata in `prenotazioni_servizi`**: se il proprietario cambia un prezzo, le prenotazioni passate e lo storico dei pagamenti restano corretti. Alternativa scartata: leggere sempre i valori attuali da `servizi` (lo storico cambierebbe a ogni modifica dei prezzi).
- **Assenze e chiusure in un'unica tabella `indisponibilita`**: una chiusura è un'assenza con `dipendente_id` vuoto, così il calcolo degli slot legge una sola tabella. Alternativa scartata: due tabelle separate (due query e due logiche quasi identiche).
- **Pagamenti come movimenti (una riga per pagamento online, saldo in sede o rimborso)**: ogni passaggio di denaro resta registrato con il suo importo e il suo stato, quindi la storia dei pagamenti è completa e verificabile. Alternativa scartata: colonne di pagamento dentro `prenotazioni` (un acconto seguito da saldo e rimborso non ci starebbe senza sovrascrivere dati).
- **`acconto_pagato` e `saldato` calcolati, non salvati**: si ricavano confrontando la somma dei movimenti completati con il totale della prenotazione, così non possono mai contraddire i movimenti. Alternativa scartata: una colonna di stato da aggiornare a ogni movimento (rischio di dati incoerenti se un aggiornamento si dimentica).
- **Idempotenza del webhook tramite `riferimento_provider` univoco**: il provider può inviare la stessa notifica più volte; il vincolo di unicità fa ritrovare la riga esistente invece di registrare due volte lo stesso pagamento. Alternativa scartata: una tabella a parte con gli eventi webhook già elaborati (una tabella in più per lo stesso risultato).
- **Rimborso sempre pari a quanto pagato**: una regola sola, senza penali né percentuali da calcolare; gli annullamenti tardivi del cliente sono già impediti dal limite delle 2 ore. Alternativa scartata: penali sugli annullamenti (più regole e più casi da testare).
- **`impostazioni` come tabella a riga singola (`id` sempre 1)**: ogni impostazione ha il suo tipo e i suoi vincoli nel database (es. percentuale tra 1 e 99). Alternativa scartata: tabella chiave-valore (più flessibile, ma tutti i valori diventano testo e i controlli passano al codice).
- **`eventi` senza IP né identità dell'utente**: per le statistiche basta un identificativo di sessione anonimo e casuale, che permette di contare visitatori unici e ricostruire il funnel raccogliendo il minimo di dati personali. Alternativa scartata: salvare IP o `utente_id` (dati personali non necessari allo scopo).

## 2026-10-08 · Progettazione – Modello a oggetti (sezione 5)

- **Classi divise in modelli, repository, servizi e provider di pagamento**: ogni gruppo ha un solo compito, l'SQL sta in un solo posto e la logica di business si testa senza Flask. Alternative scartate: SQL e regole scritti nelle rotte (logica sparsa, difficile da testare), ORM come SQLAlchemy (fuori dal perimetro del corso).
- **Modelli con `@dataclass`**: genera da solo `__init__` e `__repr__` per classi che contengono soprattutto dati. Alternativa scartata: classi normali (più codice ripetitivo per lo stesso risultato).
- **`PaymentProvider` come classe astratta (`abc`) con implementazione reale e finta**: i servizi dipendono solo dall'interfaccia, quindi i pagamenti si testano senza Stripe e si può aggiungere PayPal senza modificarli. Alternativa scartata: chiamare Stripe direttamente dai servizi (test legati al servizio esterno).
- **Eccezioni personalizzate con classe base `BarberBookingError` e gestore centrale `@app.errorhandler`**: il nome dell'eccezione dice quale regola è violata e la gestione degli errori sta in un punto solo. Alternative scartate: eccezioni generiche come `ValueError` (poco precise), valori di ritorno con codici di errore (si possono ignorare per sbaglio).
- **Una sola classe `Utente` con il campo `ruolo`**: i ruoli hanno gli stessi dati e il proprietario può anche ricevere prenotazioni; i permessi li decide il controllo degli accessi. Alternativa scartata: sottoclassi per ruolo (ereditarietà senza comportamenti diversi). Nessun modello per `eventi`, che si legge direttamente con pandas.

## 2026-10-09 · Progettazione – Finestra di prenotazione e vendita dei prodotti

- **Finestra di prenotazione configurabile da 0 a 3 mesi oltre quello corrente (`mesi_prenotabili`)**: sostituisce la regola fissa del solo mese corrente; i clienti possono prenotare con più anticipo e il proprietario sceglie quanto. Il massimo a 3 tiene gli acconti ben dentro i tempi di rimborso del provider. Alternativa scartata: valore fisso nel codice (il proprietario non potrebbe adattarlo).
- **Pagamento online obbligatorio confermato, senza opzione "tutto in sede"**: l'acconto, con percentuale anche bassa, copre già il bisogno di pagare in negozio e protegge il salone da chi prenota e non si presenta. Alternative scartate: pagamento interamente in sede (nessuna protezione), pagamento online consentito solo dalle 2 settimane prima dell'appuntamento (un flusso "paga dopo" in più da gestire e testare).
- **Vendita di prodotti con pagamento online e ritiro in negozio**: tabelle `prodotti`, `ordini` e `ordini_prodotti`, con prezzo e quantità fissati al momento dell'acquisto come per i servizi. Alternative scartate: solo vetrina (nessun acquisto online), negozio con spedizione (indirizzi, spedizioni e resi: quasi un secondo progetto).
- **Disponibilità dei prodotti sì/no invece della giacenza in pezzi**: evita un secondo controllo di concorrenza simile a quello degli slot; se un pezzo viene venduto due volte, il proprietario annulla e rimborsa. Limite di 10 pezzi per prodotto in un ordine. Alternativa scartata: giacenza numerica (rimandata agli sviluppi futuri).
- **Ordini gestiti solo dal proprietario**: registra il ritiro e annulla con rimborso; il cliente non annulla. Coerente con il resto dei permessi, il dipendente vede solo la propria agenda.
- **Una sola tabella `pagamenti` per prenotazioni e ordini, con `prenotazione_id` e `ordine_id` facoltative e un CHECK che obbliga a compilarne esattamente una**: webhook, idempotenza e rimborsi restano un'unica logica. Alternativa scartata: una seconda tabella dei pagamenti quasi identica (logica duplicata).
- **Foto dei prodotti salvate su disco, solo il nome del file nel database, controllate e risalvate con Pillow**: si accettano solo JPEG, PNG e WebP con dimensione massima, il nome lo genera il server, e il nuovo salvataggio elimina contenuti nascosti e metadati (es. posizione GPS). Alternative scartate: immagine nel database come BLOB (database e backup appesantiti), link a immagini esterne (catalogo dipendente da altri siti e IP dei visitatori inviati a terzi).
- **Carrello nella sessione di Flask, trasformato in `Ordine` solo al pagamento**: nessuna tabella in più e nessun carrello abbandonato da ripulire. Limite accettato: il carrello non passa da un dispositivo all'altro. Alternativa scartata: tabella `carrelli` nel database.

## 2026-10-09 · Progettazione – Struttura del progetto Flask (sezione 6)

- **Cartelle dentro `app/` divise come i gruppi di classi (modelli, repository, servizi, pagamenti, rotte)**: l'architettura si capisce aprendo il repository. Alternativa scartata: pochi file grandi (es. `models.py`, `routes.py`), più semplici all'inizio ma difficili da seguire con un progetto di queste dimensioni.
- **Application factory (`create_app()`)**: l'app viene creata da una funzione che riceve la configurazione, così i test usano un database di prova e il `FakeProvider` senza toccare la configurazione reale. Alternativa scartata: `app = Flask(__name__)` globale in un solo file (difficile da configurare nei test).
- **Blueprint per area con controllo in `before_request`**: il controllo degli accessi è scritto una volta per area e copre ogni rotta, anche quelle aggiunte in seguito (nega per default). Alternativa scartata: un decoratore su ogni rotta (basta dimenticarlo una volta per lasciare una rotta aperta).
- **Blueprint `webhook` senza login né CSRF, protetto dalla verifica della firma**: le notifiche arrivano dal provider, non da un modulo del sito; è l'unica eccezione e resta isolata in un Blueprint dedicato.

## 2026-10-09 · Progettazione – Sicurezza: autenticazione e sessione (sezione 7)

- **Login gestito a mano con la sessione di Flask**: dopo il login la sessione viene svuotata e riceve solo l'`id` dell'utente, che viene ricaricato dal database a ogni richiesta. Pochi passaggi, tutti spiegabili. Alternativa scartata: Flask-Login (una libreria in più per funzioni che con Blueprint e `before_request` mi servono solo in parte).
- **Rate limiting con Flask-Limiter**: 5 tentativi di login al minuto per IP, più un limite sulla registrazione. L'IP serve solo a contare i tentativi e non viene salvato nel database. Alternativa scartata: contatore dei tentativi scritto a mano (una tabella e più codice per lo stesso risultato).
- **Registrazione pubblica solo per i clienti**: i dipendenti li crea il proprietario, il primo proprietario si crea da terminale. Nessuno può assegnarsi un ruolo da solo.
- **Pagina di cambio password, nel nuovo Blueprint `account`**: richiede la password attuale; il Blueprint dedicato mantiene la regola "nega per default" anche per una rotta aperta a tutti i ruoli. Il cambio al primo accesso dei dipendenti è consigliato, non obbligato. Alternative scartate: rotta dentro `auth` con un controllo a parte (unica eccezione alla regola), colonna `deve_cambiare_password` per obbligare il cambio (più sicura, ma un dato e un controllo in più). Recupero via email rimandato agli sviluppi futuri.

## 2026-10-09 · Progettazione – Sicurezza: accessi, richieste, segreti e pagamenti (sezione 7)

- **Controllo della proprietà dei dati dentro le query (`AND cliente_id = %s`), con 404 per i dati altrui**: impedisce l'accesso ai dati di altri cambiando un id nell'URL (IDOR) e non rivela se il dato esiste. L'identità si prende sempre dalla sessione. Alternative scartate: 403 (conferma che il dato esiste), controllo separato dopo la lettura (più codice, facile da dimenticare).
- **Grafici generati in memoria e serviti da rotte protette**: nessun file con dati riservati in `static/`. Alternativa scartata: file salvati su disco (da proteggere e da ripulire).
- **CSRF con `CSRFProtect` di Flask-WTF, usato solo per il token**: protezione standard di tutti i POST, compresi quelli via fetch; i moduli restano HTML normali. Alternativa scartata: token scritto a mano (facile sbagliare un dettaglio di sicurezza).
- **XSS: escape automatico di Jinja, mai `|safe` sui dati degli utenti, `textContent` in JavaScript**: i dati degli utenti sono sempre mostrati come testo, mai interpretati come HTML.
- **Validazione di tutti i dati sul server**: i controlli del browser si aggirano, quelli del server no.
- **Segreti in `.env` con `python-dotenv` e `.env.example` nel repository**: il repository pubblico non contiene segreti e mostra quali variabili configurare. Utente MySQL dedicato, debug spento in produzione, solo chiavi di test di Stripe.
- **Pagamenti: importi calcolati dal server, conferma solo dal webhook con firma verificata, importo ricontrollato alla conferma**: il browser non decide né prezzi né esito del pagamento. I dati della carta restano su Stripe Checkout. Alternativa scartata: confermare dalla pagina di ritorno (si può aprire senza aver pagato).

## 2026-10-09 · Progettazione – Statistiche (sezione 8)

- **Statistiche con definizioni precise, solo prenotazioni confermate**: ogni numero ha un calcolo dichiarato, così si può spiegare e verificare. Aggiunti i prodotti più venduti.
- **Ricavi per data del pagamento**: è il momento in cui i soldi entrano e basta la tabella `pagamenti`. Alternativa scartata: data dell'appuntamento (un acconto di settembre per un taglio di dicembre comparirebbe solo a dicembre).
- **Occupazione rispetto all'orario del salone, senza considerare le assenze**: calcolo semplice dal calendario e dalle eccezioni. Limite accettato: chi è stato assente risulta meno occupato. Alternativa scartata: ore di apertura individuali tolte le assenze (più precisa, ma ricalcola le disponibilità di ogni dipendente).
- **Visite registrate dal server, click inviati con fetch a una rotta con elenco fisso di nomi e limite di richieste**: dati affidabili senza dipendere da JavaScript per le visite e senza eventi inventati. Alternativa scartata: tracciare tutto da JavaScript (le visite si perdono se JavaScript è disattivato).
- **Funnel con i primi passaggi da `eventi` e gli ultimi da `prenotazioni`**: le prenotazioni non sono registrate due volte; `eventi` contiene solo `visita_pagina` e `click`. Limite accettato: si confrontano i totali del periodo, non il percorso di ogni visitatore. Alternativa scartata: eventi di prenotazione legati alla sessione (dati duplicati che possono non coincidere).
- **Grafici matplotlib in stile scuro, generati in memoria con il backend `Agg` e serviti senza cache**: nessun file riservato su disco e nessun errore legato alle finestre grafiche sul server.
- **Eventi cancellati dopo 12 mesi con un comando da terminale**: si conservano solo i dati utili alle statistiche. Alternativa scartata: cancellazione automatica pianificata (un componente in più).

## 2026-10-09 · Progettazione – Riepilogo delle scelte (sezione 9) e chiusura della progettazione

- **Sezione 9 come riepilogo**: tabella delle scelte principali e delle librerie, con rimando al DEVLOG per date e motivazioni complete. Evita di duplicare ogni decisione in due documenti.
- **Precisazione sulla Fase 1**: Flask e MySQL sono richiesti dalla consegna del corso; Django, indicato tra le alternative scartate, non l'ho valutato come alternativa reale.
- **Progettazione completa (sezioni 1-10)**: requisiti, regole, modello dei dati, classi, struttura, sicurezza e statistiche sono definiti prima del codice. Le verifiche tecniche ancora aperte (versione di MySQL, Stripe, tzdata, indicazioni del Garante) le farò all'inizio delle fasi che le riguardano.

## 2026-10-09 · Fase 2 – Modello a oggetti

- **Modelli in `app/modelli/`, un file per gruppo** (es. `prenotazione.py` con `Prenotazione` e `ServizioPrenotato`): le classi collegate stanno insieme. Alternative scartate: un file per classe (troppi file minuscoli), un unico `modelli.py` (contrario alla struttura della sezione 6).
- **Primo test con pytest già in Fase 2, sui metodi di `Prenotazione`** (`durata_totale`, `prezzo_totale`): i modelli non dipendono da database né da Flask, quindi si testano subito. Test nella cartella `tests/` fuori da `app/`, eseguiti con `python -m pytest`. Alternativa scartata: rimandare tutti i test alla fase finale (gli errori si scoprirebbero tardi).
- **Modelli senza validazione**: contengono solo dati e pochi metodi di calcolo (`durata_totale`, `prezzo_totale`); le regole (durate multiple di 30, date nel futuro, `fine` dopo `inizio`) stanno nei servizi e nei CHECK del database. Alternativa scartata: controlli in `__post_init__` (regole sparse in due posti).
- **`id` facoltativo e in fondo ai campi**: un oggetto nuovo non ha ancora l'`id`, che assegna MySQL all'INSERT; una dataclass richiede i campi con valore predefinito dopo quelli obbligatori.
- **Solo la classe base `BarberBookingError` per ora**: le eccezioni specifiche si aggiungono nelle fasi in cui un servizio le solleva. Alternativa scartata: scriverle tutte subito (classi non ancora usate).


## 2026-10-09 · Fase 3 – Verifiche su MySQL

- **MySQL 8.0.41**: i vincoli `CHECK` vengono applicati (servono la 8.0.16 o successive).
- **`creato_il` con predefinito `(UTC_TIMESTAMP())` invece di `CURRENT_TIMESTAMP`**: la connessione usa il fuso orario di sistema (`SYSTEM`, ora italiana), quindi `CURRENT_TIMESTAMP` salverebbe l'ora locale. Il predefinito in UTC è scritto nello schema e vale per ogni connessione. Nelle query l'ora attuale la passa Python in UTC, senza usare `NOW()`. Alternative scartate: fuso orario della connessione impostato a UTC in `db.py` (non vale per Workbench), fuso orario globale del server (modifica anche gli altri database).

## 2026-10-12 · Fase 3 – Verifiche su MySQL
- **`schema.sql` ricrea il database da zero (`DROP DATABASE IF EXISTS`)**: si esegue sempre per intero, senza preoccuparsi dell'ordine delle chiavi esterne; i dati di prova li ricrea `seed.py`. Alternative scartate: `DROP TABLE IF EXISTS` per ogni tabella (ordine inverso delle chiavi esterne da mantenere), strumenti di migrazione come Alembic (utili con dati reali da conservare, una libreria in più).