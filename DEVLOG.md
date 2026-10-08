# DEVLOG – Barber Booking

Diario delle scelte di sviluppo: cosa è stato fatto, perché e quali alternative sono state scartate.

## 2026-10-08 · Fase 1 – Setup

- **Ambiente virtuale `venv`**: isola le librerie del progetto e rende riproducibile l'installazione. Alternative scartate: `pipenv` e `poetry` (più strumenti da spiegare, `venv` è incluso in Python).
- **Database MySQL con `mysql-connector-python`**: richiesto dalla consegna del corso e driver visto a lezione. Alternativa scartata: SQLite (più semplice, ma fuori dalla consegna).
- **`.gitignore` creato prima del primo commit**: il repository diventerà pubblico e la cronologia di Git conserva tutto; così segreti (`.env`) e venv non entrano mai nella storia.
- **Email dei commit `noreply` di GitHub**: evita di esporre l'email personale nel repository pubblico.
- **Repository privata durante lo sviluppo**, pubblica a progetto finito.
- **Flask + mysql-connector-python, versioni bloccate in `requirements.txt`**: framework leggero e driver visto nel corso; versioni fissate per riprodurre l'ambiente. Alternative scartate: Django (troppo integrato, nasconde ciò che vogliamo mostrare), ORM come SQLAlchemy (fuori dal perimetro del corso).