# Transformer Attention — Complete Notes

## 0. Big Picture — How an LLM Computes

End-to-end path from raw text to the next predicted token:

```mermaid
flowchart LR
    subgraph Input
        T["tokens<br/>'the cat sat'"]
        E["token + position<br/>embeddings X"]
    end

    subgraph Stack["Transformer stack × L layers"]
        direction TB
        MHA["Multi-Head<br/>Self-Attention"]
        Add1["+ residual<br/>→ LayerNorm"]
        FFN["Feed-Forward<br/>Network (MLP)"]
        Add2["+ residual<br/>→ LayerNorm"]
        MHA --> Add1 --> FFN --> Add2
    end

    subgraph Output
        H["final hidden h<br/>(last position)"]
        Z["logits z = h W_vocab"]
        P["softmax → P(token)"]
        Next["sample / argmax<br/>→ next token"]
    end

    T --> E --> Stack --> H --> Z --> P --> Next
    Next -.->|"append & repeat<br/>(autoregressive)"| T
```

One transformer **block** in more detail (decoder-style LLM):

```mermaid
flowchart TB
    X["Input X<br/>(n × d_model)"]
    LN1["LayerNorm"]
    Attn["Multi-Head Attention"]
    Res1["X + Attn(X)"]
    LN2["LayerNorm"]
    MLP["FFN / MLP<br/>Linear → Act → Linear"]
    Res2["X' + MLP(X')"]
    Out["Block output<br/>(n × d_model)"]

    X --> LN1 --> Attn --> Res1
    X --> Res1
    Res1 --> LN2 --> MLP --> Res2
    Res1 --> Res2 --> Out
```

---

## 1. What is an Attention Head?

An **attention head** is one instance of the self-attention mechanism. Transformers run several heads in parallel — this is **multi-head attention**.

Each head learns three projections of the input embeddings:

- **Query (Q)** — what this token is "looking for"
- **Key (K)** — what this token "offers" to be matched against
- **Value (V)** — the actual content passed along if attended to

Each token gets a new representation that's a weighted blend of other tokens' Values, based on Query–Key similarity.

**Why multiple heads instead of one big head:** each head can specialize — one might track syntax (subject-verb agreement), another coreference (pronoun → noun), another positional patterns. Outputs are combined at the end.

```mermaid
flowchart LR
    X["Input X<br/>all tokens"]

    subgraph Heads["Multi-Head Attention (parallel)"]
        direction TB
        H1["Head 1<br/>e.g. syntax"]
        H2["Head 2<br/>e.g. coreference"]
        H3["Head 3<br/>e.g. position"]
        Hh["Head h<br/>…"]
    end

    C["Concatenate<br/>head outputs"]
    WO["Linear W_O"]
    Y["Output<br/>same shape as X"]

    X --> H1 & H2 & H3 & Hh
    H1 & H2 & H3 & Hh --> C --> WO --> Y
```

How Q / K / V relate for one token attending to others:

```mermaid
flowchart TB
    subgraph Token_i["Token i (the 'asker')"]
        Qi["Query q_i"]
    end

    subgraph AllTokens["All tokens j = 1…n"]
        Kj["Keys k_1 … k_n<br/>(what each offers)"]
        Vj["Values v_1 … v_n<br/>(content to blend)"]
    end

    Score["scores = q_i · k_j<br/>→ softmax → weights α_ij"]
    Out["new vector for i<br/>= Σ_j α_ij · v_j"]

    Qi --> Score
    Kj --> Score
    Score --> Out
    Vj --> Out
```

---

## 2. Is the Value Constant Per Head?

**No** — each head has its own separate, independently-learned Value projection matrix $W_V^i$.

Three levels to keep straight:

1. **Across heads (same layer):** each head has a different $W_V^i$ → different "lens" on the same input.
2. **Across tokens (same head):** $V = XW_V$ depends on input $X$, so different tokens → different value vectors even within one head.
3. **Across forward passes:** $W_V$ (the weights) is fixed after training; the $V$ vectors it produces still vary per input sequence.

So: **weights are fixed per head after training, but the actual Value vectors are dynamic**, computed fresh from input each time.

```mermaid
flowchart TB
    X["Same input X"]

    subgraph Layer["One layer — different heads"]
        WV1["W_V¹ → V¹"]
        WV2["W_V² → V²"]
        WVh["W_Vʰ → Vʰ"]
    end

    Note["Same X, different lenses<br/>→ different Value matrices"]

    X --> WV1 & WV2 & WVh --> Note
```

