<div align="center">

[中文](指南.md) · **English**

# CNI Usage & Design Guide

</div>

A symbolic rule engine: natural language in, facts out. **No LLM.**

Facts are stored as: `isa` / `located` / `has` / `event` + `of(role…)`.  
The kernel does **not** rewrite `located`/`has` into `of(located,…)` / `of(has,…)`.

**Rule ownership follows the tables below.** Rule-by-rule Table 1 → [rules.en.md](rules.en.md) / [规则全表.md](规则全表.md).

## Table 1: Kernel rules (110)

<table width="100%">
<thead>
<tr>
<th width="12%" align="left">Series</th>
<th width="14%" align="center">Range</th>
<th width="50%" align="left">Core logic</th>
<th width="24%" align="left">Notes</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left"><strong>D</strong></td>
<td align="center">D1–D65</td>
<td align="left">Syntax: SVO, ba/bei, causative/serial, existential, complexes, questions, negation, ellipsis, deixis, modality (65)</td>
<td align="left">Sentence-splitting; in kernel</td>
</tr>
<tr>
<td align="left"><strong>E</strong></td>
<td align="center">E1–E5</td>
<td align="left">Input repair: exact match, homophone pin, typo replace, multi-char delete (never insert missing chars)</td>
<td align="left">Edit-distance / pinyin; in kernel</td>
</tr>
<tr>
<td align="left"><strong>F</strong></td>
<td align="center">F41–F50</td>
<td align="left">Dialect order rewrite (e.g. “食先”→“先食”, “有V”→“曾V过”) — 10 rules</td>
<td align="left">Regex shift; in kernel</td>
</tr>
<tr>
<td align="left"><strong>G</strong></td>
<td align="center">G1–G10</td>
<td align="left">Entity normalize (“10w”→“100000”, “明天”→ absolute date, “几十”→“30”, …)</td>
<td align="left">Math + timestamp; in kernel</td>
</tr>
<tr>
<td align="left"><strong>I</strong></td>
<td align="center">I1–I3</td>
<td align="left">Social intercept (“谢谢/你好/再见” fixed replies; skip D)</td>
<td align="left">Control-flow; EN greetings via user lexicon</td>
</tr>
<tr>
<td align="left"><strong>I</strong></td>
<td align="center">I7–I8</td>
<td align="left">Punctuation collapse (“!!!”→“!”, “??”→“?”)</td>
<td align="left">Text cleaning; in kernel</td>
</tr>
<tr>
<td align="left"><strong>I</strong></td>
<td align="center">I10</td>
<td align="left">One-char completion (“哦”→“我知道了”; fill `other` as agent)</td>
<td align="left">Default subject fill; in kernel</td>
</tr>
<tr>
<td align="left"><strong>System</strong></td>
<td align="center">RO1–RO3</td>
<td align="left">Op routing: teach trigger, default chat, no soft-fail</td>
<td align="left">Engine behavior</td>
</tr>
<tr>
<td align="left"><strong>System</strong></td>
<td align="center">WC1–WC3</td>
<td align="left">World consistency: ignore dupes, keep contradictions, precise drop</td>
<td align="left">Data management</td>
</tr>
<tr>
<td align="left"><strong>System</strong></td>
<td align="center">QP1–QP3</td>
<td align="left">Query priority: explicit > inferred > session > log; isa depth 2; WH roles</td>
<td align="left">Query ranking</td>
</tr>
<tr>
<td align="left"><strong>System</strong></td>
<td align="left">MEM1–MEM3</td>
<td align="left">Memory: focus stack len 5; events durable / session temp; reset clears</td>
<td align="left">Memory management</td>
</tr>
<tr>
<td align="left"><strong>System</strong></td>
<td align="left">REN1–REN2</td>
<td align="left">Render fallback: bare surface if no template; empty-result phrase</td>
<td align="left">Output fallback</td>
</tr>
</tbody>
</table>

> **Extensions** (in kernel; do not change the 110 count): D66 / D67 (content), D69 (threshold judge), MEM4 (short-ask → D67), I11 (poetry intercept). See the full rule catalog.

## Table 2: User lexicon (54)

Lookup mappings (historical series IDs); maintained in `knowledge/user/user_dict.tm` (`map source standard`).

<table width="100%">
<thead>
<tr>
<th width="12%" align="left">Series</th>
<th width="14%" align="center">Range</th>
<th width="50%" align="left">Content</th>
<th width="24%" align="left">Where</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left"><strong>F</strong></td>
<td align="center">F1–F40</td>
<td align="left">Net slang, dialect words (40)</td>
<td align="left">`user_dict.tm`</td>
</tr>
<tr>
<td align="left"><strong>H</strong></td>
<td align="center">H1–H10</td>
<td align="left">CN–EN mix (check→检查, …) (10)</td>
<td align="left">Same; EN→ZH before I/D</td>
</tr>
<tr>
<td align="left"><strong>I</strong></td>
<td align="center">I4–I6</td>
<td align="left">Emoji→mood (3)</td>
<td align="left">`user_dict.tm`</td>
</tr>
<tr>
<td align="left"><strong>I</strong></td>
<td align="center">I9</td>
<td align="left">“好吧”→“接受”</td>
<td align="left">`user_dict.tm`</td>
</tr>
</tbody>
</table>

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
  user/         # user_dict / form / config; domain folders e.g. 劳动法/
                # *.text → sync; limits / article.maps — see table below
