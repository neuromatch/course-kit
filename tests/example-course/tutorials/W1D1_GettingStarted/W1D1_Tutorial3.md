---
title: "Tutorial 3: Rich Outputs — Figures, Math, Cross-References"
kernelspec:
  name: python3
  display_name: Python 3
---

# Tutorial 3: Rich Outputs

MyST supports a full range of scientific publishing features natively.

## Figures with captions

```{figure} ../../_static/example_figure.png
:label: fig-example
:alt: An example figure used to demonstrate the figure directive
:width: 60%

A figure with a caption and a label. Reference it elsewhere with {numref}`fig-example`.
```

## Math

Inline math: $E = mc^2$

Display math with a label:

$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$ (eq-gaussian)

Reference equations: see {eq}`eq-gaussian`.

## Cross-references

Label any heading with (label)= and reference it with the ref role.

(sec-crossref-demo)=
### This section has a label

Refer back to it anywhere in the book using: ref to sec-crossref-demo.

## Matplotlib figures from code

```{code-cell} python
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(6, 3))
x = np.linspace(0, 2 * np.pi, 200)
ax.plot(x, np.sin(x), label="sin(x)")
ax.plot(x, np.cos(x), label="cos(x)")
ax.legend()
ax.set_xlabel("x")
ax.set_title("Trigonometric functions")
plt.tight_layout()
```

## Tables

| Column A | Column B | Column C |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |

## Summary

- Use the figure directive for captioned images with labels
- Use double-dollar signs for display math with optional equation labels
- Use (label)= syntax to label headings and cross-reference them
- Code cells produce embedded figures automatically
