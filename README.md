# Barber Booking

Applicazione web per un salone di barbiere/parrucchiere: i clienti prenotano online servizi e professionista pagando un acconto o l'intero importo, i professionisti consultano la propria agenda e il proprietario gestisce il listino. Progetto finale del corso Full Stack Python.

> Stato: versione consegnata per il corso. Il pagamento è simulato (`FakeProvider`); Stripe e vendita di prodotti sono negli sviluppi futuri.

## Funzionalità

| Ruolo | Cosa può fare |
|---|---|
| Visitatore | Vede se il salone è aperto in quel momento, consulta orari (con le date particolari), servizi e prezzi, si registra come cliente |
| Cliente | Prenota uno o più servizi scegliendo professionista, data e orario libero; paga acconto o importo completo; consulta lo storico con il totale speso; annulla fino a 2 ore prima con rimborso |
| Dipendente | Consulta la propria agenda con i recapiti dei clienti e lo storico (anche le annullate); annulla un proprio appuntamento con rimborso al cliente; vede le proprie statistiche |
| Proprietario | Gestisce i servizi; nella pagina Dipendenti vede recapiti, lavoro e agenda di ogni professionista e il totale del salone su settimana, mese o anno; annulla qualsiasi prenotazione con rimborso; decide gli orari delle singole date (chiusure, festività); consulta le statistiche; se lavora in sala riceve prenotazioni |

Regole principali: slot di 30 minuti dentro i turni del salone (festività e vigilie restano "da definire" e prenotabili con un avviso finché il proprietario non decide l'orario), nessuna sovrapposizione per lo stesso professionista né per lo stesso cliente (anche con richieste simultanee), prenotazione bloccata per 30 minuti in attesa del pagamento, prezzi e importi calcolati sempre dal server.

## Tecnologie

- Python 3.13, Flask 3, Jinja
- MySQL 8 con `mysql-connector-python` e query SQL scritte a mano (nessun ORM)
- HTML, CSS e JavaScript (`fetch` per gli orari liberi), Playfair Display da Google Fonts per i titoli
- Flask-WTF (solo protezione CSRF), python-dotenv, tzdata
- pandas e matplotlib per le statistiche (grafici generati in memoria)
- pytest

## Struttura

```
barber-booking/
├── app/
│   ├── __init__.py        # create_app(): configurazione, Blueprint, gestori degli errori
│   ├── modelli/           # dataclass: Utente, Servizio, Prenotazione, Pagamento, ...
│   ├── repository/        # unico posto con SQL, sempre parametrizzato
│   ├── servizi/           # regole di business, senza Flask: AuthService, SaloneService,
│   │                      #   DisponibilitaService, PrenotazioneService, CalendarioService,
│   │                      #   StatisticheService
│   ├── pagamenti/         # PaymentProvider (classe astratta) e FakeProvider
│   ├── rotte/             # Blueprint: pubblico, auth, cliente, dipendente, proprietario
│   ├── templates/         # pagine Jinja, una cartella per Blueprint
│   ├── static/            # CSS, JavaScript e foto ridotte (img/)
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
| anna@demo.it, luca@demo.it | Cliente, con due prenotazioni future confermate |
| sara, paolo, chiara, giovanni, elena (@demo.it) | Clienti dello storico di 4 mesi usato dalle statistiche |
| marco@demo.it, giulia@demo.it | Dipendente |

Il proprietario è quello creato al punto 5.

## Test

```powershell
python -m pytest
```

I test usano il database `barber_booking_test`. Coprono validazioni, repository, calcolo degli slot (compreso il cambio dell'ora legale), prenotazione e pagamento, annullamento con la regola delle 2 ore e da parte del salone, orari delle singole date e festività (anche il calcolo della Pasqua), controllo degli accessi su tutte le rotte, protezione dai dati altrui (IDOR) e due prenotazioni simultanee sullo stesso orario.

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
- Statistiche avanzate: occupazione rispetto all'orario, funnel visite → prenotazioni con il tracciamento delle visite.
- Gestione dal sito del calendario settimanale, delle assenze e delle chiusure lunghe; creazione dei dipendenti da parte del proprietario.
- Saldo in sede registrato dal proprietario.
- Limite ai tentativi di login (Flask-Limiter), cambio e recupero della password.
- Foto per ogni servizio, caricate dal proprietario e controllate con Pillow.

## Crediti

Foto da Unsplash, ridotte per il web:

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

Carattere dei titoli: [Playfair Display](https://fonts.google.com/specimen/Playfair+Display) da Google Fonts (senza connessione il browser usa Georgia).