runtime/        # optional persisted taught facts
docs/rules.en.md / 规则全表.md
docs/guide.en.md / 指南.md
```

<table width="100%">
<thead>
<tr>
<th width="32%" align="left">Path</th>
<th width="68%" align="left">Content</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">`knowledge/user/user_dict.tm`</td>
<td align="left">Table 2 lexicon (`map`); also merges `*.maps.tm`</td>
</tr>
<tr>
<td align="left">`knowledge/user/*.text` etc.</td>
<td align="left">Long-doc source; may live under domain folders</td>
</tr>
<tr>
<td align="left">`knowledge/user/form.tm` / `config.tm`</td>
<td align="left">Reply overrides / switches (`reply_mode`)</td>
</tr>
<tr>
<td align="left">`knowledge/user/rules.tm`</td>
<td align="left">Optional global D69 stub</td>
</tr>
<tr>
<td align="left">`knowledge/user/劳动法/rules.tm` · `limits.tm` · `article.maps.tm`</td>
<td align="left">Domain judgment / caps / article→line maps</td>
</tr>
<tr>
<td align="left">`src/cni/data/world/form.tm` · `lex.*.tm`</td>
<td align="left">Bundled templates and lexemes</td>
</tr>
<tr>
<td align="left">`teach` / `教…`</td>
<td align="left">Dialogue writes into the world</td>
</tr>
</tbody>
</table>

### Generated vs hand-written `.tm`

<table width="100%">
<thead>
<tr>
<th width="22%" align="left">Artifact</th>
<th width="50%" align="left">How</th>
<th width="28%" align="left">Automation</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">`{doc}.tm` + `.content/`</td>
<td align="left">`python -m cni.tools.sync_user_docs` (`--force` ok)</td>
<td align="left"><strong>Full</strong>: line entities + shards for D66/D67</td>
</tr>
<tr>
<td align="left">`劳动法/article.maps.tm`</td>
<td align="left">`python -m cni.tools.compile_labor_articles --write`</td>
<td align="left"><strong>Full</strong>: `map 第八条 → 第N行`; merged into lexicon</td>
</tr>
<tr>
<td align="left">Caps in `limits.tm`</td>
<td align="left">`python -m cni.tools.compile_limits --write`</td>
<td align="left"><strong>Semi</strong>: scrape 「不得超过/不少于…」 using `rules.tm` topics; editable</td>
</tr>
<tr>
<td align="left">`许可` / `书面约定` in `limits.tm`</td>
<td align="left">Same tool may append a fixed sample block; or hand-write</td>
<td align="left"><strong>Not</strong> reliably extracted from statute text</td>
</tr>
<tr>
<td align="left">`**/rules.tm` (`rule` / `tier`)</td>
<td align="left">Hand-write</td>
<td align="left"><strong>Never auto</strong>: judgment shape + triggers</td>
</tr>
<tr>
<td align="left">`user_dict.tm` / `form.tm` / `config.tm`</td>
<td align="left">Hand-write</td>
<td align="left"><strong>Never auto</strong> (aside from `*.maps.tm`)</td>
</tr>
<tr>
<td align="left">`labor_law.tm`</td>
<td align="left">Hand-write (optional mini-graph)</td>
<td align="left"><strong>Never auto</strong>; distinct from line-index `劳动法.tm`</td>
</tr>
</tbody>
</table>

Suggested order for labor law: drop `劳动法.text` → `sync_user_docs` → `compile_labor_articles --write` → author `rules.tm` → `compile_limits --write` → patch enum facts as needed. D69 merges `knowledge/user/**/rules.tm` (not world facts); `limits.tm` loads into the world.

## User-layer `.tm` syntax

[中文](指南.md#用户层-tm-语法)

### Symbol table

<table width="100%">
<thead>
<tr>
<th width="28%" align="left">Symbol / line</th>
<th width="36%" align="left">Where</th>
<th width="36%" align="left">Meaning</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">`# …`</td>
<td align="left">most `.tm`</td>
<td align="left">Comment</td>
</tr>
<tr>
<td align="left">blank line</td>
<td align="left">any</td>
<td align="left">Ignored</td>
</tr>
<tr>
<td align="left">`! name : e`</td>
<td align="left">memory world</td>
<td align="left">Register entity</td>
</tr>
<tr>
<td align="left">`+ isa(A, B)`</td>
<td align="left">memory world</td>
<td align="left">A is-a B</td>
</tr>
<tr>
<td align="left">`+ has(A, B)`</td>
<td align="left">memory world</td>
<td align="left">A has B</td>
</tr>
<tr>
<td align="left">`+ located(A, B)`</td>
<td align="left">memory world</td>
<td align="left">A at B</td>
</tr>
<tr>
<td align="left">`+ of(key, …)`</td>
<td align="left">memory world</td>
<td align="left">Slot fact</td>
</tr>
<tr>
<td align="left">`rule …`</td>
<td align="left"><strong>`rules.tm` only</strong></td>
<td align="left">D69 judgment</td>
</tr>
<tr>
<td align="left">`tier …`</td>
<td align="left"><strong>`rules.tm` only</strong></td>
<td align="left">Tiered cap</td>
</tr>
<tr>
<td align="left">`map a b`</td>
<td align="left"><strong>`user_dict.tm` only</strong></td>
<td align="left">Rewrite</td>
</tr>
<tr>
<td align="left">`out name surface`</td>
<td align="left"><strong>`form.tm` only</strong></td>
<td align="left">Reply override</td>
</tr>
<tr>
<td align="left">config keys</td>
<td align="left"><strong>`config.tm` only</strong></td>
<td align="left">Switches</td>
</tr>
<tr>
<td align="left">name `（空行）`</td>
<td align="left">synced `*.tm`</td>
<td align="left">Blank-line placeholder</td>
</tr>
</tbody>
</table>

