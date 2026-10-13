// Carosello della home: passa alla slide successiva ogni 5 secondi (quanto dura il video); i trattini in basso scelgono la slide.
// Si ferma con il mouse sopra e non parte da solo se il sistema chiede di ridurre le animazioni.
const carosello = document.querySelector(".carosello");

if (carosello) {
    const binario = carosello.querySelector(".carosello-binario");
    const slide = carosello.querySelectorAll(".slide");
    const punti = carosello.querySelectorAll(".carosello-punti button");
    const video = carosello.querySelectorAll("video");
    const menoMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let attuale = 0;
    let timer = null;

    function mostra(indice) {
        // Il resto della divisione fa ripartire dalla prima slide dopo l'ultima.
        attuale = indice % slide.length;
        binario.style.transform = `translateX(-${attuale * 100}%)`;
        // Le slide nascoste sono "inerti": il tasto Tab e i lettori di schermo le saltano.
        slide.forEach((elemento, i) => {
            elemento.inert = i !== attuale;
        });
        punti.forEach((punto, i) => {
            punto.setAttribute("aria-current", String(i === attuale));
        });
        // Il video riparte da zero quando la sua slide torna visibile e si ferma quando esce.
        video.forEach((filmato) => {
            if (filmato.closest(".slide") === slide[attuale] && !menoMovimento) {
                filmato.currentTime = 0;
                filmato.play();
            } else {
                filmato.pause();
            }
        });
    }

    function ferma() {
        clearInterval(timer);
    }

    function avvia() {
        ferma();  // mai due timer insieme
        if (!menoMovimento) {
            timer = setInterval(() => mostra(attuale + 1), 5000);
        }
    }

    punti.forEach((punto, i) => {
        punto.addEventListener("click", () => {
            mostra(i);
            avvia();
        });
    });

    carosello.addEventListener("mouseenter", ferma);
    carosello.addEventListener("mouseleave", avvia);

    if (menoMovimento) {
        video.forEach((filmato) => filmato.pause());
    }

    avvia();
}
