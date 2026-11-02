// Auto-hide flash messages after a few seconds.
document.querySelectorAll('.gh-toast').forEach((toast, i) => {
  setTimeout(() => {
    toast.style.transition = 'opacity .4s, transform .4s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    setTimeout(() => toast.remove(), 400);
  }, 5000 + i * 600);
});

// Ask before destructive actions: <form data-confirm="Are you sure?">
document.addEventListener('submit', (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

// Live preview for image file inputs: <input data-preview="#imgId">
document.querySelectorAll('input[type=file][data-preview]').forEach((input) => {
  input.addEventListener('change', () => {
    const target = document.querySelector(input.dataset.preview);
    if (!target || !input.files.length) return;
    target.innerHTML = '';
    Array.from(input.files).slice(0, 10).forEach((file) => {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.className = 'rounded-3 me-2 mb-2';
      img.style.cssText = 'width:96px;height:72px;object-fit:cover';
      target.appendChild(img);
    });
  });
});

// ----- Mockup popups (sh-modal) -----
function openModal(id) { const el = document.getElementById(id); if (!el) return false; el.classList.add('show'); return true; }
function closeModal(id) { document.getElementById(id)?.classList.remove('show'); }
function switchModal(from, to) { closeModal(from); openModal(to); }
document.addEventListener('click', (e) => {
  if (e.target.classList?.contains('sh-backdrop')) e.target.classList.remove('show');
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') document.querySelectorAll('.sh-backdrop.show').forEach((m) => m.classList.remove('show'));
});

// Contact popup: show the landowner's number with a Copy button
function openContact(title, phone) {
  const box = document.getElementById('contactModal');
  if (!box) return;
  box.querySelector('[data-contact-title]').textContent = title;
  box.querySelector('[data-contact-number]').textContent = phone || 'No phone number added';
  openModal('contactModal');
}

function copyContactNumber(btn) {
  const number = btn.parentElement.querySelector('[data-contact-number]').textContent.trim();
  const done = () => { btn.textContent = '✓ Copied'; setTimeout(() => { btn.textContent = '📋 Copy'; }, 1800); };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(number).then(done);
  } else {
    // Fallback for plain http (e.g. 127.0.0.1 in some browsers)
    const tmp = document.createElement('textarea');
    tmp.value = number; document.body.appendChild(tmp); tmp.select();
    document.execCommand('copy'); tmp.remove(); done();
  }
}

// Details page gallery thumbnails
function switchGalleryPhoto(btn) {
  const main = document.querySelector('#galleryMain img');
  if (main) main.src = btn.dataset.src;
  document.querySelectorAll('#galleryThumbs .thumb').forEach((t) => t.classList.toggle('active', t === btn));
}

// Show / hide a password field
function togglePassword(btn) {
  const input = btn.parentElement.querySelector('input');
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  btn.textContent = show ? '🙈' : '👁';
  btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
}

// Guests: explain that an action needs an account, then offer Log In / Sign Up.
// Returns true when the popup opened, so links can use: onclick="return !needLogin('...')"
function needLogin(reason) {
  const box = document.getElementById('loginRequiredModal');
  if (!box) return false;
  box.querySelector('[data-login-reason]').textContent = reason || 'Please log in first, then you can see this.';
  box.classList.add('show');
  return true;
}
