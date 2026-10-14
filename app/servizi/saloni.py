import re
from dataclasses import dataclass
from datetime import time
from decimal import ROUND_HALF_UP, Decimal

from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError
from app.modelli.orario import Turno
from app.modelli.salone import Provincia, Salone
from app.repository.orario import OrarioRepository
from app.repository.provincia import ProvinciaRepository
from app.repository.salone import SaloneRepository
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService
from app.servizi.validazione import telefono_valido, testo_obbligatorio

# Calendario di partenza di un nuovo salone: lunedì chiuso, dal martedì alla domenica 09:00-13:00 e 15:00-23:00.
# Il proprietario cambia poi gli orari delle singole date dal sito.
ORARIO_DI_PARTENZA = {
    giorno: [Turno(time(9, 0), time(13, 0)), Turno(time(15, 0), time(23, 0))] for giorno in range(2, 8)
}

# Per ora i saloni sono solo in Italia: le coordinate devono cadere in questo rettangolo.
LATITUDINE_ITALIA = (Decimal("35.0"), Decimal("47.5"))
LONGITUDINE_ITALIA = (Decimal("6.0"), Decimal("19.0"))
SEI_DECIMALI = Decimal("0.000001")

# Ricerca: raggi che il cliente può scegliere e ordinamenti, con l'etichetta mostrata nella pagina.
RAGGI_KM = (5, 10, 25, 50)
RAGGIO_PREDEFINITO_KM = 10
ORDINI_VICINO = {"distanza": "Più vicini", "recensioni": "Recensioni migliori", "nome": "Nome (A-Z)"}
ORDINI_ZONA = {"recensioni": "Recensioni migliori", "nome": "Nome (A-Z)"}


@dataclass
class RisultatoRicerca:
    """
    Un salone trovato dalla ricerca, con la sua provincia, le recensioni e, nella ricerca per posizione,
    la distanza.
    """
    salone: Salone
    provincia_nome: str
    regione: str
    distanza_km: float | None = None
    media_voti: float | None = None
    numero_recensioni: int = 0


def coordinate_valide(valore: str) -> tuple[Decimal, Decimal]:
    """
    Converte le coordinate copiate da Google Maps (tasto destro sul punto), es. "40.851800, 14.268100".
    Returns: (latitudine, longitudine) con 6 decimali (circa 10 cm di precisione).
    Raises: DatiNonValidiError se il formato non è valido o il punto non cade in Italia.
    """
    trovato = re.fullmatch(r"\s*(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*", valore or "")
    if trovato is None:
        raise DatiNonValidiError(
            "Scrivi le coordinate come le copia Google Maps: latitudine, longitudine (es. 40.8518, 14.2681)."
        )
    latitudine, longitudine = (Decimal(numero).quantize(SEI_DECIMALI, ROUND_HALF_UP) for numero in trovato.groups())
    if not (LATITUDINE_ITALIA[0] <= latitudine <= LATITUDINE_ITALIA[1]
            and LONGITUDINE_ITALIA[0] <= longitudine <= LONGITUDINE_ITALIA[1]):
        raise DatiNonValidiError(
            "Le coordinate devono indicare un punto in Italia: controlla di non aver invertito latitudine e longitudine."
        )
    return latitudine, longitudine


def percentuale_valida(valore: str) -> int:
    """
    Converte la percentuale dell'acconto: un intero da 1 a 99.
    Raises: DatiNonValidiError se non è valida.
    """
    valore = str(valore).strip()
    if not valore.isdigit() or not 1 <= int(valore) <= 99:
        raise DatiNonValidiError("L'acconto deve essere una percentuale intera da 1 a 99.")
    return int(valore)


