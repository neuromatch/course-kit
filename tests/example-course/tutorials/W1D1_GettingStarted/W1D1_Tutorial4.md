---
title: "Tutorial 4: Data and Images"
kernelspec:
  name: python3
  display_name: Python 3
---

# Tutorial 4: Data and Images

Keep shared files in the day folder, in `data/` and `image/`, and declare the
ones this tutorial uses with `{nma-data}`. Plain relative paths then work on
the site, in the editable cells and in the generated Colab notebook.

:::{nma-data}
data/demo.txt
image/demo.png
:::

This image is referenced with a relative path:

![A single red pixel](image/demo.png)

## Reading a data file

```{code-cell} python
with open("data/demo.txt") as f:
    text = f.read()
print(text.strip())
```

## Reading an image file

```{code-cell} python
with open("image/demo.png", "rb") as f:
    header = f.read(8)
print(header == b"\x89PNG\r\n\x1a\n")
```
