from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError, ServizioGiaEsistenteError
from app.modelli.servizio import Servizio
from app.repository.servizio import ServizioRepository
from app.servizi.validazione import euro_in_centesimi, testo_facoltativo, testo_obbligatorio

DURATA_MASSIMA_MINUTI = 480


def _durata_valida(valore: str) -> int:
    """
    Controlla la durata in minuti: multiplo di 30, da 30 a DURATA_MASSIMA_MINUTI.
    Returns: la durata come intero.
    Raises: DatiNonValidiError se non è un numero intero valido.
    """
    valore = valore.strip()
    if not valore.isdigit():
        raise DatiNonValidiError("La durata deve essere un numero intero di minuti.")
    durata = int(valore)
    if durata < 30 or durata > DURATA_MASSIMA_MINUTI or durata % 30 != 0:
        raise DatiNonValidiError(
            f"La durata deve essere un multiplo di 30 minuti, da 30 a {DURATA_MASSIMA_MINUTI}."
        )
    return durata


class SaloneService:
    """
    Operazioni del proprietario sul salone. Per ora: gestione dei servizi offerti.
    """

    def __init__(self, connessione):
        self._conn = connessione
        self._servizi = ServizioRepository(connessione)

    def elenca_servizi(self, solo_attivi: bool = True) -> list[Servizio]:
        """
        Elenca i servizi in ordine di nome.
        Args: solo_attivi, False per includere anche i servizi disattivati (pagine del proprietario).
        Returns: la lista dei Servizi.
        """
        return self._servizi.elenca(solo_attivi)

    def leggi_servizio(self, servizio_id: int) -> Servizio:
        """
        Legge un servizio dal suo id.
        Returns: il Servizio.
        Raises: RisorsaNonTrovataError se non esiste.
        """
        servizio = self._servizi.leggi_per_id(servizio_id)
        if servizio is None:
            raise RisorsaNonTrovataError("Servizio non trovato.")
        return servizio

    def crea_servizio(self, nome: str, descrizione: str, durata_minuti: str, prezzo_euro: str) -> int:
        """
        Crea un servizio con i dati del modulo e conferma con commit.
        Returns: l'id del nuovo servizio.
        Raises: DatiNonValidiError se un dato non è valido; ServizioGiaEsistenteError se il nome è già usato.
        """
        servizio = self._servizio_valido(nome, descrizione, durata_minuti, prezzo_euro)
        self._controlla_nome_libero(servizio.nome, None)
        servizio_id = self._servizi.inserisci(servizio)
        self._conn.commit()
        return servizio_id

    def modifica_servizio(self, servizio_id: int, nome: str, descrizione: str,
                          durata_minuti: str, prezzo_euro: str) -> None:
        """
        Modifica nome, descrizione, durata e prezzo di un servizio e conferma con commit.
        Le prenotazioni già fatte non cambiano: hanno la loro copia di durata e prezzo.
        Raises: RisorsaNonTrovataError, DatiNonValidiError, ServizioGiaEsistenteError.
        """
        attuale = self.leggi_servizio(servizio_id)
        servizio = self._servizio_valido(nome, descrizione, durata_minuti, prezzo_euro)
        self._controlla_nome_libero(servizio.nome, servizio_id)
        servizio.id = servizio_id
        servizio.attivo = attuale.attivo
        self._servizi.aggiorna(servizio)
        self._conn.commit()

    def imposta_attivo(self, servizio_id: int, attivo: bool) -> None:
        """
        Disattiva o riattiva un servizio e conferma con commit. I servizi non si cancellano mai.
        Raises: RisorsaNonTrovataError se il servizio non esiste.
        """
        servizio = self.leggi_servizio(servizio_id)
        servizio.attivo = attivo
        self._servizi.aggiorna(servizio)
        self._conn.commit()

    def _servizio_valido(self, nome: str, descrizione: str, durata_minuti: str, prezzo_euro: str) -> Servizio:
        """
        Controlla e converte i dati del modulo.
        Returns: un Servizio senza id.
        Raises: DatiNonValidiError se un dato non è valido o il prezzo è zero.
        """
        prezzo_centesimi = euro_in_centesimi(prezzo_euro, "prezzo")
        if prezzo_centesimi == 0:
            raise DatiNonValidiError("Il prezzo deve essere maggiore di zero.")
        return Servizio(
            nome=testo_obbligatorio(nome, "nome", 100),
            descrizione=testo_facoltativo(descrizione, "descrizione", 255),
            durata_minuti=_durata_valida(durata_minuti),
            prezzo_centesimi=prezzo_centesimi,
        )

    def _controlla_nome_libero(self, nome: str, servizio_id: int | None) -> None:
        """
        Controlla che il nome non sia usato da un altro servizio.
        Args: servizio_id, il servizio in modifica (può tenere il suo nome), None per uno nuovo.
        Raises: ServizioGiaEsistenteError se il nome appartiene a un altro servizio.
        """
        esistente = self._servizi.leggi_per_nome(nome)
        if esistente is not None and esistente.id != servizio_id:
            raise ServizioGiaEsistenteError(f"Esiste già un servizio chiamato «{esistente.nome}».")