class SaloniService:
    """
    I saloni della piattaforma: creazione (dal comando crea-salone) e lettura delle pagine pubbliche.
    """

    def __init__(self, connessione):
        self._conn = connessione
        self._saloni = SaloneRepository(connessione)
        self._province = ProvinciaRepository(connessione)

    def salone_pubblico(self, salone_id: int) -> Salone:
        """
        Il salone di una pagina pubblica: deve esistere ed essere attivo.
        Returns: il Salone.
        Raises: RisorsaNonTrovataError se non esiste o è disattivato (stessa risposta: 404).
        """
        salone = self._saloni.leggi_per_id(salone_id)
        if salone is None or not salone.attivo:
            raise RisorsaNonTrovataError("Salone non trovato.")
        return salone

    def salone_valido(self, nome: str, indirizzo: str, provincia: str, telefono: str,
                      coordinate: str, percentuale_acconto: str) -> Salone:
        """
        Controlla e converte i dati di un nuovo salone, senza salvare niente.
        Returns: il Salone senza id.
        Raises: DatiNonValidiError se un dato non è valido o la provincia non esiste.
        """
        sigla = testo_obbligatorio(provincia, "provincia", 2).upper()
        if self._province.leggi(sigla) is None:
            raise DatiNonValidiError("Provincia non trovata: scrivi la sigla, ad esempio NA o MI.")
        latitudine, longitudine = coordinate_valide(coordinate)
        return Salone(
            nome=testo_obbligatorio(nome, "nome del salone", 100),
            indirizzo=testo_obbligatorio(indirizzo, "indirizzo", 255),
            provincia=sigla,
            telefono=telefono_valido(telefono),
            latitudine=latitudine,
            longitudine=longitudine,
            percentuale_acconto=percentuale_valida(percentuale_acconto),
        )

    def crea_con_proprietario(self, salone: dict, proprietario: dict) -> tuple[int, int]:
        """
        Crea un salone con il suo calendario di partenza e il suo proprietario, in un'unica transazione:
        se un dato del proprietario non è valido non resta un salone senza proprietario.
        Args: salone con nome, indirizzo, provincia, telefono, coordinate, percentuale_acconto;
            proprietario con email, password, nome, cognome, telefono, riceve_prenotazioni.
        Returns: (id del salone, id del proprietario).
        Raises: DatiNonValidiError, EmailGiaRegistrataError.
        """
        nuovo = self.salone_valido(**salone)
        utente = AuthService(self._conn).utente_valido(
            proprietario["email"], proprietario["password"], proprietario["nome"], proprietario["cognome"],
            proprietario["telefono"], "proprietario", bool(proprietario.get("riceve_prenotazioni")),
        )
        salone_id = self._saloni.inserisci(nuovo)
        orari = OrarioRepository(self._conn)
        for giorno, turni in ORARIO_DI_PARTENZA.items():
            for turno in turni:
                orari.inserisci_turno_settimanale(salone_id, giorno, turno)
        utente.salone_id = salone_id
        proprietario_id = UtenteRepository(self._conn).inserisci(utente)
        self._conn.commit()
        return salone_id, proprietario_id

    # --- Ricerca ---

    def regioni(self) -> list[str]:
        """
        Le regioni italiane, per il primo menu della ricerca per zona.
        """
        return self._province.regioni()

    def province(self) -> list[Provincia]:
        """
        Tutte le province con la loro regione, per il secondo menu della ricerca per zona.
        """
        return self._province.elenca()

    def cerca_per_zona(self, regione: str, provincia: str = "", ordine: str = "recensioni") -> list[RisultatoRicerca]:
        """
        Saloni di una regione, oppure di una sua provincia se è indicata.
        Args: ordine fra ORDINI_ZONA; un valore non previsto diventa l'ordine per recensioni.
        Returns: la lista dei RisultatoRicerca.
        Raises: DatiNonValidiError se la regione non esiste o la provincia non è di quella regione.
        """
        if regione not in self.regioni():
            raise DatiNonValidiError("Scegli una regione dall'elenco.")
        sigla = None
        if provincia:
            trovata = self._province.leggi(provincia)
            if trovata is None or trovata.regione != regione:
                raise DatiNonValidiError("Scegli una provincia della regione indicata.")
            sigla = trovata.sigla
        ordine = ordine if ordine in ORDINI_ZONA else "recensioni"
        return [_risultato(riga) for riga in self._saloni.cerca(regione=regione, provincia=sigla, ordine=ordine)]

    def cerca_vicino(self, latitudine: str, longitudine: str, raggio_km: str = "",
                     ordine: str = "distanza") -> list[RisultatoRicerca]:
        """
        Saloni entro il raggio scelto dalla posizione del cliente. La posizione serve solo a questa ricerca:
        non viene salvata da nessuna parte.
        Args: latitudine e longitudine come testo (dalla richiesta); raggio_km fra RAGGI_KM (altrimenti
            RAGGIO_PREDEFINITO_KM); ordine fra ORDINI_VICINO (altrimenti per distanza).
        Returns: la lista dei RisultatoRicerca con la distanza in km.
        Raises: DatiNonValidiError se la posizione non è valida.
        """
        punto = posizione_valida(latitudine, longitudine)
        raggio = raggio_valido(raggio_km)
        ordine = ordine if ordine in ORDINI_VICINO else "distanza"
        righe = self._saloni.cerca(punto=punto, raggio_metri=raggio * 1000, ordine=ordine)
        return [_risultato(riga) for riga in righe]


def raggio_valido(valore: str) -> int:
    """
    Converte il raggio scelto nella pagina; un valore non previsto diventa RAGGIO_PREDEFINITO_KM.
    """
    return int(valore) if valore in {str(r) for r in RAGGI_KM} else RAGGIO_PREDEFINITO_KM


def posizione_valida(latitudine: str, longitudine: str) -> tuple[float, float]:
    """
    Converte la posizione inviata dal browser in due numeri, arrotondati a 3 decimali (circa 100 metri):
    per cercare un salone non serve una posizione più precisa.
    Returns: (latitudine, longitudine).
    Raises: DatiNonValidiError se non sono numeri o sono fuori dai valori possibili.
    """
    try:
        lat, lon = round(float(latitudine), 3), round(float(longitudine), 3)
    except (TypeError, ValueError):
        raise DatiNonValidiError("Posizione non valida: riprova oppure cerca per regione e provincia.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):  # anche NaN e infinito non passano questo controllo
        raise DatiNonValidiError("Posizione non valida: riprova oppure cerca per regione e provincia.")
    return lat, lon


def _risultato(riga: dict) -> RisultatoRicerca:
    """
    Trasforma una riga della ricerca in RisultatoRicerca, con la distanza in km.
    """
    distanza_metri = riga.pop("distanza_metri")
    media_voti = riga.pop("media_voti")
    extra = {campo: riga.pop(campo) for campo in ("provincia_nome", "regione", "numero_recensioni")}
    riga["attivo"] = bool(riga["attivo"])
    return RisultatoRicerca(
        salone=Salone(**riga),
        distanza_km=None if distanza_metri is None else round(distanza_metri / 1000, 1),
        media_voti=None if media_voti is None else round(float(media_voti), 1),
        **extra,
    )
