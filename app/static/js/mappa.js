// Mappa interattiva dei saloni con Leaflet e le mappe di OpenStreetMap.
// I dati (saloni ed eventuale zona del cliente) arrivano dal server in un blocco JSON nella pagina.
const contenitoreMappa = document.getElementById("mappa");
const datiMappa = document.getElementById("dati-mappa");

if (contenitoreMappa && datiMappa && window.L) {
    const dati = JSON.parse(datiMappa.textContent);
    // Lo zoom con la rotellina è spento: scorrendo la pagina non si ingrandisce la mappa per sbaglio.
    const mappa = L.map(contenitoreMappa, { scrollWheelZoom: false });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mappa);

    const limiti = L.latLngBounds([]);
    for (const salone of dati.saloni) {
        // Il riquadro si costruisce con textContent: i testi non vengono mai interpretati come HTML.
        const riquadro = document.createElement("div");
        const nome = document.createElement("strong");
        nome.textContent = salone.nome;
        const indirizzo = document.createElement("p");
        indirizzo.textContent = salone.indirizzo;
        riquadro.append(nome, indirizzo);
        if (salone.url) {
            const link = document.createElement("a");
            link.href = salone.url;
            link.textContent = "Vedi e prenota";
            riquadro.append(link);
        }
        L.circleMarker([salone.lat, salone.lon], {
            radius: 9, color: "#96391f", weight: 2, fillColor: "#b4472f", fillOpacity: 0.9,
        }).addTo(mappa).bindPopup(riquadro);
        limiti.extend([salone.lat, salone.lon]);
    }

    if (dati.tu) {
        L.circleMarker([dati.tu.lat, dati.tu.lon], {
            radius: 7, color: "#1e2a3a", weight: 2, fillColor: "#1e2a3a", fillOpacity: 0.8,
        }).addTo(mappa).bindTooltip("La tua zona");
        L.circle([dati.tu.lat, dati.tu.lon], {
            radius: dati.tu.raggio_km * 1000, color: "#b08d57", weight: 1, fillOpacity: 0.05,
            interactive: false,  // il cerchio non deve "rubare" i clic ai saloni che contiene
        }).addTo(mappa);
        // Il quadrato che contiene il cerchio del raggio scelto (lato = diametro, in metri).
        limiti.extend(L.latLng(dati.tu.lat, dati.tu.lon).toBounds(dati.tu.raggio_km * 2000));
    }

    if (limiti.isValid()) {
        mappa.fitBounds(limiti, { padding: [30, 30], maxZoom: 15 });
    } else {
        mappa.setView([42.5, 12.5], 5);  // Italia intera
    }
}
