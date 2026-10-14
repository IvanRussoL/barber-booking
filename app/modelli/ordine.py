from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProdottoOrdinato:
    """
    Prodotto dentro un ordine, con quantità e prezzo fissati al momento dell'acquisto.
    """
    prodotto_id: int
    nome: str
    quantita: int
    prezzo_centesimi: int
    ordine_id: int | None = None

@dataclass
class Ordine:
    """
    Acquisto di prodotti di un cliente, da ritirare in negozio.
    """
    cliente_id: int
    scade_il: datetime
    salone_id: int | None = None
    prodotti: list[ProdottoOrdinato] = field(default_factory=list)
    stato: str = "in_attesa_pagamento"
    ritirato_il: datetime | None = None
    annullato_il: datetime | None = None
    creato_il: datetime | None = None
    id: int | None = None

    def prezzo_totale(self) -> int:
        """
        Restituisce il totale dell'ordine in centesimi, somma di quantità per prezzo di ogni prodotto.
        """
        return sum(p.quantita * p.prezzo_centesimi for p in self.prodotti)