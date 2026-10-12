import os

from flask import Flask

def create_app(config: dict | None = None) -> Flask:
    """
    Crea e configura l'applicazione Flask.
    Args: config, valori che sostituiscono quelli predefiniti (usato dai test).
    Returns: l'applicazione configurata.
    Raises: KeyError se SECRET_KEY manca dalle variabili d'ambiente.
    """

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ["SECRET_KEY"],
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    return app