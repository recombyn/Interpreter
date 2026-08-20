<div align="center">

# Full System Rule Catalog (Table 1)

<p>
  <a href="./规则全表.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
  <a href="./rules.en.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
</p>

</div>

Ownership follows **Table 1 / Table 2** in [guide.en.md](guide.en.md).
This English page explains the catalog structure. The authoritative rule rows
(Chinese surface patterns) live in [规则全表.md](规则全表.md).

Table 1 count = **110** (D1–D65 + E + F41–50 + G + I1–3/I7–8/I10 + RO/WC/QP/MEM/REN).
Extras D66 / D67 / D69 / I11 / MEM4 are kernel extensions and do not change the 110 count.
**D68** is retired as a standalone ID: short-ask pinning → **MEM4→D67**; threshold/compliance → **D69** (no open-search rule).

## Sections

| Section                  | IDs                         | Topic                                                                         |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------------ |
| 1. Syntactic decode      | D1–D65 (+ D66–D67 / D69)    | SVO, ba/bei, questions, complexes, deixis, modality, content, threshold judge |
| 2. Input repair          | E1–E5                       | Exact / homophone / typo / delete / never-insert                              |
| 3. Op routing            | RO1–RO3                     | Teach vs chat; no soft-fail on teach                                          |
| 4. World consistency     | WC1–WC3                     | Ignore dupes; keep contradictions; precise drop                               |
| 5. Query priority        | QP1–QP3                     | Explicit > inferred > session > events; isa depth 2                           |
| 6. Memory                | MEM1–MEM3 (+ MEM4)          | Focus stacks; durable events; reset; short-ask → D67                          |
| 7. Render fallback       | REN1–REN2                   | Bare surface; empty-result phrase                                             |
| 8. Word order            | F41–F50                     | Dialect order / aspect rewrite (algorithmic)                                  |
| 9. Normalize             | G1–G10                      | Quantity / relative date / fuzzy defaults                                     |
| 10. Social & punctuation | I1–I3 / I7–I8 / I10 (+ I11) | Greetings; punct collapse; poetry intercept                                   |

## Content & judgment extras (D66–D67 / D69 / MEM4)

| ID   | Role                                                                                                            |
| ----- | ---------------------------------------------------------------------------------------------------------------- |
| D66  | Write `of(content, entity, text)`; content index + optional disk shard                                          |
| D67  | Point lookup by entity (memory ∪ sharded store); pin entity/doc/topic; O(1) content                             |
| D68  | **Retired / split** — not a live rule. Short-ask → MEM4; compliance → D69. No open full-text search.            |
| D69  | Threshold / enum judge via user `rules.tm` (`rule`/`tier` + triggers) + `limits.tm`; `D69.ask` if value missing |
| MEM4 | Short follow-up (`那呢` / `违法吗` …) with entity pin → expand to D67                                                |

There is **no D68 open-search rule**. Triggers in `rules.tm` (e.g. `合法吗|合规吗`) are examples users may extend; matching is by rule pattern, not an unbounded lexicon. User docs sync to `.tm` + `.content/` for D67 scale. Untaught world knowledge is never guessed.

## Counts

| Block                      | Count   | Owner                              |
| --------------------------- | -------- | ----------------------------------- |
| D1–D65                     | 65      | Table 1                            |
| E1–E5                      | 5       | Table 1                            |
| F41–F50                    | 10      | Table 1                            |
| G1–G10                     | 10      | Table 1                            |
| I1–I3 / I7–I8 / I10        | 6       | Table 1                            |
| RO + WC + QP + MEM + REN   | 14      | Table 1                            |
| **Table 1 total**          | **110** |                                    |
| D66–D67 / D69 / MEM4 / I11 | 5       | extras (system); D68 not allocated |
| F1–40 + H1–10 + I4–6 + I9  | 54      | Table 2 (user lexicon)             |

See [规则全表.md](规则全表.md) for every rule’s pattern and action.