```mermaid
flowchart LR
    subgraph Fixed["After training (fixed)"]
        W["W_Q, W_K, W_V<br/>learned weights"]
    end

    subgraph Dynamic["Each forward pass (dynamic)"]
        Xin["this sequence's X"]
        Vout["V = X W_V<br/>fresh every time"]
    end

    W --> Vout
    Xin --> Vout
```

---

## 3. Equations Inside a Single Attention Head

**Setup:** Input sequence $X \in \mathbb{R}^{n \times d_{model}}$ ($n$ tokens).

### Computation flow (one head)

```mermaid
flowchart TB
    X["X ∈ ℝⁿˣᵈ_model"]

    subgraph Proj["1. Project"]
        Q["Q = X W_Q"]
        K["K = X W_K"]
        V["V = X W_V"]
    end

    S["2. Scores S = Q Kᵀ<br/>(n × n)"]
    Sc["3. Scale S / √d_k"]
    M["4. Causal mask<br/>(decoder: future → −∞)"]
    A["5. Softmax → A<br/>(rows sum to 1)"]
    O["6. Output = A V"]

    X --> Q & K & V
    Q --> S
    K --> S
    S --> Sc --> M --> A
    A --> O
    V --> O
```

Causal mask intuition (token $i$ may only look at positions $j \le i$):

```mermaid
flowchart LR
    subgraph Mask["Causal attention mask (✓ = allowed)"]
        direction TB
        R1["t1: ✓ · · ·"]
        R2["t2: ✓ ✓ · ·"]
        R3["t3: ✓ ✓ ✓ ·"]
        R4["t4: ✓ ✓ ✓ ✓"]
    end
```

### Step 1 — Project into Q, K, V
$$
Q = XW_Q \qquad K = XW_K \qquad V = XW_V
$$
$W_Q, W_K \in \mathbb{R}^{d_{model}\times d_k}$, $W_V \in \mathbb{R}^{d_{model}\times d_v}$

### Step 2 — Raw attention scores
$$
S = QK^T \in \mathbb{R}^{n\times n}
$$
$S_{ij}$ = relevance of token $j$ to token $i$'s query.

### Step 3 — Scale
$$
S_{scaled} = \frac{QK^T}{\sqrt{d_k}}
$$
Prevents large dot products from saturating softmax.

### Step 4 — Mask (decoder only)
$$
S_{masked,ij} = \begin{cases} S_{scaled,ij} & j \le i \\ -\infty & j > i \end{cases}
$$
Blocks attending to future tokens (causal attention). Skipped in bidirectional/encoder attention.

### Step 5 — Softmax (row-wise)
$$
A_{ij} = \text{softmax}(S_{masked})_{ij} = \frac{\exp(S_{masked,ij})}{\sum_k \exp(S_{masked,ik})}
$$
Each row of $A$ sums to 1 — the attention weights.

### Step 6 — Weighted sum of Values
$$
\text{head}_{output} = AV
$$

### Compact formula
$$
\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

### Multi-head assembly
$$
\text{head}_i = \text{Attention}(XW_Q^i, XW_K^i, XW_V^i)
$$
$$
\text{MultiHead}(X) = \text{Concat}(\text{head}_1,\dots,\text{head}_h)\,W_O
$$
$W_O \in \mathbb{R}^{(h\cdot d_v)\times d_{model}}$ projects concatenated heads back to model dimension.

```mermaid
flowchart TB
    X["X"]

    subgraph Parallel["h heads in parallel"]
        direction LR
        H1["head₁ = Attn(X W_Q¹, …)"]
        H2["head₂"]
        Hh["headₕ"]
    end

    Cat["Concat → shape n × (h · d_v)<br/>e.g. 8 × 64 = 512"]
    WO["× W_O<br/>→ n × d_model"]
    Y["MultiHead(X)"]

    X --> H1 & H2 & Hh --> Cat --> WO --> Y
```

---

## 4. Rationale Behind Each Equation (History & Motivation)

