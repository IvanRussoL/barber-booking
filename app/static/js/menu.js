// Menu su telefono: il pulsante apre e chiude l'elenco dei link.
const pulsanteMenu = document.getElementById("apri-menu");
const menu = document.getElementById("menu");

pulsanteMenu.addEventListener("click", () => {
    const aperto = menu.classList.toggle("aperto");
    pulsanteMenu.setAttribute("aria-expanded", String(aperto));
});
