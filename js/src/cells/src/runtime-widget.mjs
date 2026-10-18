// Hidden anywidget at the top of each browser page: publishes the cell manifest
// to the page runtime and copies page.css into <head>. Renders nothing.

import { pageRuntime } from './runtime.mjs';

/** Copy the page stylesheet link from the shadow root into <head> (once). */
function installPageStyles(el) {
  const link = el.querySelector('link[rel="stylesheet"]') ?? el.getRootNode().querySelector('link[rel="stylesheet"]');
  if (!link || document.head.querySelector('link[data-nma-cells]')) return;
  const copy = document.createElement('link');
  copy.rel = 'stylesheet';
  copy.href = link.href;
  copy.dataset.nmaCells = '';
  document.head.appendChild(copy);
}

/**
 * A single floating "Run all" control per page. It runs every code cell top to
 * bottom on the page runtime. Idempotent (hydration can mount the widget twice)
 * and rebound to the current runtime on client-side navigation.
 */
function mountRunAll(rt) {
  const cells = rt.cells ?? [];
  if (cells.length === 0 || typeof document === 'undefined') return;

  let bar = document.getElementById('nma-run-all-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'nma-run-all-bar';
    bar.className = 'nma-run-all-bar';
    bar.innerHTML =
      '<button type="button" class="nma-run-all">\u25B6 Run all</button>' +
      '<span class="nma-run-all-status" role="status" aria-live="polite"></span>';
    document.body.appendChild(bar);
    const btn = bar.querySelector('.nma-run-all');
    const status = bar.querySelector('.nma-run-all-status');
    const setRunning = (v) => {
      bar._running = v;
      btn.disabled = v;
      btn.textContent = v ? '\u23F3 Running\u2026' : '\u25B6 Run all';
    };
    btn.addEventListener('click', async () => {
      if (bar._running) return;
      setRunning(true);
      status.textContent = '';
      try {
        const res = await bar._rt.runAll();
        status.textContent = res.error
          ? `\u2717 stopped at cell ${res.failedIndex + 1}`
          : '\u2713 ran all cells';
      } catch (e) {
        status.textContent = `\u2717 ${e?.message ?? e}`;
      } finally {
        setRunning(false);
      }
    });
  }

  // Rebind to the current runtime; drop any subscription to a previous one.
  bar._rt = rt;
  bar._off?.();
  const status = bar.querySelector('.nma-run-all-status');
  bar._off = rt.subscribe((e) => {
    if (!bar._running) return;
    if (e.kernel === 'starting') status.textContent = 'Starting\u2026';
    else if (typeof e.index === 'number' && e.state === 'running')
      status.textContent = `Running cell ${e.index + 1}\u2026`;
  });
}

export default {
  render({ model, el }) {
    installPageStyles(el);
    const rt = pageRuntime();
    rt.bundleUrl ||= import.meta.url;
    rt.setCells(model.get('cells'));
    mountRunAll(rt);
  },
};