| Step | Problem it solves | Origin / Alternative |
|---|---|---|
| **Separate Q/K/V** | Earlier attention (Bahdanau 2014) reused the same hidden state for both "matching" and "retrieving" — conflated two jobs | Borrowed from information-retrieval framing: query vs. key vs. document content are different roles |
| **Dot product for scores** | Cheap, maps to a single matmul — GPU/TPU-friendly | Bahdanau used additive attention (small feedforward net) — better for small $d_k$ but doesn't parallelize as well |
| **Scale by $\sqrt{d_k}$** | Dot product variance grows with $d_k$ → softmax saturates → vanishing gradients | Derived analytically: if $q,k$ components have mean 0, variance 1, then $q\cdot k$ has variance $d_k$; dividing by $\sqrt{d_k}$ renormalizes to variance 1 (same spirit as Xavier/He init) |
| **Masking** | Autoregressive models must not see future tokens | RNNs get causality "for free" from sequential structure; transformers must enforce it explicitly since they see the whole sequence at once |
| **Softmax** | Need non-negative, sums-to-1, differentiable weights | Standard from classification output layers; novelty was applying it to attention weights, not softmax itself |
| **Weighted sum (not hard lookup)** | Need a differentiable "soft" retrieval so backprop works | Traces to Bahdanau 2014 and Graves' Neural Turing Machines (2014) — soft/differentiable memory addressing |
| **Multi-head split** | One attention op over full dimension can only learn one relationship type per layer | Analogous to multiple filters in a CNN — each head specializes (empirically confirmed later, e.g. Clark et al. 2019 "What Does BERT Look At?") |
| **Concat + $W_O$** | Heads need a way to combine/mix what they each learned | Without this, heads stay informationally siloed |

**Big picture:** most individual equations predate the 2017 "Attention Is All You Need" paper. The real contribution was showing recurrence could be **removed entirely**, giving a fully parallelizable architecture built purely from attention + feedforward layers.

```mermaid
flowchart LR
    RNN["RNN / LSTM<br/>sequential, slow"]
    Attn2014["Bahdanau attention<br/>still on top of RNN"]
    Trans["Transformer 2017<br/>attention + FFN only<br/>fully parallel"]

    RNN --> Attn2014 --> Trans
```

---

## 5. What Does Concatenation of Heads Mean?

Concatenation = **lining up each head's output vector side by side**, not blending/averaging them.

If each head outputs a vector of size $d_v$ (e.g. 64) and there are $h$ heads (e.g. 8):
$$
\text{Concat}(\text{head}_1,\dots,\text{head}_8) = [\underbrace{h_1}_{64}, \underbrace{h_2}_{64}, \dots, \underbrace{h_8}_{64}] \quad \to \text{512 numbers total}
$$

**Why not average instead?** Averaging would blend/mush different heads' distinct discoveries together, losing the specialization. Concatenation keeps each head's output fully intact; the subsequent linear layer $W_O$ is responsible for actually mixing the information across heads.

```mermaid
flowchart LR
    subgraph Heads["Per-token head outputs"]
        h1["head₁<br/>64 dims"]
        h2["head₂<br/>64 dims"]
        h3["…"]
        h8["head₈<br/>64 dims"]
    end

    Cat["Concat<br/>[h₁ | h₂ | … | h₈]<br/>= 512 dims"]
    Avg["✗ Average<br/>would mush<br/>specializations"]
    WO["W_O mixes<br/>across heads"]
    Out["d_model output"]

    h1 & h2 & h3 & h8 --> Cat
    Cat --> WO --> Out
    h1 -.-> Avg
```

---

## 6. Predicting the Next Word (Output Stage)

After all transformer blocks, each token position has a final hidden vector $h \in \mathbb{R}^{d_{model}}$.

### Step 1 — Project to vocabulary size (unembedding)
$$
z = hW_{vocab} \in \mathbb{R}^{|V|}
$$
$|V|$ = vocabulary size. $z$ = raw logits, one score per possible token.

> Note: $W_{vocab}$ is often the *same* matrix used for input embeddings, transposed and reused — called **weight tying**.

### Step 2 — Softmax → probabilities
$$
P(\text{token}=i \mid \text{context}) = \frac{\exp(z_i)}{\sum_j \exp(z_j)}
$$

### Step 3 — Pick the next word
- **Greedy decoding:** take $\arg\max$ — simple but can be repetitive
- **Sampling:** randomly draw according to probabilities — more variety
- **Top-k / top-p (nucleus) sampling:** restrict sampling pool to most likely tokens first
- **Temperature ($T$):** $\text{softmax}(z/T)$ — low $T$ → sharper/greedier, high $T$ → flatter/more random

### Step 4 — Repeat (autoregressive)
Append the chosen token, reprocess the whole sequence through all layers again, predict the next token. Repeat until a stop condition (EOS token / max length).

