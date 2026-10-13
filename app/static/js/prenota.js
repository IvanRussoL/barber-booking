// Pagina di prenotazione: quando cambiano servizi, professionista o data,
// chiede al server gli orari liberi con fetch e li mostra come scelte.
const modulo = document.getElementById("modulo-prenotazione");
const contenitoreSlot = document.getElementById("slot");

async function aggiornaSlot() {
    const dati = new FormData(modulo);
    const servizi = dati.getAll("servizi");
    const dipendente = dati.get("dipendente_id");
    const data = dati.get("data");

    if (servizi.length === 0 || !dipendente || !data) {
        contenitoreSlot.textContent = "Scegli servizi, professionista e data per vedere gli orari liberi.";
        return;
    }

    const parametri = new URLSearchParams({ dipendente_id: dipendente, data: data });
    servizi.forEach((id) => parametri.append("servizi", id));
    contenitoreSlot.textContent = "Ricerca degli orari liberi...";

    const risposta = await fetch(modulo.dataset.urlSlot + "?" + parametri);
    const risultato = await risposta.json();
    contenitoreSlot.textContent = "";

    if (!risposta.ok) {
        contenitoreSlot.textContent = risultato.errore;
        return;
    }
    if (risultato.slot.length === 0) {
        contenitoreSlot.textContent = "Nessun orario libero in questa data.";
        return;
    }
    for (const ora of risultato.slot) {
        const etichetta = document.createElement("label");
        const scelta = document.createElement("input");
        scelta.type = "radio";
        scelta.name = "ora";
        scelta.value = ora;
        scelta.checked = ora === modulo.dataset.oraScelta;
        etichetta.append(scelta, " " + ora);
        contenitoreSlot.append(etichetta);
    }
}

modulo.addEventListener("change", (evento) => {
    if (evento.target.name === "ora" || evento.target.name === "modalita") {
        return;
    }
    modulo.dataset.oraScelta = "";
    aggiornaSlot();
});

aggiornaSlot();
