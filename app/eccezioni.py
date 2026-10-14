class BarberBookingError(Exception):
    """
    Classe base delle eccezioni del progetto: indica una regola di business violata.
    """

    
class DatiNonValidiError(BarberBookingError):
    """
    Dati inviati dall'utente non validi (es. campo vuoto, password troppo corta).
    """


class EmailGiaRegistrataError(BarberBookingError):
    """
    Registrazione con un'email già usata da un altro utente.
    """


class CredenzialiNonValideError(BarberBookingError):
    """
    Login fallito: email o password errate, oppure account disattivato.
    """


class ServizioGiaEsistenteError(BarberBookingError):
    """
    Servizio creato o rinominato con un nome già usato da un altro servizio.
    """


class RisorsaNonTrovataError(BarberBookingError):
    """
    Dato richiesto inesistente, o di un altro utente: viene mostrato come pagina non trovata (404).
    """


class SlotNonDisponibileError(BarberBookingError):
    """
    Orario scelto non prenotabile: fuori dai turni, già occupato o nel frattempo preso da un altro cliente.
    """


class RecensioneNonConsentitaError(BarberBookingError):
    """
    Recensione non permessa: appuntamento non ancora svolto, annullato o già recensito.
    """


class AnnullamentoNonConsentitoError(BarberBookingError):
    """
    Annullamento non permesso: prenotazione non confermata o a meno di 2 ore dall'inizio.
    """