### Full pipeline
$$
\text{tokens} \to \text{embeddings} \to \text{transformer blocks} \to h \to z=hW_{vocab} \to \text{softmax}(z) \to \text{sample/argmax} \to \text{next token}
$$

```mermaid
flowchart TB
    H["final hidden h<br/>(usually last position)"]
    Z["z = h W_vocab<br/>logits over |V|"]
    Soft["softmax(z / T)"]
    Dec{"decoding strategy"}
    Greedy["greedy: argmax"]
    Sample["sample / top-k / top-p"]
    Tok["next token"]
    Append["append to sequence"]
    Again["run full forward pass again"]

    H --> Z --> Soft --> Dec
    Dec --> Greedy & Sample --> Tok --> Append --> Again
    Again -.-> H
```

Autoregressive generation over time:

```mermaid
sequenceDiagram
    participant U as User prompt
    participant M as Model (all layers)
    participant O as Output

    U->>M: "the cat sat"
    M->>O: predict → "on"
    Note over M: append "on"
    U->>M: "the cat sat on"
    M->>O: predict → "the"
    Note over M: append "the"
    U->>M: "the cat sat on the"
    M->>O: predict → "mat"
    Note over M: stop at EOS / max length
```

---

## 7. Backpropagation Through the Whole Pipeline

### Loss function — Cross-entropy
$$
L = -\sum_i y_i \log P_i = -\log P_c
$$
($c$ = index of correct token, $y$ = one-hot true label)

### Backward flow (overview)

```mermaid
flowchart TB
    L["Loss L = −log P_c"]
    dZ["∂L/∂z = P − y"]
    dH["∂L/∂h → into stack"]
    dWO["∂L/∂W_O, slice → ∂L/∂headᵢ"]
    dAV["∂L/∂A , ∂L/∂V"]
    dS["∂L/∂S → through softmax & scale"]
    dQK["∂L/∂Q , ∂L/∂K"]
    dW["∂L/∂W_Q, ∂L/∂W_K, ∂L/∂W_V"]
    dX["∂L/∂X → previous layer / embeddings"]

    L --> dZ --> dH --> dWO --> dAV --> dS --> dQK --> dW --> dX
```

### Step A — Gradient through softmax + cross-entropy
$$
\frac{\partial L}{\partial z_i} = P_i - y_i
$$
Clean result: push correct token's logit up, all others down proportional to their (wrong) probability mass.

*Derivation:* using softmax Jacobian $\frac{\partial P_i}{\partial z_k}=P_i(\delta_{ik}-P_k)$ and $\frac{\partial L}{\partial P_c}=-\frac{1}{P_c}$, chain rule collapses to $P_k - y_k$.

### Step B — Gradient into unembedding matrix
$$
\frac{\partial L}{\partial W_{vocab}} = h^T\frac{\partial L}{\partial z}, \qquad
\frac{\partial L}{\partial h} = \frac{\partial L}{\partial z}\,W_{vocab}^T
$$
$\frac{\partial L}{\partial h}$ seeds the backward pass into the transformer stack.

### Step C — Gradient through concat + $W_O$
Let $C = \text{Concat}(\text{head}_1,\dots,\text{head}_h)$, output $=CW_O$:
$$
\frac{\partial L}{\partial W_O} = C^T \frac{\partial L}{\partial \text{output}}, \qquad
\frac{\partial L}{\partial C} = \frac{\partial L}{\partial \text{output}}\,W_O^T
$$
Backward through concatenation = **slice the gradient back into per-head chunks**:
$$
\frac{\partial L}{\partial \text{head}_i} = \left[\frac{\partial L}{\partial C}\right]_{\text{columns of head } i}
$$

### Step D — Gradient through $\text{head}=AV$
$$
\frac{\partial L}{\partial V} = A^T \frac{\partial L}{\partial \text{head}}, \qquad
\frac{\partial L}{\partial A} = \frac{\partial L}{\partial \text{head}}\,V^T
$$

