// Runnable Python panel for scrolly pages (emitted by scrolly.mjs for each
// visible code cell). One Pyodide runtime per page, shared on window.NMA_PY,
// started by the first Run (or the "Enable Python" pill in engine.mjs).
//
// Notebook semantics: running cell k first runs every earlier cell that
// hasn't run yet, in order, in one namespace (cells come from engine.mjs via
// window.NMA_SCROLLY). An earlier exercise that still has an uncommented
// `raise NotImplementedError` runs its {nma-solution} code instead, so the
// cells after it work. Same "hidden, not secret" rule as the notebooks.
//
// Model: {code, mode: edit|collapsed|output, params, index, exercise,
//         fallback, initial: {stdout, images, error} | null}

const DEFAULT_PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
const UNFINISHED_RE = /^[ \t]*raise NotImplementedError/m;
const FALLBACK_NOTE = 'An earlier exercise is not finished yet, so its reference solution ran.';

// ---------------------------------------------------------------- pure helpers (unit-tested)

export const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Minimal Python syntax highlighting as HTML. */
export function highlight(code) {
  const re =
    /(#.*$)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|(\b(?:def|return|import|for|in|as|from|if|else|elif|while|with|lambda|not|and|or|None|True|False|class|try|except|finally|raise|yield|pass|break|continue|global|is|async|await)\b)|(\.\.\.)|(\b\d+(?:\.\d+)?(?:e[-+]?\d+)?\b)|(\b[A-Za-z_]\w*(?=\())/gm;
  let out = '';
  let last = 0;
  for (const m of code.matchAll(re)) {
    out += esc(code.slice(last, m.index));
    const [all, c, s, k, b, n] = m;
    const cls = c ? 'c' : s ? 's' : k ? 'k' : b ? 'b' : n ? 'n' : 'f';
    out += `<i class="tk-${cls}">${esc(all)}</i>`;
    last = m.index + all.length;
  }
  return out + esc(code.slice(last));
}

/** A JS value as a Python literal. */
export function pyLiteral(v) {
  if (v === true) return 'True';
  if (v === false) return 'False';
  if (v === null || v === undefined) return 'None';
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : 'float("nan")';
  return JSON.stringify(String(v));
}

/**
 * Rewrite the `name = ...  # @param ...` lines of `code` with the current
 * control values, keeping the comment. Other lines are untouched.
 */
export function applyParams(code, values) {
  return code
    .split('\n')
    .map((line) => {
      const m = line.match(/^([A-Za-z_]\w*)(\s*=\s*)(.+?)(\s*#\s*@param\b.*)$/);
      if (!m || !(m[1] in values)) return line;
      return `${m[1]}${m[2]}${pyLiteral(values[m[1]])}${m[4]}`;
    })
    .join('\n');
}

/** The code to run for an earlier cell: the reader's edit, or the solution if unfinished. */
export function codeForEarlierCell(cell, edits) {
  const code = edits[cell.index] ?? cell.code;
  if (UNFINISHED_RE.test(code) && cell.fallback) return { code: cell.fallback, fallback: true };
  return { code, fallback: false };
}

/** Value shown for a slider (avoid 0.30000000000000004). */
export function formatValue(v) {
  return typeof v === 'number' ? String(Number(v.toPrecision(10))) : String(v);
}

// ---------------------------------------------------------------- shared runtime

const PY_SETUP = `
import os, sys
os.environ["MPLBACKEND"] = "AGG"

async def _nma_exec(src):
    from pyodide.code import eval_code_async
    result = await eval_code_async(src, globals(), return_mode="last_expr")
    if result is not None:
        print(repr(result))

def _nma_figures():
    if "matplotlib.pyplot" not in sys.modules:
        return []
    import base64, io, warnings
    import matplotlib.pyplot as plt
    out = []
    for n in plt.get_fignums():
        buf = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plt.figure(n).savefig(buf, format="png", bbox_inches="tight")
        out.append(base64.b64encode(buf.getvalue()).decode())
    plt.close("all")
    return out
`;

function createRuntime() {
  return {
    state: 'idle', // idle | loading | ready | error
    msg: '',
    py: null,
    promise: null,
    done: new Set(), // indexes of cells that ran successfully
    queue: Promise.resolve(),
    set(state, msg = '') {
      this.state = state;
      this.msg = msg;
      window.dispatchEvent(new CustomEvent('nma-py', { detail: { state, msg } }));
    },
    ensure() {
      if (this.promise) return this.promise;
      this.promise = (async () => {
        try {
          const url = (window.NMA_SCROLLY && window.NMA_SCROLLY.pyodideUrl) || DEFAULT_PYODIDE_URL;
          this.set('loading', 'Downloading Python (about 10 MB)…');
          const { loadPyodide } = await import(/* webpackIgnore: true */ url + 'pyodide.mjs');
          const py = await loadPyodide({ indexURL: url });
          await py.runPythonAsync(PY_SETUP);
          this.py = py;
          this.set('ready', 'Python is running in your browser');
          return py;
        } catch (e) {
          this.promise = null;
          this.set('error', String((e && e.message) || e));
          throw e;
        }
      })();
      return this.promise;
    },
    async exec(code, onStatus) {
      const py = this.py;
      let out = '';
      py.setStdout({ batched: (line) => (out += line + '\n') });
      py.setStderr({ batched: (line) => (out += line + '\n') });
      try {
        onStatus && onStatus('Loading packages…');
        await py.loadPackagesFromImports(code, { messageCallback: () => {}, errorCallback: () => {} });
        onStatus && onStatus('Running…');
        await py.globals.get('_nma_exec')(code);
        const proxy = py.globals.get('_nma_figures')();
        const images = proxy.toJs();
        proxy.destroy();
        return { stdout: out, images, error: null };
      } catch (e) {
        try {
          py.globals.get('_nma_figures')().destroy();
        } catch {
          // ignore
        }
        const lines = String((e && e.message) || e).trim().split('\n').filter(Boolean);
        return { stdout: out, images: [], error: { summary: lines.at(-1) || 'Error', detail: lines.slice(-12).join('\n') } };
      }
    },
    /** Run cell `index` with `code`, after any earlier cells that haven't run. Serialised. */
    run(index, code, onStatus) {
      const job = this.queue.then(async () => {
        onStatus && onStatus(this.state === 'ready' ? 'Running…' : 'Starting Python…');
        await this.ensure();
        const page = window.NMA_SCROLLY || { cells: [], edits: {} };
        let usedFallback = false;
        for (const cell of page.cells) {
          if (cell.index >= index || this.done.has(cell.index)) continue;
          const earlier = codeForEarlierCell(cell, page.edits || {});
          onStatus && onStatus(`Running earlier cell ${cell.index + 1}…`);
          const res = await this.exec(earlier.code);
          if (res.error) {
            return {
              stdout: '',
              images: [],
              error: { summary: `Earlier cell ${cell.index + 1} failed: ${res.error.summary}`, detail: res.error.detail },
            };
          }
          usedFallback ||= earlier.fallback;
          this.done.add(cell.index);
        }
        const res = await this.exec(code, onStatus);
        if (!res.error) this.done.add(index);
        if (usedFallback) res.note = FALLBACK_NOTE;
        return res;
      });
      this.queue = job.catch(() => {});
      return job;
    },
  };
}

const RT = typeof window !== 'undefined' ? (window.NMA_PY ||= createRuntime()) : null;

// ---------------------------------------------------------------- the widget

const LABELS = { edit: 'Python · editable', collapsed: 'Python · interactive', output: 'Output' };

function render({ model, el }) {
  const code0 = model.get('code') || '';
  const mode = model.get('mode') || 'edit';
  const params = model.get('params') || [];
  const index = model.get('index') ?? 0;
  const exercise = !!model.get('exercise');
  const initial = model.get('initial');
  const values0 = Object.fromEntries(params.map((p) => [p.name, p.value]));

  const st = { code: code0, values: { ...values0 }, out: initial, note: '' };
  const box = document.createElement('div');
  box.className = `fl-codebox mode-${mode}`;
  const controls = params
    .map((p, i) =>
      p.kind === 'slider'
        ? `<label><span>${esc(p.name)}</span><input type="range" data-i="${i}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.value}" /><output>${esc(formatValue(p.value))}</output></label>`
        : `<label><span>${esc(p.name)}</span><select data-i="${i}">${p.options
            .map((o, k) => `<option value="${k}"${o === p.value ? ' selected' : ''}>${esc(pyLiteral(o))}</option>`)
            .join('')}</select></label>`,
    )
    .join('');
  const hasEditor = mode !== 'output';
  box.innerHTML = `
    ${hasEditor ? `<div class="fl-codehead"><span>${exercise ? 'Exercise · fill in, then run' : LABELS[mode]}</span><span>cell ${index + 1}</span></div>` : ''}
    ${params.length ? `<div class="fl-params">${controls}</div>` : ''}
    ${hasEditor ? '<div class="fl-editor"><pre class="fl-hl" aria-hidden="true"></pre><textarea class="fl-ta" spellcheck="false" wrap="off" aria-label="Python code"></textarea></div>' : ''}
    <div class="fl-actions"><button type="button" class="fl-run">▶ Run</button>${hasEditor ? '<button type="button" class="fl-reset">Reset</button>' : ''}${mode === 'collapsed' ? '<button type="button" class="fl-toggle">Show code</button>' : ''}<span class="fl-status"></span></div>
    <div class="fl-out"><p class="fl-note"></p><pre class="fl-stdout"></pre><div class="fl-err"></div><div class="fl-figs"></div><p class="fl-empty">Run to see output</p></div>`;
  el.appendChild(box);

  const $ = (s) => box.querySelector(s);
  const ta = $('.fl-ta');
  const hl = $('.fl-hl');
  const status = $('.fl-status');
  const runBtn = $('.fl-run');
  let timer = 0;
  let runId = 0;

  if (mode === 'collapsed') {
    box.classList.add('is-collapsed');
    $('.fl-toggle').addEventListener('click', (e) => {
      e.target.textContent = box.classList.toggle('is-collapsed') ? 'Show code' : 'Hide code';
    });
  }

  const syncCode = () => {
    if (hl) hl.innerHTML = highlight(st.code) + '\n';
  };
  const renderOut = () => {
    const o = st.out;
    $('.fl-note').textContent = st.note;
    $('.fl-note').hidden = !st.note;
    $('.fl-stdout').textContent = (o && o.stdout) || '';
    $('.fl-stdout').hidden = !(o && o.stdout);
    $('.fl-err').innerHTML =
      o && o.error ? `<b>${esc(o.error.summary)}</b><details><summary>details</summary><pre>${esc(o.error.detail || '')}</pre></details>` : '';
    $('.fl-figs').innerHTML = ((o && o.images) || [])
      .map((b64) => `<img src="data:image/png;base64,${b64}" alt="Figure produced by the code" />`)
      .join('');
    const empty = !o || (!o.stdout && !o.error && !(o.images && o.images.length));
    $('.fl-empty').hidden = !empty || exercise;
    $('.fl-out').hidden = empty && exercise;
  };
  if (ta) ta.value = st.code;
  syncCode();
  renderOut();

  async function run() {
    const my = ++runId;
    runBtn.disabled = true;
    let res;
    try {
      res = await RT.run(index, applyParams(st.code, st.values), (msg) => {
        if (my === runId) status.textContent = msg;
      });
    } catch (e) {
      res = { stdout: '', images: [], error: { summary: 'Python could not start.', detail: String((e && e.message) || e) } };
    }
    if (my !== runId) return;
    runBtn.disabled = false;
    st.out = res;
    st.note = res.note || '';
    status.textContent = res.error ? '' : 'Done';
    renderOut();
  }

  runBtn.addEventListener('click', run);
  const reset = $('.fl-reset');
  if (reset) {
    reset.addEventListener('click', () => {
      st.code = code0;
      st.values = { ...values0 };
      st.out = initial;
      st.note = '';
      delete window.NMA_SCROLLY?.edits?.[index];
      box.querySelectorAll('[data-i]').forEach((input) => {
        const p = params[Number(input.dataset.i)];
        input.value = p.kind === 'slider' ? p.value : String(p.options.findIndex((o) => o === p.value));
        if (p.kind === 'slider') input.nextElementSibling.textContent = formatValue(p.value);
      });
      ta.value = code0;
      syncCode();
      renderOut();
      status.textContent = '';
    });
  }
  if (ta) {
    ta.addEventListener('input', () => {
      st.code = ta.value;
      if (window.NMA_SCROLLY) (window.NMA_SCROLLY.edits ||= {})[index] = ta.value;
      syncCode();
    });
    ta.addEventListener('scroll', () => {
      hl.scrollLeft = ta.scrollLeft;
      hl.scrollTop = ta.scrollTop;
    });
    ta.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const a = ta.selectionStart;
        ta.value = ta.value.slice(0, a) + '    ' + ta.value.slice(ta.selectionEnd);
        ta.selectionStart = ta.selectionEnd = a + 4;
        ta.dispatchEvent(new Event('input'));
      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || e.shiftKey)) {
        e.preventDefault();
        run();
      }
    });
  }
  box.querySelectorAll('[data-i]').forEach((input) => {
    input.addEventListener('input', () => {
      const p = params[Number(input.dataset.i)];
      if (p.kind === 'slider') {
        st.values[p.name] = Number(input.value);
        input.nextElementSibling.textContent = formatValue(Number(input.value));
      } else st.values[p.name] = p.options[Number(input.value)];
      clearTimeout(timer);
      if (RT.state === 'ready') timer = setTimeout(run, 180);
      else status.textContent = 'Press Run to start Python; after that, changes update the output live.';
    });
  });
  const onPy = (e) => {
    if (runBtn.disabled && e.detail.state === 'loading') status.textContent = e.detail.msg;
  };
  window.addEventListener('nma-py', onPy);
  el.getRootNode().host && (el.getRootNode().host._run = run); // test hook
  RT.set(RT.state, RT.msg); // tell the engine a runtime exists

  return () => {
    clearTimeout(timer);
    window.removeEventListener('nma-py', onPy);
    box.remove();
  };
}

export default { render };
