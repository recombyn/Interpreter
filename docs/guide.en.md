# CNI Usage & Design Guide

[中文](指南.md) · English

A symbolic rule engine: natural language in, facts out. **No LLM.**

Facts are stored as: `isa` / `located` / `has` / `event` + `of(role…)`.  
The kernel does **not** rewrite `located`/`has` into `of(located,…)` / `of(has,…)`.

**Keep / drop classification follows the tables below.** Rule-by-rule Table 1 → [rules.en.md](rules.en.md) / [规则全表.md](规则全表.md).

## Table 1: Hard-coded system rules (110)

| Series | Range | Core logic | Why keep |
| --- | --- | --- | --- |
| **D** | D1–D65 | Syntax: SVO, ba/bei, causative/serial, existential, complexes, questions, negation, ellipsis, deixis, modality (65) | Sentence-splitting algorithm; users cannot recreate |
| **E** | E1–E5 | Input repair: exact match, homophone pin, typo replace, multi-char delete (never insert missing chars) | Edit-distance / pinyin algorithms |
| **F** | F41–F50 | Dialect order rewrite (e.g. “食先”→“先食”, “有V”→“曾V过”) — 10 rules | Regex shift algorithms, not lookup tables |
| **G** | G1–G10 | Entity normalize (“10w”→“100000”, “明天”→ absolute date, “几十”→“30”, …) | Math + system timestamp injection |
| **I** | I1–I3 | Social intercept (“谢谢/你好/再见” fixed replies; skip D) | Control-flow decisions |
| **I** | I7–I8 | Punctuation collapse (“!!!”→“!”, “??”→“?”) | Text cleaning |
| **I** | I10 | One-char completion (“哦”→“我知道了”; fill `other` as agent) | Default subject fill; avoid deadlock |
| **System** | RO1–RO3 | Op routing: teach trigger, default chat, no soft-fail | Engine behavior |
| **System** | WC1–WC3 | World consistency: ignore dupes, keep contradictions, precise drop | Data management |
| **System** | QP1–QP3 | Query priority: explicit > inferred > session > log; isa depth 2; WH roles | Query ranking |
| **System** | MEM1–MEM3 | Memory: focus stack len 5; events durable / session temp; reset clears | Memory management |
| **System** | REN1–REN2 | Render fallback: bare surface if no template; empty-result phrase | Output fallback |

> **Implementation extras** (in system, not changing the 110 count): D66 / D67 (content store/fetch), I11 (poetry intercept). See the full rule catalog.

## Table 2: Removed — owned by user lexicon (54)

| Series | Range | Former content | How users own it now |
| --- | --- | --- | --- |
| **F** | F1–F40 | Net slang expand, dialect rewrite (40) | Edit `user_dict.tm`: `source → standard` |
| **H** | H1–H10 | CN–EN mix normalize (check→检查, …) (10) | Same; user EN→ZH maps |
| **I** | I4–I6 | Emoji→mood (3) | Add emoji→mood maps in `user_dict.tm` |
| **I** | I9 | “好吧”→“接受” | User mood-word maps |

## Summary

- **Keep (hard-coded)**: D / E / F41–50 / G / I1–3 / I7–8 / I10 / system rules — **110**, in the kernel.
- **Drop (to user)**: F1–40 + H1–10 + I4–6 + I9 — **54**, via `knowledge/user/user_dict.tm`.

Implement **only Table 1’s 110** (plus agreed D66/D67/I11); Table 2 is entirely user-maintained.

Pipeline:

```
input → E → user_dict(Table 2) → F41–50 → G → I(Table 1) → D → kernel(RO/WC/QP/MEM/REN) → output
```

## Architecture

```
User input
    │
    ▼
┌─────────── RO routing ───────────┐
│  教/记住/学习/记 or teach?        │
│   yes → hear (write)  no → turn (read)│
└──────────────┬───────────────────┘
               ▼
┌─────────── Preprocess ───────────┐
│  E → user_dict → F41–50 → G → I  │
│  I hit → spoken reply, stop      │
└──────────────┬───────────────────┘
               ▼
┌─────────── D decode ─────────────┐
│  D66/D67 literal early-exit; else lex+D│
│  write tell / read find·yesno    │
└──────────────┬───────────────────┘
               ▼
┌─────────── World ────────────────┐
│  isa / located / has / event…    │
│  inference depth ≤ 2             │
└──────────────┬───────────────────┘
               ▼
┌─────────── REN output ───────────┐
│  form/lex → NL                   │
│  REN1 bare surface; REN2 empty phrase│
└──────────────────────────────────┘
```

## Fact shape

```text
isa(电脑, 机器)
located(电脑, 桌上)          # native predicate
has(我, 电脑)                # native predicate
of(kind, e.1, invent)        # event roles still use of
of(content, 静夜思, 床前明月光)
```

## Layout

```
src/cni/
  data/world/   # bundled: lang / base / rules / lex / form
  …             # Table 1 algorithms
knowledge/
  user/         # Table 2: user_dict.tm
runtime/        # optional persisted taught facts
docs/rules.en.md / 规则全表.md
docs/guide.en.md / 指南.md
```

| Want to change | Put it here |
|--------|------|
| Table 2 slang / dialect / CN–EN / emoji | `knowledge/user/user_dict.tm` |
| Dialogue facts | `teach` / `教…` |
| New verbs for D | `src/cni/data/world/lex.*.tm` (careful) |
| Answer phrasing | `src/cni/data/world/form.tm` |

## Adding knowledge

```bash
python -m cni teach "电脑是机器"
python -m cni reply "电脑是什么"
python -m cni teach "静夜思的内容是床前明月光"
python -m cni reply "静夜思的内容是什么"
```

Table 2: edit `knowledge/user/user_dict.tm` as `map source standard`.  
Do not “patch” Table 1 algorithms via the lexicon; colloquial maps belong only in Table 2.

## Install & commands

```bash
python -m pip install -e ".[dev]"
python -m cni teach "电脑是机器"
python -m cni reply "电脑是什么"
python -m cni repl
python -m pytest
python -m cni reply "电脑是什么" --trace
```

## Boundaries

- No LLM; untaught world knowledge is never guessed
- Table 1 hard-coded / Table 2 user-owned — do not mix
- Chat path does not write open-domain facts
- On disk: `isa` / `located` / `has` / `of(role…)`; no undeclared predicates
- I11: no poetry appreciation
