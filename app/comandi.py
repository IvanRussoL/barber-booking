import click
from flask.cli import with_appcontext

from app.db import ottieni_connessione
from app.eccezioni import BarberBookingError
from app.servizi.auth import AuthService


@click.command("crea-proprietario")
@click.option("--email", prompt="Email")
@click.option("--nome", prompt="Nome")
@click.option("--cognome", prompt="Cognome")
@click.option("--telefono", prompt="Telefono")
@click.option("--password", prompt="Password", hide_input=True, confirmation_prompt=True)
@click.option("--riceve-prenotazioni", is_flag=True,
              prompt="Lavora anche come parrucchiere e riceve prenotazioni?")
@with_appcontext
def crea_proprietario(email, nome, cognome, telefono, password, riceve_prenotazioni):
    """
    Crea il proprietario del salone da terminale: nessuna pagina del sito assegna questo ruolo.
    """
    try:
        utente_id = AuthService(ottieni_connessione()).crea_staff(
            email, password, nome, cognome, telefono, "proprietario", riceve_prenotazioni
        )
    except BarberBookingError as errore:
        raise click.ClickException(str(errore))
    click.echo(f"Proprietario creato con id {utente_id}.")
