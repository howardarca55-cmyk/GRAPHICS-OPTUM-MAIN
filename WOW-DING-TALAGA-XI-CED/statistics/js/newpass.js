const form          = document.querySelector('form');
const newPwInput    = document.querySelector('#new_password');
const confirmInput  = document.querySelector('#confirm_password');
const confirmBtn    = document.querySelector('.btn');
const wrapper       = document.querySelector('.wrapper');
const strengthFill  = document.querySelector('.strength-bar-fill');
const strengthLabel = document.querySelector('.strength-label');

/* ── Password strength checker ── */
newPwInput.addEventListener('input', function () {
    const val = this.value;
    let strength = 0;

    if (val.length >= 6)                        strength++;
    if (val.length >= 10)                       strength++;
    if (/[A-Z]/.test(val) && /[a-z]/.test(val)) strength++;
    if (/[0-9]/.test(val))                      strength++;
    if (/[^a-zA-Z0-9]/.test(val))              strength++;

    const levels = [
        { width: '0%',   color: 'transparent',              label: '' },
        { width: '25%',  color: 'crimson',                  label: 'Weak' },
        { width: '50%',  color: '#e8832a',                  label: 'Fair' },
        { width: '75%',  color: '#f0c040',                  label: 'Good' },
        { width: '100%', color: '#28c76f',                  label: 'Strong' },
    ];

    const level = Math.min(strength, 4);
    strengthFill.style.width      = levels[level].width;
    strengthFill.style.background = levels[level].color;
    strengthLabel.textContent     = levels[level].label;
    strengthLabel.style.color     = levels[level].color || 'rgba(255,255,255,0.4)';
});

/* ── Toggle password visibility ── */
function togglePw(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon  = btn.querySelector('i');
    if (input.type === 'password') {
        input.type      = 'text';
        icon.className  = 'fas fa-eye-slash';
    } else {
        input.type      = 'password';
        icon.className  = 'fas fa-eye';
    }
}

/* ── Submit validation ── */
form.addEventListener('submit', function (e) {
    const newPw     = newPwInput.value.trim();
    const confirmPw = confirmInput.value.trim();

    if (!newPw || !confirmPw) {
        e.preventDefault();
        shakeWrapper();
        return;
    }

    if (newPw.length < 6) {
        e.preventDefault();
        shakeWrapper();
        showInlineError(newPwInput, 'Password must be at least 6 characters.');
        return;
    }

    if (newPw !== confirmPw) {
        e.preventDefault();
        shakeWrapper();
        showInlineError(confirmInput, 'Passwords do not match.');
        return;
    }

    /* Loading state */
    confirmBtn.textContent        = 'Updating...';
    confirmBtn.style.pointerEvents = 'none';
    confirmBtn.style.opacity       = '0.7';
});

/* ── Shake animation ── */
function shakeWrapper() {
    wrapper.classList.add('shake');
    wrapper.addEventListener('animationend', function () {
        wrapper.classList.remove('shake');
    }, { once: true });
}

/* ── Inline error under input ── */
function showInlineError(input, message) {
    /* Remove any existing error for this input */
    const existing = input.parentElement.querySelector('.inline-error');
    if (existing) existing.remove();

    const err = document.createElement('p');
    err.className   = 'inline-error';
    err.textContent = message;
    err.style.cssText = `
        font-size: 1.15rem;
        color: crimson;
        margin-top: .5rem;
        padding-left: .4rem;
        animation: fadeIn .2s ease;
    `;
    input.parentElement.appendChild(err);

    /* Auto-remove on next input event */
    input.addEventListener('input', () => err.remove(), { once: true });
}