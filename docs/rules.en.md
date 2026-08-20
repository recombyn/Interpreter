# Full System Rule Catalog (Table 1)

[中文](规则全表.md) · English

Ownership follows **Table 1 / Table 2** in [guide.en.md](guide.en.md).
This English page explains the catalog structure. The authoritative rule rows
(Chinese surface patterns) live in [规则全表.md](规则全表.md).

Table 1 count = **110** (D1–D65 + E + F41–50 + G + I1–3/I7–8/I10 + RO/WC/QP/MEM/REN).
Extras D66 / D67 / I11 / MEM4 are kernel extensions and do not change the 110 count.

## Sections

| Section | IDs | Topic |
| --- | --- | --- |
| 1. Syntactic decode | D1–D65 (+ D66–D67) | SVO, ba/bei, questions, complexes, deixis, modality, content |
| 2. Input repair | E1–E5 | Exact / homophone / typo / delete / never-insert |
| 3. Op routing | RO1–RO3 | Teach vs chat; no soft-fail on teach |
| 4. World consistency | WC1–WC3 | Ignore dupes; keep contradictions; precise drop |
| 5. Query priority | QP1–QP3 | Explicit > inferred > session > events; isa depth 2 |
| 6. Memory | MEM1–MEM3 (+ MEM4) | Focus stacks; durable events; reset; short-ask → D67 |
| 7. Render fallback | REN1–REN2 | Bare surface; empty-result phrase |
| 8. Word order | F41–F50 | Dialect order / aspect rewrite (algorithmic) |
| 9. Normalize | G1–G10 | Quantity / relative date / fuzzy defaults |
| 10. Social & punctuation | I1–I3 / I7–I8 / I10 (+ I11) | Greetings; punct collapse; poetry intercept |

## Content extras (D66–D67 only)

| ID | Role |
| --- | --- |
| D66 | Write `of(content, entity, text)`; content index + optional disk shard |
| D67 | Point lookup by entity (memory ∪ sharded store); pin entity/doc/topic |
| MEM4 | Short follow-up (`那呢` / `违法吗` …) with entity pin → expand to D67 |

There is **no D68 open-search rule**. Topic questions without a resolvable entity → REN2 / normal D miss. User docs sync to `.tm` + `.content/` for D67 scale.

## Counts

| Block | Count | Owner |
| --- | --- | --- |
| D1–D65 | 65 | Table 1 |
| E1–E5 | 5 | Table 1 |
| F41–F50 | 10 | Table 1 |
| G1–G10 | 10 | Table 1 |
| I1–I3 / I7–I8 / I10 | 6 | Table 1 |
| RO + WC + QP + MEM + REN | 14 | Table 1 |
| **Table 1 total** | **110** | |
| D66–D67 / I11 / MEM4 | 4 | extras (system) |
| F1–40 + H1–10 + I4–6 + I9 | 54 | Table 2 (user lexicon) |

See [规则全表.md](规则全表.md) for every rule’s pattern and action.
