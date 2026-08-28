const text = "Sinus";
const element = document.getElementById("sinusText");

let index = 0;

function typeText() {
    if (index < text.length) {
        element.textContent += text[index];
        index++;
        setTimeout(typeText, 350);
    }
}

typeText();
