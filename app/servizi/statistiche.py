from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")  # disegna in memoria, senza aprire finestre: adatto a un server
import matplotlib.pyplot as plt  
import pandas as pd  

from app.eccezioni import RisorsaNonTrovataError  # noqa: E402
from app.repository.salone import SaloneRepository  # noqa: E402
from app.repository.statistiche import StatisticheRepository  # noqa: E402

PERIODI = (7, 30, 365)  # settimana, mese e anno: i giorni che si possono scegliere nella pagina

# Colori del tema: un solo colore per i dati, gli altri per testo e assi.
CORALLO = "#b4472f"
CREMA = "#fbf8f3"
TESTO = "#2a211c"
TESTO_TENUE = "#6b5f55"
BORDO = "#e2d9cb"


def periodo_valido(valore: str | None) -> int:
    """
    Converte il periodo scelto nella pagina; un valore non previsto diventa il mese (30 giorni).
    """
    return int(valore) if valore in {str(p) for p in PERIODI} else 30


@dataclass
class Riepilogo:
    """
    Numeri principali del periodo, mostrati in cima alla pagina.
    """
    prenotazioni: int
    clienti_unici: int
    valore_servizi_centesimi: int
    valore_medio_centesimi: int
    incasso_netto_centesimi: int | None = None  # solo per il proprietario


class StatisticheService:
    """
    Statistiche di un salone su prenotazioni confermate e incassi, calcolate con pandas e disegnate
    con matplotlib.
    """

    def __init__(self, connessione, salone_id: int):
        """
        Raises: RisorsaNonTrovataError se il salone non esiste.
        """
        salone = SaloneRepository(connessione).leggi_per_id(salone_id)
        if salone is None:
            raise RisorsaNonTrovataError("Salone non trovato.")
        self._salone_id = salone_id
        self._repo = StatisticheRepository(connessione)
        self._fuso_orario = ZoneInfo(salone.fuso_orario)

    # --- Dati ---

    def _intervallo(self, giorni: int, adesso: datetime | None) -> tuple[datetime, datetime]:
        """
        Ultimi `giorni` giorni fino ad adesso, in UTC senza fuso orario come nel database.
        """
        fine = (adesso or datetime.now(UTC)).astimezone(UTC).replace(tzinfo=None)
        return fine - timedelta(days=giorni), fine

    def _prenotazioni(self, giorni: int, adesso: datetime | None, dipendente_id: int | None = None) -> pd.DataFrame:
        """
        Prenotazioni confermate del periodo come DataFrame, con l'inizio convertito nell'ora locale del salone.
        """
        da, a = self._intervallo(giorni, adesso)
        tabella = pd.DataFrame(
            self._repo.prenotazioni_confermate(self._salone_id, da, a, dipendente_id),
            columns=["id", "dipendente_id", "professionista", "cliente_id", "inizio", "totale_centesimi"],
        )
        tabella["totale_centesimi"] = tabella["totale_centesimi"].astype(int)
        tabella["inizio"] = pd.to_datetime(tabella["inizio"]).dt.tz_localize("UTC").dt.tz_convert(self._fuso_orario)
        return tabella

    def riepilogo(self, giorni: int, adesso: datetime | None = None, dipendente_id: int | None = None) -> Riepilogo:
        """
        Prenotazioni confermate, clienti diversi, valore dei servizi e valore medio del periodo;
        per il salone intero (dipendente_id None) anche l'incasso netto (pagamenti meno rimborsi).
        Returns: il Riepilogo.
        """
        tabella = self._prenotazioni(giorni, adesso, dipendente_id)
        riepilogo = Riepilogo(
            prenotazioni=len(tabella),
            clienti_unici=tabella["cliente_id"].nunique(),
            valore_servizi_centesimi=int(tabella["totale_centesimi"].sum()),
            valore_medio_centesimi=int(tabella["totale_centesimi"].mean()) if len(tabella) else 0,
        )
        if dipendente_id is None:
            da, a = self._intervallo(giorni, adesso)
            movimenti = pd.DataFrame(self._repo.movimenti_completati(self._salone_id, da, a),
                                     columns=["tipo", "importo_centesimi", "creato_il"])
            segno = movimenti["tipo"].map(lambda tipo: -1 if tipo == "rimborso" else 1)
            riepilogo.incasso_netto_centesimi = int((movimenti["importo_centesimi"] * segno).sum())
        return riepilogo

    def per_professionista(self, giorni: int, adesso: datetime | None = None) -> pd.DataFrame:
        """
        Prenotazioni e valore dei servizi per professionista, dal più prenotato.
        Returns: DataFrame con dipendente_id, professionista, prenotazioni, valore_centesimi.
        """
        tabella = self._prenotazioni(giorni, adesso)
        return (tabella.groupby(["dipendente_id", "professionista"])
                .agg(prenotazioni=("id", "count"), valore_centesimi=("totale_centesimi", "sum"))
                .sort_values("prenotazioni", ascending=False)
                .reset_index())

    def per_ora_di_inizio(self, giorni: int, adesso: datetime | None = None) -> pd.Series:
        """
        Fasce di punta: prenotazioni per ora di inizio, nell'ora locale del salone.
        Returns: Series con l'ora come indice e il numero di prenotazioni come valore.
        """
        tabella = self._prenotazioni(giorni, adesso)
        return tabella["inizio"].dt.hour.value_counts().sort_index()

    def andamento(self, giorni: int, adesso: datetime | None = None, dipendente_id: int | None = None) -> pd.Series:
        """
        Andamento delle prenotazioni, per il salone o per un professionista: per giorno sulla settimana
        e sul mese, per settimana (dal lunedì) sull'anno.
        Returns: Series con il giorno, o il lunedì della settimana, come indice.
        """
        tabella = self._prenotazioni(giorni, adesso, dipendente_id)
        frequenza = "D" if giorni <= 31 else "W-SUN"
        periodi = tabella["inizio"].dt.tz_localize(None).dt.to_period(frequenza).dt.start_time
        return periodi.value_counts().sort_index()

    # --- Grafici ---

    def grafico_professionisti(self, giorni: int, adesso: datetime | None = None) -> bytes:
        """
        Barre orizzontali: prenotazioni confermate per professionista.
        Returns: l'immagine PNG.
        """
        dati = self.per_professionista(giorni, adesso).iloc[::-1]  # il più prenotato in alto
        return _barre(dati["professionista"].tolist(), dati["prenotazioni"].tolist(), orizzontale=True)

    def grafico_fasce(self, giorni: int, adesso: datetime | None = None) -> bytes:
        """
        Barre verticali: prenotazioni per ora di inizio.
        Returns: l'immagine PNG.
        """
        dati = self.per_ora_di_inizio(giorni, adesso)
        return _barre([f"{ora:02d}:00" for ora in dati.index], dati.tolist())

    def grafico_andamento(self, giorni: int, adesso: datetime | None = None, dipendente_id: int | None = None) -> bytes:
        """
        Barre verticali: prenotazioni per giorno o per settimana (vedi andamento).
        Returns: l'immagine PNG.
        """
        dati = self.andamento(giorni, adesso, dipendente_id)
        return _barre([inizio.strftime("%d/%m") for inizio in dati.index], dati.tolist())