Memory world: `!` then `+`. `rule` / `map` / `out` are other file formats.

### Memory world (`!` / `+`)

Shared by `劳动法.tm`, `labor_law.tm`, `limits.tm`, and taught facts. Supported predicates only (incl. `上限` / `下限` / `许可` / `出处` / `单位`).

### `*.text` and sibling `.tm`

<table width="100%">
<thead>
<tr>
<th width="32%" align="left">File</th>
<th width="68%" align="left">Role</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">`*.text` (e.g. `劳动法.text`)</td>
<td align="left">Line-oriented source</td>
</tr>
<tr>
<td align="left">sibling `.tm`</td>
<td align="left">From `python -m cni.tools.sync_user_docs` (`--force` optional); D67 line recall</td>
</tr>
</tbody>
</table>

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

`limits.tm` uses memory-world syntax. See **Generated vs hand-written** above for what `--write` can and cannot produce.

## Dialogue memory (session pins, not the knowledge base)

Principle: **pin “which doc / entity / topic we’re on”, and let short asks attach to those pins; knowledge stays in the world + content store—session only does deixis and disambiguation.**

<table width="100%">
<thead>
<tr>
<th width="22%" align="left">Pin</th>
<th width="40%" align="left">Meaning</th>
<th width="38%" align="left">Used by</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">`doc_focus`</td>
<td align="left">Current doc stem</td>
<td align="left">Bare `第N行` → prefer `{doc}第N行` in D67</td>
</tr>
<tr>
<td align="left">`entity_focus`</td>
<td align="left">Current entity</td>
<td align="left">这/那/他; MEM4 short-ask → D67</td>
</tr>
<tr>
<td align="left">`topic_focus`</td>
<td align="left">Recent content terms</td>
<td align="left">Context marks (not a search index)</td>
</tr>
<tr>
<td align="left">`event_focus`</td>
<td align="left">Event `e.n`</td>
<td align="left">Event deixis</td>
</tr>
</tbody>
</table>

No D68 open-search rule: without a resolvable entity → REN2 / normal miss.

## Decode mitigations (D-layer limits)

Template matching is not full syntax. Practical knobs:

<table width="100%">
<thead>
<tr>
<th width="32%" align="left">Item</th>
<th width="68%" align="left">Behavior</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">Ambiguity</td>
<td align="left">`config.tm` `ambig_mode first\</td>
</tr>
<tr>
<td align="left">Parataxis</td>
<td align="left">Comma clauses → `cause` / `before` (D37y / D40y)</td>
</tr>
<tr>
<td align="left">Threshold judgment</td>
<td align="left"><strong>D69</strong>: `rules.tm` + `limits.tm`; `compile_limits` extracts caps; `D69.ask` for missing value; `in` for enums</td>
</tr>
<tr>
<td align="left">Coref</td>
<td align="left">MEM5: `他/她` prefers `last_patient`</td>
</tr>
<tr>
<td align="left">Negation write</td>
<td align="left">Teach of `不/没…` does not store a negated event; queries use D57/D58</td>
</tr>
<tr>
<td align="left">MEM4</td>
<td align="left">Only very short follow-ups (≤4 chars or listed patterns); full polars like「电脑是机器吗」 stay D21</td>
</tr>
</tbody>
</table>

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
