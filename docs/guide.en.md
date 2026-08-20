# CNI Usage & Design Guide

[中文](指南.md) · English

A symbolic rule engine: natural language in, facts out. **No LLM.**

Facts are stored as: `isa` / `located` / `has` / `event` + `of(role…)`.  
The kernel does **not** rewrite `located`/`has` into `of(located,…)` / `of(has,…)`.

**Rule ownership follows the tables below.** Rule-by-rule Table 1 → [rules.en.md](rules.en.md) / [规则全表.md](规则全表.md).

## Table 1: Kernel rules (110)

| Series | Range | Core logic | Notes |
| --- | --- | --- | --- |
| **D** | D1–D65 | Syntax: SVO, ba/bei, causative/serial, existential, complexes, questions, negation, ellipsis, deixis, modality (65) | Sentence-splitting; in kernel |
| **E** | E1–E5 | Input repair: exact match, homophone pin, typo replace, multi-char delete (never insert missing chars) | Edit-distance / pinyin; in kernel |
| **F** | F41–F50 | Dialect order rewrite (e.g. “食先”→“先食”, “有V”→“曾V过”) — 10 rules | Regex shift; in kernel |
| **G** | G1–G10 | Entity normalize (“10w”→“100000”, “明天”→ absolute date, “几十”→“30”, …) | Math + timestamp; in kernel |
| **I** | I1–I3 | Social intercept (“谢谢/你好/再见” fixed replies; skip D) | Control-flow; EN greetings via user lexicon |
| **I** | I7–I8 | Punctuation collapse (“!!!”→“!”, “??”→“?”) | Text cleaning; in kernel |
| **I** | I10 | One-char completion (“哦”→“我知道了”; fill `other` as agent) | Default subject fill; in kernel |
| **System** | RO1–RO3 | Op routing: teach trigger, default chat, no soft-fail | Engine behavior |
| **System** | WC1–WC3 | World consistency: ignore dupes, keep contradictions, precise drop | Data management |
| **System** | QP1–QP3 | Query priority: explicit > inferred > session > log; isa depth 2; WH roles | Query ranking |
| **System** | MEM1–MEM3 | Memory: focus stack len 5; events durable / session temp; reset clears | Memory management |
| **System** | REN1–REN2 | Render fallback: bare surface if no template; empty-result phrase | Output fallback |

> **Extensions** (in kernel; do not change the 110 count): D66 / D67 (content), D69 (threshold judge), MEM4 (short-ask → D67), I11 (poetry intercept). See the full rule catalog.

## Table 2: User lexicon (54)

Lookup mappings (historical series IDs); maintained in `knowledge/user/user_dict.tm` (`map source standard`).

| Series | Range | Content | Where |
| --- | --- | --- | --- |
| **F** | F1–F40 | Net slang, dialect words (40) | `user_dict.tm` |
| **H** | H1–H10 | CN–EN mix (check→检查, …) (10) | Same; EN→ZH before I/D |
| **I** | I4–I6 | Emoji→mood (3) | `user_dict.tm` |
| **I** | I9 | “好吧”→“接受” | `user_dict.tm` |

## Split & pipeline

- **Table 1 (kernel)**: D / E / F41–50 / G / I1–3 / I7–8 / I10 / RO·WC·QP·MEM·REN — **110**, plus extensions D66/D67/D69/MEM4/I11.
- **Table 2 (user)**: F1–40 + H1–10 + I4–6 + I9 — **54**, in `knowledge/user/user_dict.tm`.

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
│  D66/D67 literal early-exit; MEM4 short-ask→D67; else lex+D│
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
# D67: O(1) by entity (memory index ∪ knowledge/user/.content shards)
# MEM4: short follow-up + entity pin → D67 (no open-search rule)
```

## Layout

```
src/cni/
  data/world/   # bundled: lang / base / rules / lex / form
  knowledge/    # content_store: sharded bodies + term→entity index
  …             # Table 1 algorithms
knowledge/
  user/         # user_dict.tm, form.tm, config.tm, rules.tm, limits.tm
                # *.text/*.md → *.tm + .content/
