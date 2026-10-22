---
title: "Project 1: Fitting a Line"
kernelspec:
  name: python3
  display_name: Python 3
---

# Project 1: Fitting a Line

Projects are authored like tutorials and get the same generated notebooks,
Colab and Kaggle badges and solution links, under `notebooks/projects/`.

## Exercise 1

Complete the function so it returns the slope of the line through two points.

```{code-cell} python
def slope(x0, y0, x1, y1):
    raise NotImplementedError("Student exercise: compute the slope")

print(slope(0, 0, 2, 4))
```

::::{nma-solution}
```python
def slope(x0, y0, x1, y1):
    return (y1 - y0) / (x1 - x0)
```
::::
