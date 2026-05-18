/* ═══════════════════════════════════════════════════════════════════
   animations.js — shared interactive animation controller
   Import on every page: <script type="module" src="js/animations.js"></script>
═══════════════════════════════════════════════════════════════════ */

/* ── Scroll-reveal (IntersectionObserver) ─────────────────────────── */
function initScrollReveal() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        // Stagger children if parent has class
        if (e.target.classList.contains('stagger-children')) {
          e.target.classList.add('in');
        }
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('[data-fade], .stagger-children').forEach(el => io.observe(el));
}

/* ── Tilt cards on mouse move ─────────────────────────────────────── */
function initTiltCards() {
  document.querySelectorAll('.tilt-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width  - 0.5;
      const y = (e.clientY - r.top)  / r.height - 0.5;
      card.style.transform = `perspective(600px) rotateY(${x * 8}deg) rotateX(${-y * 6}deg) translateZ(6px)`;
      card.style.boxShadow = `${-x * 16}px ${-y * 16}px 40px rgba(0,0,0,0.35)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
      card.style.boxShadow = '';
    });
  });
}

/* ── Ripple effect on buttons ─────────────────────────────────────── */
function initRipple() {
  document.querySelectorAll('.btn-primary, .btn-outline').forEach(btn => {
    btn.classList.add('ripple-host');
    btn.addEventListener('click', e => {
      const r = btn.getBoundingClientRect();
      const size = Math.max(r.width, r.height) * 1.8;
      const dot = document.createElement('span');
      dot.className = 'ripple';
      dot.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-r.left-size/2}px;top:${e.clientY-r.top-size/2}px`;
      btn.appendChild(dot);
      dot.addEventListener('animationend', () => dot.remove());
    });
  });
}

/* ── Count-up numbers ─────────────────────────────────────────────── */
function countUp(el, target, duration = 1400) {
  const start = performance.now();
  const isFloat = target % 1 !== 0;
  const step = ts => {
    const elapsed = ts - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = eased * target;
    el.textContent = isFloat ? current.toFixed(1) : Math.floor(current).toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = isFloat ? target.toFixed(1) : target.toLocaleString();
  };
  requestAnimationFrame(step);
}

function initCounters() {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && !e.target.dataset.counted) {
        e.target.dataset.counted = '1';
        countUp(e.target, parseFloat(e.target.dataset.count), 1200);
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('[data-count]').forEach(el => io.observe(el));
}

/* ── Typewriter effect ────────────────────────────────────────────── */
export function typewriter(el, texts, speed = 60, pause = 2000) {
  let ti = 0, ci = 0, deleting = false;
  function tick() {
    const text = texts[ti];
    if (deleting) {
      el.textContent = text.slice(0, --ci);
      if (ci === 0) { deleting = false; ti = (ti + 1) % texts.length; setTimeout(tick, 400); return; }
    } else {
      el.textContent = text.slice(0, ++ci);
      if (ci === text.length) { setTimeout(() => { deleting = true; tick(); }, pause); return; }
    }
    setTimeout(tick, deleting ? speed / 2 : speed);
  }
  tick();
}

/* ── Smooth nav transitions ───────────────────────────────────────── */
function initNavTransitions() {
  document.querySelectorAll('a[href]').forEach(a => {
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto')) return;
    a.addEventListener('click', e => {
      e.preventDefault();
      document.body.classList.add('page-out');
      setTimeout(() => { window.location.href = href; }, 220);
    });
  });
}

/* ── Smooth scroll for anchor links ──────────────────────────────── */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });
}

/* ── Navbar hide/show on scroll ───────────────────────────────────── */
function initNavScroll() {
  const nav = document.querySelector('.landing-nav, .navbar');
  if (!nav) return;
  let lastY = 0;
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    if (y > 80 && y > lastY) nav.style.transform = 'translateY(-100%)';
    else nav.style.transform = '';
    nav.style.transition = 'transform 0.3s var(--ease)';
    lastY = y;
  }, { passive: true });
}

/* ── Progress bar on page scroll ─────────────────────────────────── */
function initScrollProgress() {
  const bar = document.getElementById('scroll-progress');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const pct = window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100;
    bar.style.width = pct + '%';
  }, { passive: true });
}

/* ── Parallax hero elements ───────────────────────────────────────── */
function initParallax() {
  const els = document.querySelectorAll('[data-parallax]');
  if (!els.length) return;
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    els.forEach(el => {
      const speed = parseFloat(el.dataset.parallax) || 0.3;
      el.style.transform = `translateY(${y * speed}px)`;
    });
  }, { passive: true });
}

/* ── Boot ─────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
  initTiltCards();
  initRipple();
  initCounters();
  initNavTransitions();
  initSmoothScroll();
  initNavScroll();
  initScrollProgress();
  initParallax();
});