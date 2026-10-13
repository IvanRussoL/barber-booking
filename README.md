# Barber Booking

Applicazione web per un salone di barbiere/parrucchiere: i clienti prenotano online servizi e professionista pagando un acconto o l'intero importo, i professionisti consultano la propria agenda e il proprietario gestisce il listino. Progetto finale del corso Full Stack Python.

> Stato: versione consegnata per il corso. Il pagamento è simulato (`FakeProvider`); Stripe, vendita di prodotti e statistiche sono negli sviluppi futuri.

## Funzionalità

| Ruolo | Cosa può fare |
|---|---|
| Visitatore | Consulta servizi e prezzi, si registra come cliente |
| Cliente | Prenota uno o più servizi scegliendo professionista, data e orario libero; paga acconto o importo completo; consulta lo storico con il totale speso; annulla fino a 2 ore prima con rimborso |
| Dipendente | Consulta la propria agenda con i recapiti dei clienti |
| Proprietario | Crea, modifica, disattiva e riattiva i servizi; se lavora in sala riceve prenotazioni e ha la sua agenda |

Regole principali: slot di 30 minuti dentro i turni del salone, nessuna sovrapposizione per lo stesso professionista né per lo stesso cliente (anche con richieste simultanee), prenotazione bloccata per 30 minuti in attesa del pagamento, prezzi e importi calcolati sempre dal server.

## Tecnologie

- Python 3.13, Flask 3, Jinja
- MySQL 8 con `mysql-connector-python` e query SQL scritte a mano (nessun ORM)
- HTML, CSS e JavaScript (`fetch` per gli orari liberi)
- Flask-WTF (solo protezione CSRF), python-dotenv, tzdata
- pytest

## Struttura

```
barber-booking/
├── app/
│   ├── __init__.py        # create_app(): configurazione, Blueprint, gestori degli errori
│   ├── modelli/           # dataclass: Utente, Servizio, Prenotazione, Pagamento, ...
│   ├── repository/        # unico posto con SQL, sempre parametrizzato
│   ├── servizi/           # regole di business, senza Flask: AuthService, SaloneService,
│   │                      #   DisponibilitaService, PrenotazioneService
│   ├── pagamenti/         # PaymentProvider (classe astratta) e FakeProvider
│   ├── rotte/             # Blueprint: pubblico, auth, cliente, dipendente, proprietario
│   ├── templates/         # pagine Jinja, una cartella per Blueprint
│   ├── static/            # CSS e JavaScript
│   ├── accessi.py         # controllo comune dei Blueprint riservati
│   ├── comandi.py         # flask crea-proprietario
│   ├── eccezioni.py       # BarberBookingError e sottoclassi
│   └── db.py              # connessione a MySQL
├── database/schema.sql    # tabelle, vincoli e dati iniziali
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
5. Proprietario (le domande compaiono nel terminale):
   ```powershell
   flask --app app crea-proprietario
   ```
6. Dati di prova (facoltativo):
   ```powershell
   python seed.py
   ```
7. Avvio: `python run.py`, poi aprire http://127.0.0.1:5000

## Profili di prova

Creati da `seed.py`, con password `demo12345` (solo per l'uso in locale):

| Email | Ruolo |
|---|---|
| anna@demo.it, luca@demo.it | Cliente, con due prenotazioni confermate |
| marco@demo.it, giulia@demo.it | Dipendente |

Il proprietario è quello creato al punto 5.

## Test

```powershell
python -m pytest
```

I test usano il database `barber_booking_test`. Coprono validazioni, repository, calcolo degli slot (compreso il cambio dell'ora legale), prenotazione e pagamento, annullamento con la regola delle 2 ore, controllo degli accessi su tutte le rotte, protezione dai dati altrui (IDOR) e due prenotazioni simultanee sullo stesso orario.

## Scelte tecniche principali

- **Architettura a strati**: rotte sottili → servizi con le regole → repository con l'SQL → modelli `@dataclass`. I servizi non dipendono da Flask e si testano da soli.
- **OOP**: `PaymentProvider` è una classe astratta (`abc`); i servizi usano solo l'interfaccia, quindi `FakeProvider` e un futuro `StripeProvider` sono intercambiabili. Le eccezioni derivano da `BarberBookingError` e un gestore centrale le trasforma in pagine di errore (400, o 404 per i dati non trovati).
- **Doppie prenotazioni**: `SELECT ... FOR UPDATE` sulla riga del dipendente e nuovo controllo dello slot nella stessa transazione dell'`INSERT`, con isolamento `READ COMMITTED`. Un test lancia due richieste in parallelo.
- **Controllo degli accessi "nega per default"**: ogni area riservata è un Blueprint con un controllo in `before_request`; anonimo → login, ruolo sbagliato → 403. I dati del cliente si leggono con `WHERE id = %s AND cliente_id = %s` (404 per i dati altrui).
- **Sicurezza**: password con hash scrypt di Werkzeug, sessione svuotata al login, token CSRF in ogni modulo, query parametrizzate, escape automatico di Jinja, segreti solo in `.env`, utente MySQL con i soli permessi sui dati.
- **Date**: istanti salvati in UTC, turni in ora locale del salone, conversione con `zoneinfo`. Prezzi in centesimi interi.

Le motivazioni complete e le alternative scartate sono in `DEVLOG.md` e `docs/PROGETTAZIONE.md`.

## Sviluppi futuri

- Pagamento reale con Stripe Checkout (carta, Google Pay, PayPal) e conferma tramite webhook con firma verificata.
- Vendita di prodotti con carrello, foto e ritiro in negozio.
- Statistiche con pandas e matplotlib: prenotazioni per dipendente, occupazione, fasce di punta, ricavi.
- Gestione dal sito di orari, eccezioni per data, assenze e chiusure; creazione dei dipendenti da parte del proprietario.
- Saldo in sede registrato dal proprietario, annullamenti da parte del salone.
- Limite ai tentativi di login (Flask-Limiter), cambio e recupero della password.
