from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Limite ai tentativi sbagliati di login e di cambio password, per indirizzo IP. I conteggi stanno nella
# memoria del processo: basta con un solo server; con più processi servirebbe un archivio comune (es. Redis).
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

LIMITE_TENTATIVI = "5 per minute"


def tentativo_fallito(risposta) -> bool:
    """
    Conta solo i tentativi sbagliati (risposta 400): chi entra al primo colpo non consuma il limite.
    """
    return risposta.status_code == 400
