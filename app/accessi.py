from flask import abort, g, redirect, url_for


def controlla_accesso(*ruoli_ammessi: str):
    """
    Controllo comune dei Blueprint riservati, da chiamare nel loro before_request.
    Args: ruoli_ammessi, i ruoli che possono aprire le rotte del Blueprint.
    Returns: il redirect al login se l'utente è anonimo, None se l'accesso è consentito.
    Raises: Forbidden (abort 403) se l'utente ha un ruolo non ammesso.
    """
    if g.utente is None:
        return redirect(url_for("auth.login"))
    if g.utente.ruolo not in ruoli_ammessi:
        abort(403)
    return None
