// CodeMirror 6 editor for one cell. Colors come from CSS variables (cells.css),
// so a course restyles panels from _static/custom.css without touching JS.
// No basicSetup: the explicit list is smaller and leaves out search/autocomplete popups.

import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from '@codemirror/view';
import { EditorState, Prec } from '@codemirror/state';
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
import { indentUnit, bracketMatching, syntaxHighlighting, HighlightStyle } from '@codemirror/language';
import { closeBrackets } from '@codemirror/autocomplete';
import { python } from '@codemirror/lang-python';
import { tags as t } from '@lezer/highlight';

const highlight = HighlightStyle.define([
  { tag: t.keyword, color: 'var(--nma-tok-keyword)' },
  { tag: [t.string, t.special(t.string)], color: 'var(--nma-tok-string)' },
  { tag: [t.number, t.bool, t.null], color: 'var(--nma-tok-number)' },
  { tag: t.comment, color: 'var(--nma-tok-comment)', fontStyle: 'italic' },
  { tag: [t.function(t.variableName), t.function(t.propertyName)], color: 'var(--nma-tok-function)' },
  { tag: [t.definition(t.variableName), t.className], color: 'var(--nma-tok-definition)' },
]);

const theme = EditorView.theme({
  '&': { color: 'var(--nma-cell-fg)', backgroundColor: 'var(--nma-cell-bg)', fontSize: 'var(--nma-cell-font-size)' },
  '.cm-content': { fontFamily: 'var(--nma-cell-font)', caretColor: 'var(--nma-cell-accent)' },
  '.cm-cursor': { borderLeftColor: 'var(--nma-cell-accent)' },
  '.cm-gutters': { backgroundColor: 'var(--nma-cell-gutter-bg)', color: 'var(--nma-cell-gutter-fg)', border: 'none' },
  '.cm-activeLine': { backgroundColor: 'var(--nma-cell-active-line)' },
  '.cm-activeLineGutter': { backgroundColor: 'var(--nma-cell-active-line)' },
  '&.cm-focused': { outline: '2px solid var(--nma-cell-accent)' },
});

export function createEditor({ parent, root, doc, onChange, onRun }) {
  // Prec.highest: the default keymap otherwise swallows Shift-Enter.
  const runKeys = Prec.highest(
    keymap.of([
      { key: 'Shift-Enter', run: () => (onRun(), true) },
      { key: 'Mod-Enter', run: () => (onRun(), true) },
    ]),
  );
  const view = new EditorView({
    parent,
    root, // the shadow root
    state: EditorState.create({
      doc,
      extensions: [
        runKeys,
        lineNumbers(),
        highlightActiveLine(),
        drawSelection(),
        history(),
        bracketMatching(),
        closeBrackets(),
        indentUnit.of('    '),
        keymap.of([indentWithTab, ...defaultKeymap, ...historyKeymap]),
        python(),
        syntaxHighlighting(highlight),
        theme,
        EditorView.contentAttributes.of({ 'aria-label': 'Python code' }),
        EditorView.updateListener.of((u) => u.docChanged && onChange(u.state.doc.toString())),
      ],
    }),
  });
  return {
    text: () => view.state.doc.toString(),
    setText: (s) => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: s } }),
    destroy: () => view.destroy(),
  };
}
