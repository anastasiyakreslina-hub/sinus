const text = "Sinus";
const element = document.getElementById("sinusText");

let index = 0;

function typeText() {
    if (element && index < text.length) {
        element.textContent += text[index];
        index++;
        setTimeout(typeText, 350);
    }
}

typeText();

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       REVEAL
    ===================================================== */
    const observer = new IntersectionObserver(
        (entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("active");
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.12,
            rootMargin: "0px 0px -50px 0px"
        }
    );

    document.querySelectorAll(".reveal").forEach(element => {
        observer.observe(element);
    });

    /* =====================================================
       3D CARD TILT
    ===================================================== */
    const cards = document.querySelectorAll(".featureCard");

    cards.forEach(card => {
        card.addEventListener("mousemove", event => {
            const rect = card.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = ((y - centerY) / centerY) * -2.5;
            const rotateY = ((x - centerX) / centerX) * 2.5;

            card.style.transform = `
                translateY(-10px)
                perspective(900px)
                rotateX(${rotateX}deg)
                rotateY(${rotateY}deg)
            `;
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform = "";
        });
    });

    /* =====================================================
       HERO PARALLAX
    ===================================================== */
    const mathElements = document.querySelectorAll(".bgMath, .mathCard");

    window.addEventListener("mousemove", event => {
        const x = (event.clientX / window.innerWidth) - 0.5;
        const y = (event.clientY / window.innerHeight) - 0.5;

        mathElements.forEach((element, index) => {
            const speed = (index + 1) * 5;
            element.style.translate = `${x * speed}px ${y * speed}px`;
        });
    });

    /* =====================================================
       CONTACTS
    ===================================================== */
    window.openContacts = function () {
        const modal = document.getElementById("contacts");
        if (!modal) return;

        modal.style.display = "grid";
        document.body.style.overflow = "hidden";
    };

    window.closeContacts = function () {
        const modal = document.getElementById("contacts");
        if (!modal) return;

        modal.style.display = "none";
        document.body.style.overflow = "";
    };

    /* закрытие по фону */
    const contacts = document.getElementById("contacts");

    if (contacts) {
        contacts.addEventListener("click", event => {
            if (event.target === contacts) {
                closeContacts();
            }
        });
    }

    /* =====================================================
       ESC
    ===================================================== */
    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeContacts();
        }
    });

    /* =====================================================
       SMOOTH ANCHORS
    ===================================================== */
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", event => {
            const id = link.getAttribute("href");
            if (!id || id === "#") return;

            const target = document.querySelector(id);
            if (target) {
                event.preventDefault();
                target.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

});