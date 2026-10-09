from datetime import datetime

from app.modelli.ordine import Ordine, ProdottoOrdinato

def crea_ordine():
    """
    Crea un ordine di prova con due cere ed uno shampoo.
    """
    return Ordine(
        cliente_id = 1,
        scade_il=datetime(2026, 10, 9, 15, 0),
        prodotti=[
            ProdottoOrdinato(prodotto_id=1, nome="Cera Opaca", quantita=2, prezzo_centesimi=1200),
            ProdottoOrdinato(prodotto_id=2, nome="Shampoo", quantita=1, prezzo_centesimi=900),
        ],
    )

def test_prezzo_totale():
    assert crea_ordine().prezzo_totale() == 3300