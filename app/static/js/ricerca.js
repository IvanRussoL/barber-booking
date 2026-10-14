// Ricerca dei saloni: pulsante "Usa la mia posizione" e menu delle province filtrato per regione.

// Il pulsante sta nella home e nella ricerca per zona; gli indirizzi arrivano dal server negli attributi data-.
// Con la posizione si va ai saloni vicini; senza (permesso negato, errore, browser che non la supporta)
// alla ricerca per regione e provincia, con un avviso.
for (const pulsante of document.querySelectorAll("[data-usa-posizione]")) {
    const stato = pulsante.parentElement.querySelector("[data-stato-posizione]");
    const vaiAllaZona = () => {
        window.location.href = pulsante.dataset.urlZona;
    };
    pulsante.addEventListener("click", () => {
        if (!("geolocation" in navigator)) {
            vaiAllaZona();
            return;
        }
        stato.textContent = "Ricerca della posizione...";
        navigator.geolocation.getCurrentPosition(
            (posizione) => {
                // 3 decimali (circa 100 metri) bastano per trovare i saloni vicini: la posizione esatta non lascia il browser.
                const indirizzo = new URL(pulsante.dataset.urlVicino, window.location.href);
                indirizzo.searchParams.set("lat", posizione.coords.latitude.toFixed(3));
                indirizzo.searchParams.set("lon", posizione.coords.longitude.toFixed(3));
                window.location.href = indirizzo.href;
            },
            vaiAllaZona,
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
        );
    });
}

const sceltaRegione = document.getElementById("regione");
const sceltaProvincia = document.getElementById("provincia");
if (sceltaRegione && sceltaProvincia) {
    // Mostra solo le province della regione scelta. Senza JavaScript restano tutte, raggruppate per regione,
    // e il server controlla comunque che la provincia sia della regione indicata.
    function filtraProvince() {
        for (const gruppo of sceltaProvincia.querySelectorAll("optgroup")) {
            const visibile = gruppo.label === sceltaRegione.value;
            gruppo.hidden = !visibile;
            gruppo.disabled = !visibile;
        }
        const scelta = sceltaProvincia.selectedOptions[0];
        if (scelta && scelta.parentElement.disabled) {
            sceltaProvincia.value = "";
        }
    }
    sceltaRegione.addEventListener("change", filtraProvince);
    filtraProvince();
}
