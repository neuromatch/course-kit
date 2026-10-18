---
title: "Tutorial 6: Scrollytelling Pages"
layout: scrolly
site:
  hide_outline: true
kernelspec:
  name: python3
  display_name: Python 3
---

This page is itself a scrollytelling page. Each card explains one feature and shows its syntax, and the stage next to it shows that feature working. [W2D1 Tutorial 2](../W2D1_Examples/W2D1_Tutorial2.md) is a full tutorial built this way.

```{code-cell} python
:tags: [remove-cell]
# Setup (a remove-cell: hidden on the site, run before the first visible cell)
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(2026)
```

:::{step} hero
:kicker: neuromatch course template
:::
# Tutorial 6: *Scrollytelling pages*

A pinned stage of figures, videos and live Python, with text cards that scroll past.

**Time:** about 20 minutes

:::{step}
:section: Basics
:kicker: What and when
:::
## What a scrolly page is

A scrolly page is an ordinary tutorial `.md` file with one extra frontmatter line. The page is split into **steps**. Each step has a **card** (the text you are reading) and a **stage** (the pinned area next to it, or above it on a phone).

**Use it for** narrative walkthroughs: a sequence of figures, short demos and videos, where each idea needs one picture.

**Don't use it for** long reference material, or for pages that are mostly heavy exercises. Those read better as normal pages.

:::{stage}
:style: list
### A scrolly page

1. Is still one flat MyST `.md` file
2. Still produces a normal notebook for Colab and Kaggle
3. Shows real figures before Python starts
4. Runs Python in the browser when the reader asks
:::

:::{step}
:kicker: Turning it on
:::
## `layout: scrolly` and `{step}`

Add `layout: scrolly` to the frontmatter, hide the "On this page" outline (recommended, see below), then put a `{step}` marker wherever a new step starts. A step runs from its marker to the next one. Markers have no body: the content goes **after** the closing fence.

````markdown
---
title: "Tutorial 2: My topic"
layout: scrolly
site:
  hide_outline: true
kernelspec:
  name: python3
  display_name: Python 3
---

:::{step} hero
:::
# My topic

:::{step}
:::
Text for the first card.

:::{step}
:::
Text for the second card.
````

MyST logs `extra key ignored: layout`, which is expected.

