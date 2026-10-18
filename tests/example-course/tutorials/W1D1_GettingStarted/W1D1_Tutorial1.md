---
title: "Tutorial 1: Writing Content in MyST Markdown"
kernelspec:
  name: python3
  display_name: Python 3
---

# Tutorial 1: Writing Content in MyST Markdown

MyST (Markedly Structured Text) is the markup language powering this book.
It extends standard Markdown with directives and roles that produce rich,
structured scientific content.

## Why MyST instead of notebooks?

MyST `.md` files are the **source of truth** for this template. Jupyter notebooks
(`.ipynb`) are generated automatically by CI — you never edit them by hand.

Benefits:
- **Clean git diffs** — no output noise, no cell metadata churn
- **Human-readable** — readable in any text editor
- **Full Jupyter execution** at build time and in-browser via JupyterLite

## Basic Markdown

Everything standard Markdown supports works in MyST:

- **Bold**, *italic*, `inline code`
- [Links](https://mystmd.org)
- Images: `![alt text](path/to/image.png)`

## Admonitions

Use admonitions to call out notes, warnings, and exercises:

```{note}
This is a note admonition. Use it for supplementary information.
```

```{warning}
This is a warning. Use it to flag common mistakes.
```

```{admonition} Exercise 1.1
:class: tip

Replace the text in this admonition with your own exercise prompt.
Your students will see this highlighted block in the rendered book.
```

## Code cells

Add executable code with the `{code-cell}` directive:

```{code-cell} python
# This cell runs in JupyterLite (in the browser) or via myst build --execute
message = "Hello from MyST!"
print(message)
```

## Hiding cells

Tag cells to control visibility:

```{code-cell} python
:tags: [hide-input]
# Students see the output but not this code
import numpy as np
print(f"pi = {np.pi:.6f}")
```

```{code-cell} python
:tags: [remove-cell]
# This cell is completely hidden in the rendered book
# Use it for setup code you do not want students to see
pass
```

## Summary

- Write prose in plain Markdown
- Use {code-cell} for executable code
- Use admonitions to structure exercises and notes
- Tag cells with hide-input or remove-cell to control what students see
