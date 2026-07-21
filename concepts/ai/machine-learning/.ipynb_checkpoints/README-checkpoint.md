# Neural Networks from Scratch (XOR + MNIST)

Two self-contained Jupyter notebooks that build neural networks in **NumPy** from first principles — forward propagation, cost functions, and backpropagation — with visualizations and end-of-section Socratic questions. Each notebook ends with a **PyTorch autograd** comparison.

**Recommended order:** XOR first (tiny, inspectable), then MNIST (batched, multi-class).

## Setup (`learningenv`)

Use the repo-root virtualenv — do **not** create a local `venv` here.

```bash
# from repository root (learning/)
source learningenv/bin/activate
pip install -r concepts/ai/machine-learning/requirements.txt
python -m ipykernel install --user --name=learningenv --display-name="Python (learningenv)"
```

### If `learningenv` does not exist yet

```bash
# from repository root
python3 -m venv learningenv
source learningenv/bin/activate
python -m pip install --upgrade pip
pip install -r concepts/ai/machine-learning/requirements.txt
python -m ipykernel install --user --name=learningenv --display-name="Python (learningenv)"
```

## Run

```bash
source learningenv/bin/activate
cd concepts/ai/machine-learning
jupyter notebook
```

Or execute headlessly to verify:

```bash
jupyter nbconvert --to notebook --execute xor-neural-network.ipynb --output xor-neural-network.ipynb
jupyter nbconvert --to notebook --execute mnist-neural-network.ipynb --output mnist-neural-network.ipynb
```

## Notebooks

| Notebook | Problem | Architecture | Expected runtime |
|----------|---------|--------------|------------------|
| `xor-neural-network.ipynb` | XOR (4 points) | 2 → 4 → 1, sigmoid | ~30 seconds |
| `mnist-neural-network.ipynb` | MNIST subset (10k train) | 784 → 128 → 10, ReLU + softmax | ~2–5 minutes |

## What you'll learn

- Forward propagation layer by layer (with shape annotations)
- Cost functions: binary cross-entropy (XOR) and categorical cross-entropy (MNIST)
- Backpropagation via the chain rule — including the elegant \(\delta = \hat{Y} - Y\) shortcut
- Training loops, decision boundaries, confusion matrices, and weight visualizations
- How PyTorch's `loss.backward()` replaces manual gradient computation
