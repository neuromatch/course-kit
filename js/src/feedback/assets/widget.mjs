// Feedback widget for {nma-feedback} (anywidget ESM, loaded by the MyST theme
// in the browser, no kernel needed). feedback/plugin.mjs fills the model:
//   section_id, url, project, user_key
//
// It does what vibecheck's DatatopsContentReviewContainer does in notebooks:
// 🙂 sends right away, 😐/🙁 ask for a comment first. The request body matches
// vibecheck's, so site and notebook feedback land in the same datatops project.

const CHOICES = [
  { name: 'happy', emoji: '🙂', color: '#aaffaa', label: 'Happy' },
  { name: 'medium', emoji: '😐', color: '#dddd77', label: 'Neutral' },
  { name: 'sad', emoji: '🙁', color: '#ffaaaa', label: 'Unhappy' },
];

const STYLE = `
.nma-fb { margin: 0.75rem 0; font-size: 0.95rem; }
.nma-fb-label { opacity: 0.75; margin: 0 0 0.35rem; }
.nma-fb-buttons { display: flex; gap: 0.5rem; }
.nma-fb-buttons button {
  font-size: 1.6rem; line-height: 1; padding: 0.35rem 0.6rem; cursor: pointer;
  border: 2px solid transparent; border-radius: 0.4rem; color: #000;
}
.nma-fb-buttons button[aria-pressed="true"] { border-color: #666; }
.nma-fb-buttons button:disabled { cursor: default; opacity: 0.6; }
.nma-fb-comment { display: flex; gap: 0.5rem; margin-top: 0.5rem; align-items: stretch; }
.nma-fb-comment[hidden] { display: none; }
.nma-fb-comment textarea {
  flex: 1; min-height: 3rem; padding: 0.4rem; font: inherit; color: inherit;
  background: transparent; border: 1px solid #888; border-radius: 0.3rem;
}
.nma-fb-comment button {
  padding: 0 1rem; cursor: pointer; font: inherit; color: inherit;
  background: transparent; border: 1px solid #888; border-radius: 0.3rem;
}
.nma-fb-status { margin: 0.4rem 0 0; }
.nma-fb-status.error { color: #c62828; }
`;

/** vibecheck's timestamp format: ISO 8601 in UTC without the trailing Z. */
export function timestamp(date = new Date()) {
  return date.toISOString().replace(/Z$/, '');
}

/** POST one response to datatops. Resolves true on success, false otherwise. */
export async function send(settings, buttonName, feedback, fetchImpl = globalThis.fetch) {
  const base = settings.url.replace(/\/+$/, '');
  try {
    const response = await fetchImpl(`${base}/api/v1/projects/${encodeURIComponent(settings.project)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-User-Key': settings.user_key },
      body: JSON.stringify({
        button_name: buttonName,
        feedback,
        section_id: settings.section_id,
        timestamp_utc: timestamp(),
      }),
    });
    if (!response.ok) return false;
    const result = await response.json();
    return result?.status === 'success';
  } catch {
    return false;
  }
}

function element(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children);
  return node;
}

function render({ model, el }) {
  const settings = Object.fromEntries(
    ['section_id', 'url', 'project', 'user_key'].map((key) => [key, model.get(key)]),
  );
  let selected = null;

  const buttons = CHOICES.map((choice) => {
    const button = element('button', {
      type: 'button',
      textContent: choice.emoji,
      title: choice.label,
    });
    button.style.background = choice.color;
    button.setAttribute('aria-label', choice.label);
    button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => choose(choice.name));
    return button;
  });
  const textarea = element('textarea', { placeholder: 'We want your feedback!', rows: 2 });
  textarea.setAttribute('aria-label', 'Your feedback');
  const submit = element('button', { type: 'button', textContent: 'Submit' });
  const comment = element('div', { className: 'nma-fb-comment', hidden: true }, [textarea, submit]);
  const status = element('p', { className: 'nma-fb-status' });
  status.setAttribute('role', 'status');

  const root = element('div', { className: 'nma-fb' }, [
    element('style', { textContent: STYLE }),
    element('p', { className: 'nma-fb-label', textContent: 'How did this section go?' }),
    element('div', { className: 'nma-fb-buttons' }, buttons),
    comment,
    status,
  ]);

  function setBusy(busy) {
    buttons.forEach((b) => (b.disabled = busy));
    submit.disabled = busy;
    textarea.disabled = busy;
  }

  async function submitFeedback(buttonName, text) {
    setBusy(true);
    status.className = 'nma-fb-status';
    status.textContent = 'Sending…';
    if (await send(settings, buttonName, text)) {
      comment.hidden = true;
      buttons.forEach((b) => (b.disabled = true));
      status.textContent = 'Thanks for your feedback!';
    } else {
      setBusy(false);
      status.className = 'nma-fb-status error';
      status.textContent = "Couldn't send feedback, please try again.";
    }
  }

  function choose(name) {
    selected = name;
    CHOICES.forEach((choice, i) => buttons[i].setAttribute('aria-pressed', String(choice.name === name)));
    if (name === 'happy') {
      comment.hidden = true;
      submitFeedback('happy', '');
    } else {
      comment.hidden = false;
      status.textContent = '';
      textarea.focus();
    }
  }

  submit.addEventListener('click', () => submitFeedback(selected, textarea.value));

  el.replaceChildren(root);
  return () => el.replaceChildren();
}

export default { render };
