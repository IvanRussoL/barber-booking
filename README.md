# Barber Booking

Applicazione web di prenotazione per saloni di barbiere/parrucchiere: i clienti trovano un salone vicino (con la posizione del browser o per regione e provincia, anche su una mappa), prenotano servizi e professionista pagando un acconto o l'intero importo e, dopo l'appuntamento, lasciano una recensione; i professionisti consultano la propria agenda e ogni proprietario gestisce il proprio salone. Progetto finale del corso Full Stack Python.

> Stato: la versione consegnata per il corso (14 ottobre 2026, un solo salone) è segnata dal tag `consegna-corso`. La versione attuale aggiunge più saloni, ricerca, recensioni, mappa, la gestione completa del salone e i pagamenti con Stripe in modalità test; senza la chiave di Stripe il pagamento è simulato (`FakeProvider`).

## Funzionalità

| Ruolo | Cosa può fare |
|---|---|
| Visitatore | Cerca i saloni vicino a sé (raggio di 5, 10, 25 o 50 km) o per regione e provincia, ordinati per distanza, recensioni o nome, anche su una mappa interattiva; nella pagina di un salone vede se è aperto, orari (con le date particolari), servizi e prezzi, recensioni; si registra come cliente |
| Cliente | Con un solo account prenota in qualsiasi salone uno o più servizi scegliendo professionista, data e orario libero; paga acconto o importo completo con carta, Google Pay o PayPal su Stripe Checkout; consulta lo storico di tutti i saloni con il totale speso; annulla fino a 2 ore prima con rimborso; recensisce un appuntamento svolto (una volta) |
| Dipendente | Consulta la propria agenda con i recapiti dei clienti, quanto hanno già pagato e quanto resta da pagare in sede, e lo storico (anche le annullate); annulla un proprio appuntamento con rimborso al cliente; vede le proprie statistiche |
| Proprietario | Vede e gestisce solo il proprio salone: servizi; nella pagina Dipendenti vede recapiti, lavoro e agenda di ogni professionista e il totale del salone su settimana, mese o anno; annulla qualsiasi prenotazione con rimborso e registra il saldo in sede; crea, disattiva e riattiva i dipendenti; decide l'orario settimanale, gli orari delle singole date (chiusure, festività), le assenze dei professionisti e le chiusure di più giorni; consulta le statistiche; se lavora in sala riceve prenotazioni |

Tutti gli utenti con il login cambiano la propria password dalla pagina Account.