### Step E — Gradient through attention softmax (per row $i$)
$$
\frac{\partial L}{\partial S_{i,:}} = A_{i,:} \odot \left(\frac{\partial L}{\partial A_{i,:}} - \left(\frac{\partial L}{\partial A_{i,:}}\cdot A_{i,:}^T\right)\mathbf{1}\right)
$$
Same softmax backward pattern as Step A, applied per row (no cross-entropy pairing here, so it doesn't collapse as cleanly).

### Step F — Gradient through masking
Masked positions had $A_{ij}=0$ and contributed nothing forward → they get **zero gradient** backward too.

### Step G — Gradient through scaling
$$
\frac{\partial L}{\partial(QK^T)} = \frac{1}{\sqrt{d_k}}\cdot\frac{\partial L}{\partial S_{scaled}}
$$

### Step H — Gradient through $QK^T$
$$
\frac{\partial L}{\partial Q} = \frac{\partial L}{\partial M}\,K, \qquad
\frac{\partial L}{\partial K} = \left(\frac{\partial L}{\partial M}\right)^T Q
$$
(where $M=QK^T$)

### Step I — Gradient into projection weights
$$
\frac{\partial L}{\partial W_Q} = X^T\frac{\partial L}{\partial Q}, \qquad
\frac{\partial L}{\partial W_K} = X^T\frac{\partial L}{\partial K}, \qquad
\frac{\partial L}{\partial W_V} = X^T\frac{\partial L}{\partial V}
$$
These drive the weight update, e.g. $W_Q \leftarrow W_Q - \eta\frac{\partial L}{\partial W_Q}$ (SGD/Adam).

### Step J — Gradient back into input $X$
Since $X$ feeds Q, K, and V independently, gradients **sum** across all three paths:
$$
\frac{\partial L}{\partial X} = \frac{\partial L}{\partial Q}W_Q^T + \frac{\partial L}{\partial K}W_K^T + \frac{\partial L}{\partial V}W_V^T
$$
This flows into the previous layer (or the embedding table, if first layer).

```mermaid
flowchart TB
    dHead["∂L/∂head"]
    dA["∂L/∂A"]
    dV["∂L/∂V"]
    dS["∂L/∂S (softmaxᵀ)"]
    dM["∂L/∂(QKᵀ) via 1/√d_k"]
    dQ["∂L/∂Q"]
    dK["∂L/∂K"]
    dWQ["∂L/∂W_Q = Xᵀ ∂L/∂Q"]
    dWK["∂L/∂W_K"]
    dWV["∂L/∂W_V = Xᵀ ∂L/∂V"]
    dX["∂L/∂X = sum of Q,K,V paths"]

    dHead --> dA & dV
    dA --> dS --> dM --> dQ & dK
    dQ --> dWQ
    dK --> dWK
    dV --> dWV
    dQ & dK & dV --> dX
```

### Full backward chain summary
$$
\frac{\partial L}{\partial z}=P-y \;\to\; \frac{\partial L}{\partial h} \;\to\; \frac{\partial L}{\partial \text{head}_i} \;\to\; \frac{\partial L}{\partial A},\frac{\partial L}{\partial V} \;\to\; \frac{\partial L}{\partial S} \;\to\; \frac{\partial L}{\partial Q},\frac{\partial L}{\partial K} \;\to\; \frac{\partial L}{\partial W_Q},\frac{\partial L}{\partial W_K},\frac{\partial L}{\partial W_V} \;\to\; \frac{\partial L}{\partial X}
$$

> **Not yet covered:** backprop through LayerNorm and the feedforward (MLP) sublayer — needed for the complete picture of one full transformer block's backward pass.

---

## Quick-Reference Analogy (Birthday Party 🎂)

- **Query** = your sign ("I like dinosaurs!")
- **Key** = every kid's name tag describing themselves
- **Value** = what's inside each kid's backpack
- **Attention score → softmax** = handing out gold stars, then converting to percentages (pizza slices) that sum to 100%
- **Weighted sum with V** = taking a little/a lot from each kid's backpack based on their percentage, mixing into one final present
- **Multi-head** = playing the game again with different signs (dinosaurs, colors, games), each time getting a different present
- **Concatenation** = taping all the separate presents together in a row (not blending them)
- **$W_O$** = a grown-up who looks at the whole taped-together present and decides how to combine it sensibly
- **Backprop** = complaining backward from "I didn't like the final present" all the way down to "kids, rewrite your signs and tags next time"

```mermaid
flowchart LR
    Q["Query<br/>your sign"]
    K["Keys<br/>name tags"]
    Stars["scores → soft<br/>pizza slices"]
    V["Values<br/>backpacks"]
    Mix["weighted mix<br/>= one present"]
    Heads["× h heads<br/>different games"]
    Tape["concat = tape<br/>presents in a row"]
    Adult["W_O = grown-up<br/>combines them"]

    Q --> Stars
    K --> Stars
    Stars --> Mix
    V --> Mix
    Mix --> Heads --> Tape --> Adult
```
