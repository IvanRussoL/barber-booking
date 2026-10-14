// Ricerca dei saloni: posizione del browser per "Vicino a te" e menu delle province filtrato per regione.

const moduloVicino = document.getElementById("cerca-vicino");
if (moduloVicino) {
    const pulsante = moduloVicino.querySelector("[data-usa-posizione]");
    const stato = moduloVicino.querySelector("[data-stato-posizione]");
    pulsante.addEventListener("click", () => {
        if (!("geolocation" in navigator)) {
            stato.textContent = "Il browser non permette di condividere la posizione: cerca per regione e provincia.";
            return;
        }
        stato.textContent = "Ricerca della posizione...";
        navigator.geolocation.getCurrentPosition(
            (posizione) => {
                // 3 decimali (circa 100 metri) bastano per trovare i saloni vicini: la posizione esatta non lascia il browser.
                moduloVicino.elements.lat.value = posizione.coords.latitude.toFixed(3);
                moduloVicino.elements.lon.value = posizione.coords.longitude.toFixed(3);
                moduloVicino.submit();
            },
            () => {
                stato.textContent = "Posizione non disponibile o non concessa: cerca per regione e provincia.";
            },
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
