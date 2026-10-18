// anywidget panel for one visible code cell: CodeMirror editor + toolbar in the
// shadow root, output in light DOM (slotted) so the page's thebe/ipywidgets CSS applies.

import { createEditor } from './editor.mjs';
import { pageRuntime } from './runtime.mjs';
import { statusText } from './model.mjs';

const LABEL = { edit: 'Python', collapsed: 'Python · code hidden', output: 'Output' };

export default {
  render({ model, el }) {
    const index = model.get('index');
    const mode = model.get('mode');
    const exercise = model.get('exercise');
    const original = model.get('code');
    const rt = pageRuntime();
    rt.bundleUrl ||= import.meta.url;
    const root = el.getRootNode();
    const host = root.host;

    // Append, don't replace: el also holds the <link> that loads cells.css.
    const wrap = document.createElement('div');
    wrap.innerHTML = `
      <div class="cell${exercise ? ' is-exercise' : ''}" data-mode="${mode}">
        <div class="head"><span class="label">${exercise ? 'Exercise · fill in, then run' : LABEL[mode]}</span></div>
        <div class="editor"${mode === 'collapsed' ? ' hidden' : ''}></div>
        <div class="actions">
          <button class="run" type="button" aria-label="Run cell">▶ Run</button>
          ${mode !== 'output' ? '<button class="reset" type="button">Reset</button>' : ''}
          ${mode === 'collapsed' ? '<button class="toggle" type="button" aria-expanded="false">Show code</button>' : ''}
          <button class="restart" type="button" hidden>Restart</button>
          <span class="status" role="status" aria-live="polite"></span>
        </div>
        <div class="output"><slot name="out"></slot></div>
      </div>`;
    el.appendChild(wrap.firstElementChild);

    // Keep data-theme in sync with the site's light/dark switch (no :host-context in Firefox).
    const syncTheme = () =>
      host.setAttribute('data-theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    syncTheme();
    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    // Output lives in light DOM. Idempotent: hydration can mount a panel twice.
    host.querySelectorAll(':scope > .nma-cell-out').forEach((n) => n.remove());
    const out = document.createElement('div');
    out.slot = 'out';
    out.className = 'nma-cell-out';
    host.appendChild(out);
    if (!rt.ready && mode === 'output') out.innerHTML = '<p class="nma-hint">Run to see output</p>';
    const unregister = rt.register(index, out);

    const status = el.querySelector('.status');
    const restartButton = el.querySelector('.restart');
    restartButton.hidden = !rt.ready;
    let pending = false;

    const editor =
      mode === 'output'
        ? null
        : createEditor({
            parent: el.querySelector('.editor'),
            root,
            doc: rt.edits[index] ?? original,
            onChange: (text) => {
              if (text === original) delete rt.edits[index];
              else rt.edits[index] = text;
              if (rt.ran.has(index)) out.classList.add('is-stale');
            },
            onRun: () => run(),
          });

    async function run() {
      out.classList.remove('is-stale');
      pending = true;
      try {
        const res = await rt.run(index, editor ? editor.text() : original);
        // An earlier cell failed first: its own panel shows the error.
        if (res.failedIndex !== null && res.failedIndex !== index) status.textContent = '';
      } catch (err) {
        status.textContent = `✗ ${err?.message ?? err}`;
      } finally {
        pending = false;
      }
    }

    const off = rt.subscribe((e) => {
      if (e.kernel === 'starting') {
        if (pending) status.textContent = statusText(e);
      } else if (e.kernel === 'ready') {
        restartButton.hidden = false;
        if (e.restarted) {
          status.textContent = '';
          out.classList.remove('is-stale');
        }
      } else if (e.index === index) {
        status.textContent = statusText(e);
      }
    });

    el.querySelector('.run').addEventListener('click', run);
    restartButton.addEventListener('click', () => rt.restart());
    el.querySelector('.reset')?.addEventListener('click', () => {
      editor.setText(original);
      delete rt.edits[index];
      out.classList.remove('is-stale');
    });
    el.querySelector('.toggle')?.addEventListener('click', (ev) => {
      const ed = el.querySelector('.editor');
      ed.hidden = !ed.hidden;
      ev.target.textContent = ed.hidden ? 'Show code' : 'Hide code';
      ev.target.setAttribute('aria-expanded', String(!ed.hidden));
    });

    return () => {
      off();
      observer.disconnect();
      unregister();
      editor?.destroy();
      out.remove();
      el.querySelector('.cell')?.remove();
    };
  },
};
