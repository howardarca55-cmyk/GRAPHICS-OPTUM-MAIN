const form             = document.querySelector('form');
const codeInput        = document.querySelector('#verification_code');
const verifyBtn        = document.querySelector('.btn');
const wrapper          = document.querySelector('.wrapper');

/* ── Auto-uppercase & strip non-alphanumeric characters ── */
codeInput.addEventListener('input', function () {
    this.value = this.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
});

/* ── Add loading state on submit ── */
form.addEventListener('submit', function (e) {
    const code = codeInput.value.trim();

    if (code.length === 0) {
        e.preventDefault();
        shakeInput();
        return;
    }

    verifyBtn.textContent = 'Verifying...';
    verifyBtn.style.pointerEvents = 'none';
    verifyBtn.style.opacity = '0.7';
});

/* ── Shake animation on empty submit ── */
function shakeInput() {
    wrapper.classList.add('shake');
    wrapper.addEventListener('animationend', function () {
        wrapper.classList.remove('shake');
    }, { once: true });
}