---
title: "Tutorial 3: A heavy-compute tutorial (Colab)"
runtime: colab
kernelspec:
  name: python3
  display_name: Python 3
---

This page shows how an author marks a tutorial that is too heavy for the browser. Add `runtime: colab` to the frontmatter. The page then shows its code read-only, with a banner that links to Colab and Kaggle, instead of editable cells that can't run here.

Use it for tutorials that need PyTorch, a GPU, large datasets or long training runs.

```{code-cell} python
import torch
from torch import nn

torch.manual_seed(0)
```

A tiny training loop, the kind of thing that belongs in Colab:

```{code-cell} python
model = nn.Linear(1, 1)
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
x = torch.linspace(-1, 1, 64).unsqueeze(1)
y = 3 * x + 0.5

for step in range(200):
  optimizer.zero_grad()
  loss = nn.functional.mse_loss(model(x), y)
  loss.backward()
  optimizer.step()

print(f"final loss: {loss.item():.4f}")
```
