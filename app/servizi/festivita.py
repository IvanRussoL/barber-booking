from datetime import date, timedelta

# Giorno e mese delle giornate a rischio fisse: festività nazionali italiane più le vigilie di Natale
# e Capodanno, in cui molti saloni cambiano orario.
GIORNATE_FISSE = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8),
                  (12, 24), (12, 25), (12, 26), (12, 31)]


def pasqua(anno: int) -> date:
    """
    Domenica di Pasqua nel calendario gregoriano (algoritmo di Meeus/Jones/Butcher).
    """
    a = anno % 19
    b, c = divmod(anno, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese, giorno = divmod(h + l - 7 * m + 114, 31)
    return date(anno, mese, giorno + 1)


def giornate_a_rischio(anno: int) -> set[date]:
    """
    Date dell'anno in cui l'apertura del salone è incerta: festività italiane, Pasqua e Pasquetta, vigilie.
    """
    domenica_di_pasqua = pasqua(anno)
    return {date(anno, mese, giorno) for mese, giorno in GIORNATE_FISSE} | {
        domenica_di_pasqua, domenica_di_pasqua + timedelta(days=1)
    }