Regole principali: ogni salone ha i suoi servizi, professionisti, orari e acconto, e nessuno dello staff vede i dati di un altro salone; slot di 30 minuti dentro i turni del salone (festività e vigilie restano "da definire" e prenotabili con un avviso finché il proprietario non decide l'orario), nessuna sovrapposizione per lo stesso professionista né per lo stesso cliente (anche con richieste simultanee), prenotazione bloccata per 30 minuti in attesa del pagamento, prezzi e importi calcolati sempre dal server.

## Tecnologie

- Python 3.13, Flask 3, Jinja
- MySQL 8 con `mysql-connector-python` e query SQL scritte a mano (nessun ORM)
- HTML, CSS e JavaScript (`fetch` per gli orari liberi, geolocalizzazione del browser), Playfair Display da Google Fonts per i titoli
- Leaflet con le mappe di OpenStreetMap per la mappa dei saloni; distanze calcolate da MySQL con `ST_Distance_Sphere`
- Flask-WTF (solo protezione CSRF), Flask-Limiter (limite ai tentativi di login), python-dotenv, tzdata
- Stripe Checkout in modalità test, con la libreria ufficiale `stripe`
- pandas e matplotlib per le statistiche (grafici generati in memoria)
- pytest

## Struttura

```
barber-booking/
├── app/
│   ├── __init__.py        # create_app(): configurazione, Blueprint, gestori degli errori
│   ├── modelli/           # dataclass: Salone, Utente, Servizio, Prenotazione, Pagamento, Recensione, ...
│   ├── repository/        # unico posto con SQL, sempre parametrizzato e filtrato per salone
│   ├── servizi/           # regole di business, senza Flask: SaloniService (creazione e ricerca),
│   │                      #   AuthService, SaloneService, DisponibilitaService, PrenotazioneService,
│   │                      #   CalendarioService, AssenzeService, PersonaleService, StatisticheService,
│   │                      #   RecensioniService
│   ├── pagamenti/         # PaymentProvider (classe astratta), StripeProvider e FakeProvider
│   ├── rotte/             # Blueprint: pubblico, auth, account, cliente, dipendente, proprietario, webhook
│   ├── templates/         # pagine Jinja, una cartella per Blueprint
│   ├── static/            # CSS, JavaScript, foto ridotte (img/) e video della home (video/)
│   ├── accessi.py         # controllo comune dei Blueprint riservati
│   ├── comandi.py         # flask crea-salone e flask crea-proprietario
│   ├── limiti.py          # limite ai tentativi sbagliati (Flask-Limiter)
│   ├── eccezioni.py       # BarberBookingError e sottoclassi
│   └── db.py              # connessione a MySQL
├── database/schema.sql    # tabelle, vincoli e province italiane
├── tests/                 # test con pytest
├── docs/PROGETTAZIONE.md  # requisiti, modello dei dati, architettura, sicurezza
├── DEVLOG.md              # diario delle scelte
├── seed.py                # dati di prova
└── run.py                 # avvio in sviluppo
```

## Installazione (Windows, PowerShell)

Servono Python 3.13 e MySQL 8.0.16 o successivo.

1. Ambiente virtuale e librerie:
   ```powershell
   git clone <URL-del-repository>
   cd barber-booking
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Database: in MySQL Workbench, come `root`, eseguire `database/schema.sql`. Per i test, eseguire lo stesso script sostituendo `barber_booking` con `barber_booking_test`.
3. Utente MySQL dell'app, con i soli permessi sui dati:
   ```sql
   CREATE USER 'barber_app'@'localhost' IDENTIFIED BY 'una-password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON barber_booking.* TO 'barber_app'@'localhost';
   GRANT SELECT, INSERT, UPDATE, DELETE ON barber_booking_test.* TO 'barber_app'@'localhost';
   ```
4. Configurazione: copiare `.env.example` in `.env` e inserire la password di `barber_app` e una `SECRET_KEY` generata con:
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. Dati di prova (facoltativo): cinque saloni immaginari con proprietari, dipendenti, clienti, prenotazioni e recensioni:
   ```powershell
   python seed.py
   ```
6. Un salone vero, con il suo proprietario (le domande compaiono nel terminale; le coordinate si copiano da Google Maps con il tasto destro sul punto):
   ```powershell
   flask --app app crea-salone
   ```
   Per aggiungere un altro proprietario a un salone esistente: `flask --app app crea-proprietario`.
7. Avvio: `python run.py`, poi aprire http://127.0.0.1:5000
8. Pagamenti con Stripe (facoltativo; senza, il pagamento è simulato):
   - nel Dashboard di Stripe, in modalità test, copiare la chiave segreta (`sk_test_...`) in `STRIPE_SECRET_KEY` di `.env`; nelle impostazioni dei metodi di pagamento attivare carta, Google Pay e PayPal;
   - con la [Stripe CLI](https://docs.stripe.com/stripe-cli) inoltrare le notifiche all'app e copiare il segreto che stampa (`whsec_...`) in `STRIPE_WEBHOOK_SECRET`:
     ```powershell
     stripe listen --forward-to http://127.0.0.1:5000/webhook/stripe
     ```
   - riavviare l'app e pagare con la carta di prova `4242 4242 4242 4242` (scadenza futura, CVC qualsiasi).

## Profili di prova

Creati da `seed.py`, con password `demo12345` (solo per l'uso in locale):

| Email | Ruolo |
|---|---|
| anna@demo.it, luca@demo.it | Cliente, con due prenotazioni future confermate in due saloni diversi |
| sara, paolo, chiara, giovanni, elena (@demo.it) | Clienti dello storico di 4 mesi (statistiche e recensioni) |
| titolare.napoli, titolare.pozzuoli, titolare.salerno, titolare.caserta, titolare.roma (@demo.it) | Proprietario del salone della sua città (lavora anche in sala) |
| marco@demo.it, giulia@demo.it | Dipendenti della Barberia Plebiscito (Napoli) |
| tommaso, federica, stefano (@demo.it) | Dipendenti dei saloni di Pozzuoli, Salerno e Roma |

Nomi dei saloni e delle persone sono inventati; indirizzi e coordinate sono piazze pubbliche.

## Test

```powershell
python -m pytest
```

I test usano il database `barber_booking_test` e creano da soli due saloni di prova (Napoli e Roma) la prima volta. Coprono l'isolamento tra saloni (nessun proprietario apre o modifica i dati di un altro salone, nessuna prenotazione mescola servizi o professionisti di saloni diversi), la ricerca per zona e per distanza, le recensioni (solo dopo l'appuntamento, una volta, testo mostrato senza HTML), validazioni, repository, calcolo degli slot (compreso il cambio dell'ora legale), prenotazione e pagamento, annullamento con la regola delle 2 ore e da parte del salone, orari delle singole date e festività (anche il calcolo della Pasqua), controllo degli accessi su tutte le rotte, protezione dai dati altrui (IDOR), due prenotazioni simultanee sullo stesso orario, le pagine di gestione del proprietario (orario settimanale, assenze e chiusure, dipendenti, saldo in sede), il cambio password e il limite ai tentativi di login, e Stripe senza chiamarlo davvero (parametri della sessione, rimborsi, firma del webhook).

## Scelte tecniche principali

- **Architettura a strati**: rotte sottili → servizi con le regole → repository con l'SQL → modelli `@dataclass`. I servizi non dipendono da Flask e si testano da soli.
- **OOP**: `PaymentProvider` è una classe astratta (`abc`); i servizi usano solo l'interfaccia, quindi `FakeProvider` (test e demo) e `StripeProvider` sono intercambiabili. Le eccezioni derivano da `BarberBookingError` e un gestore centrale le trasforma in pagine di errore (400, o 404 per i dati non trovati).
- **Doppie prenotazioni**: `SELECT ... FOR UPDATE` sulla riga del dipendente e nuovo controllo dello slot nella stessa transazione dell'`INSERT`, con isolamento `READ COMMITTED`. Un test lancia due richieste in parallelo.
- **Più saloni (multi tenancy)**: tabella `saloni` e colonna `salone_id` in servizi, orari, prenotazioni e staff. Il salone dello staff viene sempre dalla sessione, mai dall'URL; quello del cliente dalla pagina del salone, ma servizi e professionista devono appartenergli. Un dato di un altro salone risulta "non trovato" (404), come per i dati di un altro cliente.
- **Ricerca**: per distanza con `ST_Distance_Sphere` di MySQL (nessuna libreria), con la posizione arrotondata a circa 100 metri e mai salvata; per regione e provincia con i dati ISTAT. L'ordinamento si sceglie da un elenco fisso: nella query non entra mai testo dell'utente.
- **Controllo degli accessi "nega per default"**: ogni area riservata è un Blueprint con un controllo in `before_request`; anonimo → login, ruolo sbagliato → 403. I dati del cliente si leggono con `WHERE id = %s AND cliente_id = %s` (404 per i dati altrui).
- **Sicurezza**: password con hash scrypt di Werkzeug, sessione svuotata al login, al massimo 5 tentativi sbagliati al minuto per indirizzo IP, token CSRF in ogni modulo, query parametrizzate, escape automatico di Jinja, segreti solo in `.env`, utente MySQL con i soli permessi sui dati.
- **Pagamenti**: importi calcolati solo dal server (minimo 0,50 €); la prenotazione si conferma solo con la notifica di Stripe firmata (il ritorno del cliente sul sito non conferma niente); conferma idempotente; rimborso sempre pari a quanto pagato online, con chiave di idempotenza.
- **Date**: istanti salvati in UTC, turni in ora locale del salone, conversione con `zoneinfo`. Prezzi in centesimi interi.

Le motivazioni complete e le alternative scartate sono in `DEVLOG.md` e `docs/PROGETTAZIONE.md`.

## Sviluppi futuri

L'app serve a trovare un barbiere e prenotare; restano solo gli sviluppi che servono a questo (elenco completo e voci tolte in `docs/PROGETTAZIONE.md`, sezione 10):

- Conferma dell'indirizzo email e recupero della password dimenticata.
- Pagina pubblica "Registra il tuo salone", con approvazione prima della pubblicazione (oggi i saloni si creano da terminale).
- Coordinate calcolate dall'indirizzo (geocoding) al posto di quelle copiate da Google Maps; mappe da un fornitore con contratto se il traffico cresce (le tile pubbliche di OpenStreetMap hanno limiti d'uso).

## Crediti

Foto da Unsplash e video da Pexels, ridotti per il web:

| File | Autore |
|---|---|
| `img/barbiere.jpg` | [Agustin Fernandez](https://unsplash.com/photos/1Pmp9uxK8X8) |
| `img/ritratto.jpg` | [Megan Bagshaw](https://unsplash.com/photos/YmaaUNbHHtw) |
| `img/listino.jpg` | [Agustin Fernandez](https://unsplash.com/photos/Znyjl9pbaUs) |
| `img/prenota.jpg` | [Jay Huang](https://unsplash.com/photos/aZBQB-uYosc) |
| `img/area.jpg` | [Arthur Humeau](https://unsplash.com/photos/Twd3yaqA2NM) |
| `img/accedi.jpg` | [Oriol Pascual](https://unsplash.com/photos/pzl6s-FJ72I) |
| `img/registrati.jpg` | [T (@tanyabarrow)](https://unsplash.com/photos/fa0DqQ91dWU) |
| `img/agenda.jpg` | [Ta Focando](https://unsplash.com/photos/1VTQaaI0HP8) |
| `img/gestione.jpg` | [Haberdoedas](https://unsplash.com/photos/zj2CkHpoDPQ) |
| `img/salone.jpg` | [T (@tanyabarrow)](https://unsplash.com/photos/fa0DqQ91dWU) |
| `img/barba.jpg` | [Reza Ghaemi](https://unsplash.com/photos/5P-eClxMg1s) |
| `video/copertina.mp4` | Pexels, video 4177956 |

Mappa: [Leaflet](https://leafletjs.com) (licenza BSD-2) e mappe © [OpenStreetMap](https://www.openstreetmap.org/copyright) e collaboratori. Province: dati ISTAT, dall'elenco dei comuni del progetto [comuni-json](https://github.com/matteocontrini/comuni-json) e, per la Sardegna, dall'elenco ISTAT delle nuove province.

Carattere dei titoli: [Playfair Display](https://fonts.google.com/specimen/Playfair+Display) da Google Fonts (senza connessione il browser usa Georgia).
