<div align="center">

**English** · [中文](README.zh.md)

# CNI — Concept Network Interpreter

</div>

> Natural language → symbolic rule engine → world facts. **No LLM. No regex black box.**

## What this is

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

| Cap. | &emsp;&emsp;Regex&emsp;&emsp; | &emsp;Traditional NLP&emsp; | &emsp;&emsp;LLM&emsp;&emsp; | &emsp;**CNI**&emsp; |
| --- | :---: | :---: | :---: | :---: |
| NL structure | &emsp;✗&emsp; | △ (corpus) | &emsp;✓&emsp; | ✓ (rules) |
| Auditable | &emsp;✓&emsp; | &emsp;△&emsp; | ✗ (black box) | ✓ (trace) |
| Zero hallucination | &emsp;✓&emsp; | &emsp;△&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; |
| Constructions | &emsp;✗&emsp; | &emsp;△&emsp; | &emsp;✓&emsp; | ✓ (65 D) |
| Typo / homophone | &emsp;✗&emsp; | &emsp;△&emsp; | &emsp;✓&emsp; | ✓ (E) |
| Dialect / colloquial | &emsp;✗&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; | ✓ (F/G) |
| Offline / no API | &emsp;✓&emsp; | &emsp;✓&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; |
| Extensible lexicon | &emsp;✗&emsp; | &emsp;△&emsp; | &emsp;✗&emsp; | ✓ (`user_dict`) |
| Clear boundary | &emsp;✓&emsp; | &emsp;△&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; |

## Design

**Pipeline**

```
Input
 │
 ▼
E (fix) → user_dict → F41–50 (word order) → G (quantity/time) → I (social intercept)
 │                                                                      │
 │ (pass-through)                                                       │ (hit → reply)
 ▼
D (syntactic decode: 65 rules)
 │
 ▼
Kernel (RO routing / WC consistency / QP query / MEM memory / REN render)
 │
 ▼
Output (natural language)
```

**Fact shape (on disk)**

```
isa(电脑, 机器)              # class membership
located(电脑, 桌上)          # location
has(我, 电脑)                # possession
of(kind, e.1, 发明)          # event role
of(content, 静夜思, 床前明月光) # content
```

**Rule layers**

| Layer | Content | Count | Owner |
| --- | --- | :---: | --- |
| **Table 1 (kernel)** | Syntax / fix / order / time / social core algorithms | 110 | Engine kernel |
| **Table 2 (user)** | Abbreviations, dialect, CN–EN mix, emoji maps, etc. | 54 | `user_dict.tm` |

Table 1 is algorithm; Table 2 is lexicon maps.

## What you can do

- **Teach**: state facts in natural language; the engine parses and persists them
- **Ask**: query in natural language against stored facts
- **Complex syntax**: ba/bei constructions, cause/contrast/condition complexes, questions, etc.
- **Tolerant input**: typos, homophones, extra characters
- **Colloquial Chinese**: Cantonese order, fuzzy quantities, relative dates
- **Focus memory**: pronoun resolution via a dialogue focus stack
- **Inference**: `isa` inheritance chains (depth ≤ 2)

## Quick start

```bash
pip install -e ".[dev]"

# Teach
python -m cni teach "电脑是机器"
python -m cni teach "静夜思的内容是床前明月光"

# Query
python -m cni reply "电脑是什么"
python -m cni reply "静夜思的内容是什么"

# Interactive
python -m cni repl

# Debug (show inference chain)
python -m cni reply "电脑是什么" --trace

# Tests
python -m pytest
```

In `repl`, lines starting with `教|记住|学习|记` write to the world; everything else is read-only query.

## Custom lexicon

Edit `knowledge/user/user_dict.tm`:

```
map yyds 永远的神
map check 检查
map 偶 我
```

## Layout

```
src/cni/
  data/world/  # bundled world data (lang/base/lex/form/rules)
knowledge/
  user/        # user lexicon (Table 2)
docs/
  rules.en.md / 规则全表.md
  guide.en.md / 指南.md
```

## Boundaries

- Untaught facts are **never guessed**; reply is “我不了解这个信息”
- No open-domain chit-chat writes (non-teach paths do not persist)
- No poetry appreciation (I11 intercept)
- `isa` chain depth capped at 2; no full-graph walk

## Docs

- **Rule catalog**: [docs/rules.en.md](docs/rules.en.md) (Chinese patterns: [规则全表.md](docs/规则全表.md))
- **Architecture & guide**: [docs/guide.en.md](docs/guide.en.md) (includes **user-layer `.tm` syntax**: `!` / `+`, labor-law file split, D69 `rules`/`limits`)
- **中文**: [README.zh.md](README.zh.md) · [docs/指南.md](docs/指南.md)