runtime/        # optional persisted taught facts
docs/rules.en.md / 规则全表.md
docs/guide.en.md / 指南.md
```

| Path | Content |
| --- | --- |
| `knowledge/user/user_dict.tm` | Table 2 lexicon (`map`) |
| `knowledge/user/*.text` etc. | Long-doc source; `sync_user_docs` → sibling `.tm` + `.content/` |
| `knowledge/user/form.tm` / `config.tm` | Reply overrides / switches (`reply_mode`) |
| `knowledge/user/rules.tm` · `limits.tm` | D69 declarations and comparable facts |
| `src/cni/data/world/form.tm` · `lex.*.tm` | Bundled templates and lexemes |
| `teach` / `教…` | Dialogue writes into the world |

## User-layer `.tm` syntax

[中文](指南.md#用户层-tm-语法)

### Symbol table

| Symbol / line | Where | Meaning |
| --- | --- | --- |
| `# …` | most `.tm` | Comment |
| blank line | any | Ignored |
| `! name : e` | memory world | Register entity |
| `+ isa(A, B)` | memory world | A is-a B |
| `+ has(A, B)` | memory world | A has B |
| `+ located(A, B)` | memory world | A at B |
| `+ of(key, …)` | memory world | Slot fact |
| `rule …` | **`rules.tm` only** | D69 judgment |
| `tier …` | **`rules.tm` only** | Tiered cap |
| `map a b` | **`user_dict.tm` only** | Rewrite |
| `out name surface` | **`form.tm` only** | Reply override |
| config keys | **`config.tm` only** | Switches |
| name `（空行）` | synced `*.tm` | Blank-line placeholder |

Memory world: `!` then `+`. `rule` / `map` / `out` are other file formats.

### Memory world (`!` / `+`)

Shared by `劳动法.tm`, `labor_law.tm`, `limits.tm`, and taught facts. Supported predicates only (incl. `上限` / `下限` / `许可` / `出处` / `单位`).

### `*.text` and sibling `.tm`

| File | Role |
| --- | --- |
| `*.text` (e.g. `劳动法.text`) | Line-oriented source |
| sibling `.tm` | From `python -m cni.tools.sync_user_docs` (`--force` optional); D67 line recall |

- Entities: `第N行` and `{doc}第N行`  
- Blank source lines → placeholder `（空行）`  
- Bodies in `.content/` shards; `.tm` holds entities/index  

### `labor_law.tm`

Optional small `isa` / `has` / `content` graph (`memory_path`). Distinct from full-line `劳动法.tm`. Thresholds: `rules.tm` + `limits.tm`.

### `rules.tm` (D69)

Not scanned as ordinary world facts; read by the judge.

```tm
rule 试用期 le 上限 合法吗|合规吗|可以吗
tier 试用期 3 12 1
```

`limits.tm` uses memory-world syntax. Optional: `python -m cni.tools.compile_limits --write`.

## Dialogue memory (session pins, not the knowledge base)

Principle: **pin “which doc / entity / topic we’re on”, and let short asks attach to those pins; knowledge stays in the world + content store—session only does deixis and disambiguation.**

| Pin | Meaning | Used by |
| --- | --- | --- |
| `doc_focus` | Current doc stem | Bare `第N行` → prefer `{doc}第N行` in D67 |
| `entity_focus` | Current entity | 这/那/他; MEM4 short-ask → D67 |
| `topic_focus` | Recent content terms | Context marks (not a search index) |
| `event_focus` | Event `e.n` | Event deixis |

No D68 open-search rule: without a resolvable entity → REN2 / normal miss.

## Decode mitigations (D-layer limits)

Template matching is not full syntax. Practical knobs:

| Item | Behavior |
| --- | --- |
| Ambiguity | `config.tm` `ambig_mode first\|clarify\|warn` (AMB1) |
| Parataxis | Comma clauses → `cause` / `before` (D37y / D40y) |
| Threshold judgment | **D69**: `rules.tm` + `limits.tm`; `compile_limits` extracts caps; `D69.ask` for missing value; `in` for enums |
| Coref | MEM5: `他/她` prefers `last_patient` |
| Negation write | Teach of `不/没…` does not store a negated event; queries use D57/D58 |
| MEM4 | Only very short follow-ups (≤4 chars or listed patterns); full polars like「电脑是机器吗」 stay D21 |

## Examples

```bash
python -m cni teach "电脑是机器"
python -m cni reply "电脑是什么"
python -m cni teach "静夜思的内容是床前明月光"
python -m cni reply "静夜思的内容是什么"
python -m cni.tools.sync_user_docs --force
python -m cni reply "第20行的内容是什么"
python -m cni reply "那呢"   # MEM4 → same entity via D67
```

Table 2 maps: `knowledge/user/user_dict.tm` (`map source standard`).

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
- Table 1 kernel / Table 2 user lexicon — do not mix
- Chat path does not write open-domain facts
- On disk: `isa` / `located` / `has` / `of(role…)`; no undeclared predicates
- I11: no poetry appreciation
