import click
from flask.cli import with_appcontext

from app.db import ottieni_connessione
from app.eccezioni import BarberBookingError
from app.servizi.auth import AuthService
from app.servizi.saloni import SaloniService


@click.command("crea-salone")
@click.option("--nome", prompt="Nome del salone")
@click.option("--indirizzo", prompt="Indirizzo (via, numero civico, CAP, comune)")
@click.option("--provincia", prompt="Sigla della provincia (es. NA)")
@click.option("--telefono-salone", prompt="Telefono del salone")
@click.option("--coordinate", prompt="Coordinate da Google Maps (tasto destro sul punto, es. 40.8518, 14.2681)")
@click.option("--acconto", prompt="Percentuale dell'acconto", default="30")
@click.option("--email", prompt="Email del proprietario")
@click.option("--nome-proprietario", prompt="Nome del proprietario")
@click.option("--cognome", prompt="Cognome del proprietario")
@click.option("--telefono", prompt="Telefono del proprietario")
@click.option("--password", prompt="Password del proprietario", hide_input=True, confirmation_prompt=True)
@click.option("--riceve-prenotazioni", is_flag=True,
              prompt="Il proprietario lavora anche come parrucchiere e riceve prenotazioni?")
@with_appcontext
def crea_salone(nome, indirizzo, provincia, telefono_salone, coordinate, acconto,
                email, nome_proprietario, cognome, telefono, password, riceve_prenotazioni):
    """
    Crea un salone e il suo proprietario da terminale: nessuna pagina del sito crea saloni.
    """
    try:
        salone_id, proprietario_id = SaloniService(ottieni_connessione()).crea_con_proprietario(
            {"nome": nome, "indirizzo": indirizzo, "provincia": provincia, "telefono": telefono_salone,
             "coordinate": coordinate, "percentuale_acconto": acconto},
            {"email": email, "password": password, "nome": nome_proprietario, "cognome": cognome,
             "telefono": telefono, "riceve_prenotazioni": riceve_prenotazioni},
        )
    except BarberBookingError as errore:
        raise click.ClickException(str(errore))
    click.echo(f"Salone creato con id {salone_id}, proprietario con id {proprietario_id}.")


@click.command("crea-proprietario")
@click.option("--salone-id", prompt="Id del salone", type=int)
@click.option("--email", prompt="Email")
@click.option("--nome", prompt="Nome")
@click.option("--cognome", prompt="Cognome")
@click.option("--telefono", prompt="Telefono")
@click.option("--password", prompt="Password", hide_input=True, confirmation_prompt=True)
@click.option("--riceve-prenotazioni", is_flag=True,
              prompt="Lavora anche come parrucchiere e riceve prenotazioni?")
@with_appcontext
def crea_proprietario(salone_id, email, nome, cognome, telefono, password, riceve_prenotazioni):
    """
    Aggiunge un proprietario a un salone già esistente (per esempio un socio).
    """
    try:
        utente_id = AuthService(ottieni_connessione()).crea_staff(
            email, password, nome, cognome, telefono, "proprietario", riceve_prenotazioni, salone_id
        )
    except BarberBookingError as errore:
        raise click.ClickException(str(errore))
    click.echo(f"Proprietario creato con id {utente_id}.")
