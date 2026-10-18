// The page runtime: one thebe-lite kernel per page, a run queue with notebook
// semantics, and everything that must survive a panel remount (edits, which
// cells ran, the output elements). Shared through window.NMA_CELLS, because the
// panel and runtime-widget bundles each contain their own copy of this module.
//
// window and location are only read inside functions, so tests can set globals.

import { thebeId, thebeScriptUrls, withNoFallback } from './model.mjs';

const STARTING = 'Starting Python… the first run takes about 10 seconds';

const thebeReady = () => Boolean(window.thebeCore?.api && window.thebeLite);

/** MyST loads thebe on executable pages. If it hasn't (yet), load it from the site root. */
export async function ensureThebeLoaded(bundleUrl) {
  if (thebeReady()) return;
  if (bundleUrl && typeof document !== 'undefined') {
    const { core, lite } = thebeScriptUrls(bundleUrl);
    for (const src of [core, lite]) {
      if (document.querySelector(`script[src="${src}"]`)) continue;
      const s = document.createElement('script');
      s.src = src;
      document.head.appendChild(s);
    }
  }
  const deadline = Date.now() + 30000;
  while (!thebeReady()) {
    if (Date.now() > deadline) throw new Error('thebe did not load');
    await new Promise((r) => setTimeout(r, 50));
  }
}

export class PageRuntime {
  constructor(path) {
    this.path = path;
    this.cells = null; // manifest from the runtime widget
    this.edits = {}; // index -> edited source (in memory only)
    this.ran = new Set(); // indices run in the current kernel
    this.ready = null; // thebe handles once booted
    this.bundleUrl = null; // set by the widgets (import.meta.url)
    this.kernel = null; // Promise<handles>
    this.queue = Promise.resolve();
    this.listeners = new Set();
    this.outs = new Map(); // index -> the panel's current light-DOM output element
    this.cellsReady = new Promise((resolve) => (this._resolveCells = resolve));
  }

  setCells(cells) {
    this.cells = cells;
    this._resolveCells(cells);
  }

  subscribe(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  emit(event) {
    for (const fn of this.listeners) fn(event);
  }

  /**
   * A panel hands over its output element (again after a remount). The latest
   * element wins, and an older unregister never drops a newer element.
   */
  register(index, el) {
    this.outs.set(index, el);
    if (this.ready) this.ready.nb.getCellById(thebeId(index))?.attachToDOM(el);
    return () => {
      if (this.outs.get(index) === el) this.outs.delete(index);
    };
  }

  /** Boot thebe-lite once per page. */
  boot() {
    this.kernel ||= (async () => {
      this.emit({ kernel: 'starting', message: STARTING });
      await ensureThebeLoaded(this.bundleUrl);
      const api = window.thebeCore.api;
      const events = api.makeEvents();
      const config = api.makeConfiguration({ useJupyterLite: true }, events);
      const server = api.makeServer(config);
      await server.connectToJupyterLiteServer();
      const rendermime = api.makeRenderMimeRegistry(config.mathjax);
      const cells = await this.cellsReady;
      const nb = api.setupNotebookFromBlocks(
        cells.map((c) => ({ id: thebeId(c.index), source: c.code })),
        config,
        rendermime,
      );
      const session = await server.startNewSession(rendermime);
      nb.attachSession(session);
      this.ready = { api, config, server, rendermime, session, nb };
      // attachToDOM replaces the element's contents (e.g. the "Run to see output" hint).
      for (const [index, el] of this.outs) nb.getCellById(thebeId(index))?.attachToDOM(el);
      this.emit({ kernel: 'ready' });
      return this.ready;
    })();
    this.kernel.catch(() => {
      this.kernel = null; // let the next Run retry
    });
    return this.kernel;
  }

  /**
   * Run cell `index` like a notebook would: earlier unrun cells first (an
   * unfinished earlier exercise runs its solution via the kernel-side
   * fallback), then the target with the fallback switched off. Serialized.
   */
  run(index, source) {
    const job = this.queue.then(async () => {
      const k = await this.boot();
      for (const c of this.cells) {
        if (c.index >= index) break;
        if (this.ran.has(c.index)) continue;
        const res = await this.exec(k, c.index, this.edits[c.index] ?? c.code);
        if (res.error) return { error: res.error, failedIndex: c.index };
      }
      const res = await this.exec(k, index, withNoFallback(source));
      return { error: res.error, failedIndex: res.error ? index : null };
    });
    this.queue = job.catch(() => {});
    return job;
  }

  /**
   * Run every cell top-to-bottom, like a notebook "Run all". Edits are applied
   * and the kernel-side fallback stays on for all cells, so an unfinished
   * exercise runs its solution instead of stopping the run. Serialized through
   * the same queue as single-cell runs; stops at the first cell that errors.
   */
  runAll() {
    const job = this.queue.then(async () => {
      const k = await this.boot();
      for (const c of this.cells) {
        const res = await this.exec(k, c.index, this.edits[c.index] ?? c.code);
        if (res.error) return { error: res.error, failedIndex: c.index };
      }
      return { error: null, failedIndex: null };
    });
    this.queue = job.catch(() => {});
    return job;
  }

  async exec(k, index, source) {
    const cell = k.nb.getCellById(thebeId(index));
    this.emit({ index, state: 'running' });
    const res = await cell.execute(source); // null on internal failure
    this.ran.add(index);
    const raw = res === null || res === undefined ? { ename: 'InternalError' } : res.error?.[0] ?? null;
    // thebe-lite reports the exception class as "<class 'NotImplementedError'>".
    const error = raw && { ...raw, ename: String(raw.ename ?? 'Error').replace(/^<class '(.*)'>$/, '$1') };
    this.emit({ index, state: error ? 'error' : 'done', count: cell.executionCount, error });
    return { error };
  }

  async restart() {
    const k = await this.kernel;
    // session.kernel.restart() / session.restart() leave thebe-lite's notebook without a
    // kernel (verified in the browser, thebe 0.5.0). A fresh session is the working restart.
    await k.server.shutdownAllSessions();
    const session = await k.server.startNewSession(k.rendermime);
    k.nb.attachSession(session);
    k.session = session;
    this.ran.clear();
    this.queue = Promise.resolve();
    this.emit({ kernel: 'ready', restarted: true });
  }

  async dispose() {
    if (!this.kernel) return;
    const k = await this.kernel.catch(() => null);
    await k?.server.shutdownAllSessions();
    k?.server.dispose();
  }
}

/** One runtime per page path; switching pages shuts the old kernel down. */
export function pageRuntime() {
  const path = location.pathname;
  const shared = (window.NMA_CELLS ||= {});
  if (shared.runtime?.path !== path) {
    shared.runtime?.dispose();
    shared.runtime = new PageRuntime(path);
  }
  return shared.runtime;
}
