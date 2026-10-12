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