def _barre(etichette: list[str], valori: list[int], orizzontale: bool = False) -> bytes:
    """
    Disegna un grafico a barre con i colori del tema e lo restituisce come PNG, senza salvarlo su disco.
    """
    figura, assi = plt.subplots(figsize=(8, 3.4), dpi=110)
    figura.patch.set_facecolor(CREMA)
    assi.set_facecolor(CREMA)
    if not valori:
        assi.text(0.5, 0.5, "Nessuna prenotazione nel periodo", ha="center", va="center",
                  color=TESTO_TENUE, fontsize=12, transform=assi.transAxes)
        assi.set_axis_off()
    else:
        if orizzontale:
            barre = assi.barh(etichette, valori, color=CORALLO, height=0.55)
            assi.xaxis.grid(True, color=BORDO, linewidth=0.8)
            assi.bar_label(barre, padding=4, color=TESTO, fontsize=10)
        else:
            assi.bar(etichette, valori, color=CORALLO, width=0.6)
            assi.yaxis.grid(True, color=BORDO, linewidth=0.8)
            if len(etichette) > 12:
                assi.tick_params(axis="x", labelrotation=45)
        assi.set_axisbelow(True)  # griglia dietro le barre
        for lato in ("top", "right", "left"):
            assi.spines[lato].set_visible(False)
        assi.spines["bottom"].set_color(BORDO)
        assi.tick_params(colors=TESTO_TENUE, labelsize=9, length=0)
    figura.tight_layout()
    memoria = BytesIO()
    figura.savefig(memoria, format="png", facecolor=CREMA)
    plt.close(figura)  # libera la memoria: sul server le figure non vanno mai lasciate aperte
    return memoria.getvalue()
