import os

import mysql.connector

def crea_connessione():
    """
    Apre una nuova connessiona a MySQL con i parametri letti dalle variabili d'ambiente.
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