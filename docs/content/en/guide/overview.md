# What this is

CNI is a **purely symbolic Chinese language understanding engine**.

You teach it knowledge in natural language; it answers in natural language. There is no neural network underneath—only a readable, auditable, extensible set of symbolic rules.

```
You say: "电脑是机器"
→ Engine records: isa(电脑, 机器)

You ask: "电脑是什么"
→ Engine answers: "电脑是机器"
```


## Why it exists

**Problem**

| Approach | Limitation |
| --- | --- |
| Regex / keyword matching | Narrow coverage; maintenance explodes with input variants |
| Traditional NLP (tokenize + POS + dependency) | Heavy toolchain; brittle generalization; rules hard to change |
| Large language models (LLMs) | Hallucination, opacity, high cost, hard to audit precisely |

**Goals**

CNI aims to be **controllable, explainable, extensible, and hallucination-free**.

- It only knows what you taught it—no guessing, no invention
- Every inference path is traceable (`--trace`)
- Grammar rules live in code; knowledge lives in files
- Runs offline in resource-constrained or privacy-sensitive settings


## Comparison

| Capability | Regex | Traditional NLP | LLM | **CNI** |
| --- | --- | --- | --- | --- |
| Understand NL structure | ✗ | △ (corpus-trained) | ✓ | ✓ (symbolic rules) |
| Auditable results | ✓ | △ | ✗ (black box) | ✓ (step-by-step) |
| Zero hallucination | ✓ | △ | ✗ | ✓ |
| Many constructions (ba/bei, questions, complexes…) | ✗ | △ | ✓ | ✓ (65 D-rules) |
| Typo / homophone correction | ✗ | △ | ✓ | ✓ (E-series) |
| Dialect / colloquial input | ✗ | ✗ | ✓ | ✓ (F/G-series) |
| No internet / no API cost | ✓ | ✓ | ✗ | ✓ |
| User-extensible lexicon | ✗ | △ | ✗ | ✓ (`user_dict.tm`) |
| Clear knowledge boundary | ✓ | △ | ✗ | ✓ |


## What you can do

- **Teach**: state facts in natural language; the engine parses and persists them
- **Ask**: query in natural language against stored facts
- **Complex syntax**: ba/bei constructions, cause/contrast/condition complexes, questions, etc.
- **Tolerant input**: typos, homophones, extra characters
- **Colloquial Chinese**: Cantonese order, fuzzy quantities, relative dates
- **Focus memory**: pronoun resolution via a dialogue focus stack
- **Inference**: `isa` inheritance chains (depth ≤ 2)
