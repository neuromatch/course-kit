---
title: "Tutorial 4: Data and Images"
kernelspec:
  name: python3
  display_name: Python 3
---

# Tutorial 4: Data and Images

Keep shared files in the day folder, in `data/` and `images/`. Images the page
only displays need no declaration: the build publishes them for Colab. Files
the code reads are declared with `{nma-data}`. Plain relative paths then work on
the site, in the editable cells and in the generated Colab notebook.

:::{nma-data}
data/demo.txt
images/demo.png
:::

This image is referenced with a relative path:

![A single red pixel](images/demo.png)

The `{figure}` directive works too, and becomes an `<img>` in the notebook:

```{figure} images/demo.png
:alt: The same pixel, as a figure
:width: 80px

A figure with a caption.
```

## Reading a data file

```{code-cell} python
with open("data/demo.txt") as f:
    text = f.read()
print(text.strip())
```

## Reading an image file

```{code-cell} python
with open("images/demo.png", "rb") as f:
    header = f.read(8)
print(header == b"\x89PNG\r\n\x1a\n")
```
