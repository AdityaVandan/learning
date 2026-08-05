# Neural Networks from Scratch

Self-contained Jupyter notebooks that build core neural architectures in **NumPy** from first principles — with equations, learning notes, Pause & Reflect questions, visualizations, and a **PyTorch** comparison in each notebook.

**Recommended order:** XOR → MNIST → CNN → RNN → LSTM → Transformer.

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
jupyter nbconvert --to notebook --execute cnn.ipynb --output cnn.ipynb
jupyter nbconvert --to notebook --execute rnn.ipynb --output rnn.ipynb
jupyter nbconvert --to notebook --execute lstm.ipynb --output lstm.ipynb
jupyter nbconvert --to notebook --execute transformer-next-token.ipynb --output transformer-next-token.ipynb
```

## Notebooks

| Notebook | Problem | Architecture | Expected runtime |
|----------|---------|--------------|------------------|
| `xor-neural-network.ipynb` | XOR (4 points) | 2 → 4 → 1, sigmoid | ~30 seconds |
| `mnist-neural-network.ipynb` | MNIST subset (10k train) | 784 → 128 → 10, ReLU + softmax | ~2–5 minutes |
| `cnn.ipynb` | Horizontal vs vertical bars | Conv → ReLU → Pool → Dense | ~1 minute |
| `rnn.ipynb` | Next character (`abc` cycle) | Vanilla RNN + BPTT | ~1 minute |
| `lstm.ipynb` | Long-range copy task | LSTM vs RNN comparison | ~1–2 minutes |
| `transformer-next-token.ipynb` | Next-token prediction | Causal self-attention decoder | ~1 minute |

## What you'll learn

### Feedforward (XOR / MNIST)
- Forward propagation layer by layer (with shape annotations)
- Cost functions: binary and categorical cross-entropy
- Backpropagation via the chain rule — including $\delta = \hat{Y} - Y$
- How PyTorch's `loss.backward()` replaces manual gradient computation

### CNN
- 2D convolution, padding, stride, and max-pooling equations
- Weight sharing vs dense-on-pixels parameter counts
- Learned filters as oriented edge detectors

### RNN / LSTM
- Recurrent hidden state and Backpropagation Through Time (BPTT)
- Vanishing gradients on long delays
- LSTM gates and the cell-state “memory highway”

### Transformer
- Scaled dot-product self-attention and causal masking
- Multi-head attention + position-wise FFN decoder block
- Character-level next-token prediction
