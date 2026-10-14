from app.modelli.salone import Salone

_COLONNE = (
    "id, nome, indirizzo, provincia, telefono, fuso_orario, latitudine, longitudine, "
    "percentuale_acconto, mesi_prenotabili, attivo, creato_il"
)


def _da_riga(riga: dict) -> Salone:
    """
    Trasforma una riga di saloni in un oggetto Salone, convertendo attivo da 0/1 a bool.
    """
    riga["attivo"] = bool(riga["attivo"])
    return Salone(**riga)


class SaloneRepository:
    """
    Accesso alla tabella saloni.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, salone: Salone) -> int:
        """
        Inserisce un nuovo salone, senza fare commit.
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se la provincia non esiste.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO saloni (nome, indirizzo, provincia, telefono, fuso_orario, latitudine, longitudine, "
                "percentuale_acconto, mesi_prenotabili, attivo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (salone.nome, salone.indirizzo, salone.provincia, salone.telefono, salone.fuso_orario,
                 salone.latitudine, salone.longitudine, salone.percentuale_acconto, salone.mesi_prenotabili,
                 salone.attivo),
            )
            return cur.lastrowid

    def leggi_per_id(self, salone_id: int) -> Salone | None:
        """
        Legge un salone dal suo id, anche se disattivato.
        Returns: il Salone, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(f"SELECT {_COLONNE} FROM saloni WHERE id = %s", (salone_id,))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def leggi_per_nome(self, nome: str) -> Salone | None:
        """
        Legge un salone dal nome (il primo, se ce ne sono più con lo stesso nome). Usato da seed.py e dai test.
        Returns: il Salone, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(f"SELECT {_COLONNE} FROM saloni WHERE nome = %s ORDER BY id LIMIT 1", (nome,))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def cerca(self, regione: str | None = None, provincia: str | None = None,
              punto: tuple[float, float] | None = None, raggio_metri: int | None = None,
              ordine: str = "nome", limite: int = 100) -> list[dict]:
        """
        Saloni attivi che rispettano i filtri, con il nome della provincia, la regione, la media dei voti
        e il numero di recensioni e, se c'è un punto, la distanza in metri calcolata da MySQL
        (ST_Distance_Sphere, distanza sulla superficie terrestre).
        Args: regione e provincia (sigla) per la ricerca per zona; punto (latitudine, longitudine) e
            raggio_metri per la ricerca intorno al cliente; ordine "nome", "recensioni" o "distanza"
            (quest'ultimo solo con il punto).
        Returns: righe con le colonne del salone più provincia_nome, regione, media_voti, numero_recensioni
            e distanza_metri (None senza punto).
        Raises: ValueError se l'ordine non è tra quelli previsti.
        """
        # L'ordine arriva da una lista fissa: nella query non finisce mai testo scritto dall'utente.
        ordinamenti = {
            "nome": "s.nome, s.id",
            "distanza": "distanza_metri, s.nome",
            # Prima i saloni con recensioni (media più alta, poi più recensioni), in fondo quelli senza.
            "recensioni": "r.media_voti IS NULL, r.media_voti DESC, r.numero_recensioni DESC, s.nome",
        }
        if ordine not in ordinamenti or (ordine == "distanza" and punto is None):
            raise ValueError(f"Ordine non previsto: {ordine}")
        colonne = ", ".join("s." + c.strip() for c in _COLONNE.split(","))
        parametri: list = []
        if punto is not None:
            # POINT vuole prima la longitudine (x) e poi la latitudine (y).
            distanza = "ST_Distance_Sphere(POINT(s.longitudine, s.latitudine), POINT(%s, %s))"
            sql = f"SELECT {colonne}, {distanza} AS distanza_metri, "
            parametri += [punto[1], punto[0]]
        else:
            sql = f"SELECT {colonne}, NULL AS distanza_metri, "
        sql += (
            "p.nome AS provincia_nome, p.regione, r.media_voti, COALESCE(r.numero_recensioni, 0) AS numero_recensioni "
            "FROM saloni s JOIN province p ON p.sigla = s.provincia "
            "LEFT JOIN (SELECT salone_id, AVG(voto) AS media_voti, COUNT(*) AS numero_recensioni "
            "FROM recensioni GROUP BY salone_id) r ON r.salone_id = s.id "
            "WHERE s.attivo = TRUE "
        )
        if regione is not None:
            sql += "AND p.regione = %s "
            parametri.append(regione)
        if provincia is not None:
            sql += "AND s.provincia = %s "
            parametri.append(provincia)
        if punto is not None and raggio_metri is not None:
            sql += f"AND {distanza} <= %s "
            parametri += [punto[1], punto[0], raggio_metri]
        sql += f"ORDER BY {ordinamenti[ordine]} LIMIT %s"
        parametri.append(limite)
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(sql, parametri)
            return cur.fetchall()