`hide_outline` removes the "On this page" outline on this page only, which gives the scrolly section more room. Keep the table of contents (don't set `hide_toc`): on a page this long it is how readers move to other pages without scrolling to the end. The section fits between the menus, and when that is too narrow the stage sits above the cards instead of beside them. The previous/next links at the bottom of the page work as on any other page.

:::{step}
:kicker: Options
:::
## `hero`, `:section:`, `:kicker:` and `{stage}`

- `{step} hero` makes a full-screen title or closing step, with no card. The first step of this page is one.
- `:section:` sets the label in the progress bar at the top of the stage. It carries forward until the next step that sets it.
- `:kicker:` is the small label above a card, like "Options" above this one.
- `{stage}` holds markdown that only appears on the stage. `:style: list` turns a list into the numbered chips shown here. `:class:` adds CSS classes.

````markdown
:::{step}
:section: Basics
:kicker: Options
:::
Card text.

:::{stage}
:style: list
1. Shown on the stage as a chip
2. Another chip
:::
````

:::{stage}
:style: list
### Step options

1. `hero`: full screen, no card
2. `:section:` label in the progress bar
3. `:kicker:` label above the card
4. `{stage}` for stage-only markdown
:::

:::{step}
:kicker: Stage or card
:::
## What goes where

The plugin sorts each step's content for you:

| Stage | Card |
|---|---|
| code cells (except `remove-cell`) | prose, math, headings |
| images and `{figure}` (also `.mp4`) | `{nma-solution}` / `{nma-explanation}` links |
| `{nma-video}`, `{nma-slides}` | `{nma-feedback}` |
| the `{stage}` block | everything else |

If a step has nothing for the stage, **the previous stage stays**. This step is an example: the chips from the last step are still showing. Content before the first `{step}` renders as a normal page header.

:::{step}
:section: Code
:kicker: Code cells
:::
## An editable cell

An untagged code cell becomes an editable panel with **Run** and **Reset**. Change the code and run it (Ctrl+Enter also works).

The first Run downloads Python into your browser. All cells on the page share one namespace, and running a cell first runs any earlier cells that haven't run yet. So `rng` below comes from the hidden setup cell at the top of the page, without you running it.

```{code-cell} python
samples = rng.normal(loc=0.0, scale=1.0, size=1000)
print(f"mean = {samples.mean():.3f}, std = {samples.std():.3f}")
```

:::{step}
:kicker: Code cells
:::
## Tags choose how a cell looks

| Tag | On the stage |
|---|---|
| none | editable panel (code + output) |
| `hide-input` | code collapsed behind "Show code" |
| `remove-input` | output only |
| `remove-cell` | invisible, runs before the first visible cell |

This step's cell is tagged `hide-input`: the output shows, and the code is one click away.

```{code-cell} python
:tags: [hide-input]
counts, edges = np.histogram(samples, bins=30)
plt.figure(figsize=(6, 3.5))
plt.stairs(counts, edges, fill=True)
plt.xlabel("value")
plt.ylabel("count")
plt.title("1000 samples from a normal distribution")
plt.show()
```

:::{step}
:kicker: Code cells
:::
## Output-only figures

A `remove-input` cell shows only its output. Use it for figures that tell the story, where the code would be a distraction.

````markdown
```{code-cell} python
:tags: [remove-input]
plt.plot(...)
plt.show()
```
````

```{code-cell} python
:tags: [remove-input]
t = np.linspace(0, 2 * np.pi, 400)
fig, ax = plt.subplots(figsize=(6, 3.5))
for k in [1, 2, 3]:
  ax.plot(t, np.sin(k * t), label=f"sin({k}t)")
ax.set(xlabel="t", ylabel="value", title="A remove-input figure")
ax.legend(loc="upper right")
plt.show()
```

:::{step}
:section: Demos
:kicker: Interactive demos
:::
## Sliders and dropdowns with `# @param`

Mark an assignment with a Colab form comment, and the panel gets a control. Moving it reruns the cell.

```python
freq = 2.0      # @param {type:"slider", min:0.5, max:5, step:0.5}
shape = "sine"  # @param ["sine", "square", "sawtooth"]
```

Rules: one top-level assignment per line, numbers for sliders (`step` defaults to 1), and a list of literals for dropdowns that includes the default. Before Python starts, the stage shows the output for the defaults.

```{code-cell} python
:tags: [hide-input]
# @title Sliders and dropdowns
freq = 2.0      # @param {type:"slider", min:0.5, max:5, step:0.5}
shape = "sine"  # @param ["sine", "square", "sawtooth"]

t = np.linspace(0, 2, 1000)
wave = {
  "sine": np.sin(2 * np.pi * freq * t),
  "square": np.sign(np.sin(2 * np.pi * freq * t)),
  "sawtooth": 2 * (freq * t % 1) - 1,
}[shape]
plt.figure(figsize=(6, 3))
plt.plot(t, wave)
plt.xlabel("time (s)")
plt.title(f"{shape} wave, {freq} Hz")
plt.show()
```

:::{step}
:kicker: Interactive demos
:::
## From `widgets.interact` to `# @param`

Existing NMA demos use ipywidgets. On a scrolly page, rewrite them with `# @param`:

```python
# Before
@widgets.interact(a=widgets.FloatSlider(value=-0.5, min=-2.5, max=1.5, step=0.25))
def plot_demo(a):
  plt.plot(t, np.exp(a * t)); plt.show()

# After
a = -0.5  # @param {type:"slider", min:-2.5, max:1.5, step:0.25}
plt.plot(t, np.exp(a * t)); plt.show()
```

You don't lose anything in the notebooks: the generated `.ipynb` turns every `# @param` cell back into a `widgets.interact` demo, as shown on the stage.

:::{stage}
```python
# The demo from the last step, as it appears in the notebook
# @title Sliders and dropdowns
import ipywidgets as widgets


@widgets.interact(freq=widgets.FloatSlider(value=2.0, min=0.5, max=5, step=0.5, continuous_update=False), shape=widgets.Dropdown(options=['sine', 'square', 'sawtooth'], value='sine'))
def _demo(freq, shape):
    t = np.linspace(0, 2, 1000)
    ...
```
:::

:::{step}
:section: Exercises
:kicker: Exercises
:::
## Exercises, solutions and explanations

These work exactly as in [Tutorial 5](./W1D2_Tutorial5.md): an untagged exercise cell, directly followed by an `{nma-solution}`. The card gets the *Click for solution* link.

Try it: fill in `cube`, or don't. If you run the **next** cell first, the page runs the reference solution in place of the unfinished exercise and says so, so you can always run ahead.

```{code-cell} python
def cube(x):
  ###################################################################
  ## Fill out the following then remove
  raise NotImplementedError("Student exercise: return x cubed")
  ###################################################################
  return ...
```

::::{nma-solution}
```python
def cube(x):
  return x ** 3
```
::::

:::{step}
:kicker: Exercises
:::
## Running ahead

This cell uses `cube` from the exercise. Run it before finishing the exercise to see the fallback note.

```{code-cell} python
print([cube(n) for n in range(1, 6)])
```

:::{nma-explanation}
The cell prints `[1, 8, 27, 64, 125]`. If `cube` still raises
`NotImplementedError`, the page runs the `{nma-solution}` code instead and
shows a note. The solutions are hidden, not secret, as on every other page.
:::

:::{step}
:kicker: Media and feedback
:::
## Videos and feedback

`{nma-video}` and `{nma-slides}` go on the stage, and `{nma-feedback}` stays on the card. Both work as in [Tutorial 4](./W1D2_Tutorial4.md). Media keep playing only while their step is active: muted `.mp4` figures play and pause as you scroll.

:::{nma-video} Video 1: Linear Dynamical Systems
:youtube: 87z6OR7-DBI
:bilibili: BV1up4y1S7wj
:::

Did this step make sense?

:::{nma-feedback} Scrolly_Media_And_Feedback
:::

:::{step}
:section: Under the hood
:kicker: Browser Python
:::
## Python in the browser

The **Enable Python** pill at the top of the stage (or any Run button) starts [Pyodide](https://pyodide.org) once for the page. The first load is about 10 MB plus the packages a cell imports, and the browser then caches it. JupyterLite is not used on scrolly pages, so its power button is hidden.

- Packages come from the cells' imports. numpy, matplotlib, scipy and pandas all work. Anything Pyodide can't run belongs in the Colab notebook.
- No sockets: load data files with `pyodide.http.open_url` under `sys.platform == "emscripten"` (see the setup cell of W2D1 Tutorial 2).
- The Pyodide build comes from `nma.scrolly.pyodide_url` in `myst.yml`. The host must send CORS headers.

:::{stage}
```yaml
# myst.yml
project:
  plugins:
    - plugins/nma.mjs
    - plugins/scrolly/scrolly.mjs

nma:
  scrolly:
    pyodide_url: https://cdn.jsdelivr.net/pyodide/v314.0.7/full/
```
:::

:::{step}
:kicker: Pre-rendered outputs
:::
## Real figures before Python starts

In CI, `scripts/nma_scrolly.py --render` runs every scrolly page's **instructor** notebook (solutions filled in, `# @param` at their defaults) and saves the outputs. The plugin puts them in the page, so every figure above appeared without starting Python. Never type outputs by hand.

- A cell that raises **fails the build**, naming the file and line.
- Exercise cells get no starting output.
- Without a render file (for example, plain `myst start`), panels show *Run to see output*.

:::{stage}
```bash
# Preview with real outputs locally
uv run python scripts/nma_scrolly.py --render
uv run myst start

# Writes _build/scrolly/<Day>/<Tutorial>.json
```
:::

:::{step}
:kicker: Notebooks
:::
## The Colab and Kaggle version

A scrolly page with a `kernelspec` still gets a linear notebook, generated the usual way:

- `{step}` markers disappear. A `:kicker:` becomes an italic line.
- `{stage}` blocks become plain markdown.
- `# @param` cells become `widgets.interact` demos.
- Videos, solutions and feedback become the usual NMA cells, with student and instructor versions.

Open this page's notebook from the badges at the top to see the result. A scrolly page without code or `kernelspec` is site-only.

:::{step}
:section: Your turn
:kicker: Converting a tutorial
:::
## Converting an existing tutorial

[W2D1 Tutorial 2](../W2D1_Examples/W2D1_Tutorial2.md) is [Tutorial 1](../W2D1_Examples/W2D1_Tutorial1.md) converted this way:

1. Copy the page and add `layout: scrolly`, plus `site: hide_outline: true`.
2. Merge setup, figure style and helpers into one `remove-cell` cell. Drop `%` magics and the ipywidgets import.
3. Add a `{step}` before each idea that needs its own picture, with `:section:` at section starts and `:kicker:` labels.
4. Rewrite `widgets.interact` demos with `# @param`.
5. Add `remove-input` figures where a card has nothing to show.
6. Avoid "on the right" in card text: the notebook reads it too.
7. Run `--render` and `myst start`, and scroll through it.

:::{step}
:kicker: CI errors
:::
## Errors you may see

| Message | Fix |
|---|---|
| `{step} only works on pages with layout: scrolly` | Add `layout: scrolly`, or remove the marker |
| `page has layout: scrolly but no {step} markers` | Add at least one `{step}` |
| `{step} has no body` | Move the content below the closing `:::` |
| `{step} takes no argument or hero` | Use `{step}` or `{step} hero` |
| `unknown option` | `{step}`: `:section:`, `:kicker:`. `{stage}`: `:style:`, `:class:` |
| `step has more than one {stage}` / `before the first {step}` | One `{stage}` per step, after its marker |
| `must be at the top level` | Don't nest markers in other directives |
| `# @param must not be indented` / `must be an assignment` | One top-level `name = value  # @param ...` per line |
| `default ... is not one of the options` | Include the default in the dropdown list |
| `T.md:42: ZeroDivisionError` (render) | Fix the cell at that line; it raised in CI |

:::{step} hero
:section: Done
:kicker: that's it
:::
# Now *write your own*

Start from W2D1 Tutorial 2, or add `layout: scrolly` and a few `{step}` markers to a page you already have.
