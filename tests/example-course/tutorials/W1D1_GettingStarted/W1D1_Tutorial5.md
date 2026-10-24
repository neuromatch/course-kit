---
title: "Tutorial 5: Data and Images (scrolly)"
layout: scrolly
site:
  hide_outline: true
kernelspec:
  name: python3
  display_name: Python 3
---

:::{step} hero
:kicker: data and images
:::
# Tutorial 5: Data in a scrolly page

:::{nma-data}
data/demo.txt
image/demo.png
:::

:::{step}
:section: Reading data
:kicker: Read a file
:::
The declared files are written into the page's Python, so a plain relative
path works here too.

```{code-cell} python
with open("data/demo.txt") as f:
    text = f.read()
print(text.strip())
```

:::{step}
:section: Reading data
:kicker: Read an image
:::
So do images.

```{code-cell} python
with open("image/demo.png", "rb") as f:
    header = f.read(8)
print(header == b"\x89PNG\r\n\x1a\n")
```
