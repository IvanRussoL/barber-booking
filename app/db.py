import os

import mysql.connector
from flask import g

def crea_connessione():
    """
    Apre una nuova connessione a MySQL con i parametri letti dalle variabili d'ambiente.
    Returns: la connessione aperta, con autocommit spento.
    Raises: KeyError se manca una variabile; mysql.connector.Error se la connessione fallisce.
    """
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )

def ottieni_connessione():
    """
    Restituisce la connessione della richiesta in corso, aprendola al primo uso.
    Returns: la connessione salvata in g.
    """
    if "conn" not in g:
        g.conn = crea_connessione()
    return g.conn


def chiudi_connessione(errore=None):
    """
    A fine richiesta annulla le modifiche senza commit e chiude la connessione.
    Args: errore, l'eccezione che ha interrotto la richiesta (la passa Flask), oppure None.
    """
    conn = g.pop("conn", None)
    if conn is not None:
        conn.rollback()
        conn.close()