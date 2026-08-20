# Rule layers

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
