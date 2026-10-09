from datetime import datetime

from app.modelli.prenotazione import Prenotazione, ServizioPrenotato


def crea_prenotazione():
    """Crea una prenotazione di prova con taglio e barba."""
    return Prenotazione(
        cliente_id=1,
        dipendente_id=2,
        inizio=datetime(2026, 11, 3, 9, 0),
        fine=datetime(2026, 11, 3, 10, 0),
        modalita_pagamento="acconto",
        scade_il=datetime(2026, 10, 9, 12, 30),
        servizi=[
            ServizioPrenotato(servizio_id=1, nome="Taglio", durata_minuti=30, prezzo_centesimi=2000),
            ServizioPrenotato(servizio_id=2, nome="Barba", durata_minuti=30, prezzo_centesimi=1500),
        ],
    )


def test_durata_totale():
    assert crea_prenotazione().durata_totale() == 60


def test_prezzo_totale():
    assert crea_prenotazione().prezzo_totale() == 3500