// Scrollytelling engine (one per scrolly page, emitted by scrolly.mjs).
//
// - Copies the page layout stylesheet (scrolly.css, attached to this widget
//   so MyST bundles it) from the widget's shadow root into the document.
// - Tracks which step card is on screen and shows the matching stage view.
// - Draws the progress bar, section label and the "Enable Python" pill.
// - Plays muted videos in the active view and pauses the others.
// - Publishes the page's code cells on window.NMA_SCROLLY for runnable.mjs.
//
// Without JavaScript the page is a plain linear document.

const STYLE = `
.hud { position: absolute; top: 0; left: 0; right: 0; display: flex; align-items: center; gap: 16px; padding: 14px 28px; pointer-events: none; font-family: var(--nm-font-head, system-ui, sans-serif); }
.sec { font-weight: 600; font-size: 0.78rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--nm-mint, #5efbd7); min-width: 12ch; }
.bar { flex: 1; height: 3px; background: rgba(255,255,255,0.14); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; width: 0; background: linear-gradient(90deg, var(--nm-salmon, #fb7a7a), var(--nm-mint, #5efbd7)); transition: width 0.4s; }
.py[hidden] { display: none; }
.py { pointer-events: auto; flex: none; font: 600 0.74rem var(--nm-font-head, system-ui, sans-serif); letter-spacing: 0.04em; border: 1px solid var(--nm-mint, #5efbd7); border-radius: 999px; padding: 0.3rem 0.85rem; cursor: pointer; max-width: 34ch; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; background: var(--nm-mint, #5efbd7); color: var(--nm-indigo, #2a2952); }
.py[data-state="loading"] { background: transparent; color: var(--nm-mint, #5efbd7); cursor: progress; }
.py[data-state="ready"] { background: transparent; color: var(--nm-mint, #5efbd7); cursor: default; }
.py[data-state="error"] { background: var(--nm-salmon, #fb7a7a); border-color: var(--nm-salmon, #fb7a7a); }
`;

// Section width (px) from which the stage sits beside the cards.
// Keep in sync with the @container breakpoint in scrolly.css.
const WIDE = 760;

const PY_LABELS = { idle: 'Enable Python ▸', ready: 'Python ready', error: 'Python failed. Retry' };

/** Copy the layout stylesheet link from the shadow root into <head> (once). */
function installPageStyles(el) {
  const link = el.querySelector('link[rel="stylesheet"]');
  if (!link || document.head.querySelector('link[data-nma-scrolly]')) return;
  const copy = document.createElement('link');
  copy.rel = 'stylesheet';
  copy.href = link.href;
  copy.dataset.nmaScrolly = '';
  document.head.appendChild(copy);
}

function render({ model, el }) {
  installPageStyles(el);
  const host = el.getRootNode().host;
  const container = host && host.closest('.scrolly');
  if (!container) {
    el.textContent = 'scrolly engine: no enclosing .scrolly section';
    return;
  }
  window.NMA_SCROLLY = {
    ...(window.NMA_SCROLLY || {}),
    cells: model.get('cells') || [],
    pyodideUrl: model.get('pyodideUrl'),
    edits: (window.NMA_SCROLLY && window.NMA_SCROLLY.edits) || {},
  };

  const map = model.get('map') || [];
  const hero = model.get('hero') || [];
  const sections = model.get('sections') || [];
  const steps = [...container.querySelectorAll(':scope > .scrolly-steps > .scrolly-step')];
  const views = [...container.querySelectorAll(':scope > .scrolly-stage > .scrolly-view')];

  const style = document.createElement('style');
  style.textContent = STYLE;
  const hud = document.createElement('div');
  hud.className = 'hud';
  hud.innerHTML = '<span class="sec"></span><div class="bar"><i></i></div><button type="button" class="py"></button>';
  el.append(style, hud);
  const secEl = hud.querySelector('.sec');
  const barEl = hud.querySelector('.bar i');
  const pyBtn = hud.querySelector('.py');

  let active = -1;
  function activate(i) {
    if (i === active || i < 0) return;
    active = i;
    steps.forEach((s, k) => s.classList.toggle('is-active', k === i));
    const v = map[i] ?? -1;
    views.forEach((x, k) => {
      const on = k === v;
      x.classList.toggle('is-active', on);
      x.querySelectorAll('video').forEach((video) => {
        if (!on) video.pause();
        else if (video.muted || video.autoplay) video.play().catch(() => {});
      });
    });
    container.classList.toggle('is-hero-active', !!hero[i]);
    secEl.textContent = sections[i] || '';
    barEl.style.width = `${((i + 1) / steps.length) * 100}%`;
  }

  let io;
  let lastKey = '';
  function observe() {
    const H = window.innerHeight;
    const wide = container.clientWidth >= WIDE;
    const key = `${H}|${wide}`;
    if (io && key === lastKey) return;
    lastKey = key;
    if (io) io.disconnect();
    const top = parseFloat(getComputedStyle(container).getPropertyValue('--scrolly-top')) || 0;
    const line = wide ? Math.round(H * 0.5) : Math.round(top + 0.55 * H + 48);
    io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && activate(steps.indexOf(e.target.closest('.scrolly-step')))),
      { rootMargin: `-${line}px 0px -${Math.max(0, H - line - 1)}px 0px`, threshold: 0 },
    );
    steps.forEach((s) => io.observe(s.querySelector('.scrolly-card') || s));
  }
  window.addEventListener('resize', observe);
  const ro = new ResizeObserver(observe); // the section's width changes with the menus, not just the window
  ro.observe(container);

  const showPy = (state, msg) => {
    pyBtn.hidden = false;
    pyBtn.dataset.state = state;
    pyBtn.textContent = state === 'loading' ? msg : PY_LABELS[state] || PY_LABELS.idle;
    pyBtn.title = state === 'error' ? msg : 'Runs Python in your browser (Pyodide). Downloaded once, then cached.';
  };
  const onPy = (e) => showPy(e.detail.state, e.detail.msg);
  window.addEventListener('nma-py', onPy);
  pyBtn.hidden = true; // shown once runnable.mjs creates the runtime
  if (window.NMA_PY) showPy(window.NMA_PY.state, window.NMA_PY.msg);
  pyBtn.addEventListener('click', async () => {
    const py = window.NMA_PY;
    if (py && (py.state === 'idle' || py.state === 'error')) py.ensure().catch(() => {});
  });

  activate(0);
  observe();
  container.dataset.ready = 'true';
  container._activate = activate; // test hook

  return () => {
    if (io) io.disconnect();
    window.removeEventListener('resize', observe);
    ro.disconnect();
    window.removeEventListener('nma-py', onPy);
  };
}

export default { render };
