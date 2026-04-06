// nav.js — Navbar compartida inyectada en todas las páginas
(function () {
    const NAV_HTML = `
<header class="navbar">
  <div class="container">
    <a class="logo" href="/dashboard" style="text-decoration:none;display:flex;align-items:center;gap:8px;">
      <span class="logo-icon">🔍</span>
      <span class="logo-text">CorupCol</span>
    </a>
    <button class="nav-hamburger" id="nav-hamburger" aria-label="Abrir menú" aria-expanded="false" aria-controls="nav-links">
      <span></span><span></span><span></span>
    </button>
    <nav class="nav-links" id="nav-links">
      <a href="/dashboard">Inicio</a>
      <a href="/dashboard/hallazgos.html">📰 Hallazgos</a>
      <a href="/dashboard/red.html">Red Vínculos</a>
      <a href="/dashboard/carruseles.html">Carruseles</a>
      <a href="/dashboard/nepotismo.html">Nepotismo</a>
      <a href="/dashboard/sobrecostos.html">Sobrecostos</a>
      <a href="/dashboard/contexto.html">Contexto Político</a>
      <a href="/dashboard/busqueda.html" class="btn-buscar">Buscar 🔎</a>
    </nav>
  </div>
</header>`;

    document.body.insertAdjacentHTML('afterbegin', NAV_HTML);

    // Marcar enlace activo según pathname
    const normalizePath = (path) => {
        const clean = path.replace(/\/$/, '');
        if (clean === '/dashboard/index.html') return '/dashboard';
        return clean || '/dashboard';
    };
    const current = normalizePath(window.location.pathname);
    document.querySelectorAll('#nav-links a').forEach(a => {
        const href = normalizePath(a.getAttribute('href'));
        if (href === current) {
            a.classList.add('nav-active');
        }
    });

    // Hamburguesa
    const hamburger = document.getElementById('nav-hamburger');
    const navLinks  = document.getElementById('nav-links');
    if (!hamburger || !navLinks) return;
    hamburger.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', String(isOpen));
        hamburger.setAttribute('aria-label', isOpen ? 'Cerrar menú' : 'Abrir menú');
    });
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('open');
            hamburger.setAttribute('aria-expanded', 'false');
        });
    });
})();
