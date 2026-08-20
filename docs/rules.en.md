# Full System Rule Catalog (Table 1)

[中文](规则全表.md) · English

Ownership follows **Table 1 / Table 2** in [guide.en.md](guide.en.md).
This English page explains the catalog structure. The authoritative rule rows
(Chinese surface patterns) live in [规则全表.md](规则全表.md).

Table 1 count = **110** (D1–D65 + E + F41–50 + G + I1–3/I7–8/I10 + RO/WC/QP/MEM/REN).
Extras D66 / D67 / I11 / MEM4 are kernel extensions and do not change the 110 count.

## Sections

<table width="100%">
<thead>
<tr>
<th width="28%" align="left">Section</th>
<th width="28%" align="left">IDs</th>
<th width="44%" align="left">Topic</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">1. Syntactic decode</td>
<td align="left">D1–D65 (+ D66–D67)</td>
<td align="left">SVO, ba/bei, questions, complexes, deixis, modality, content</td>
</tr>
<tr>
<td align="left">2. Input repair</td>
<td align="left">E1–E5</td>
<td align="left">Exact / homophone / typo / delete / never-insert</td>
</tr>
<tr>
<td align="left">3. Op routing</td>
<td align="left">RO1–RO3</td>
<td align="left">Teach vs chat; no soft-fail on teach</td>
</tr>
<tr>
<td align="left">4. World consistency</td>
<td align="left">WC1–WC3</td>
<td align="left">Ignore dupes; keep contradictions; precise drop</td>
</tr>
<tr>
<td align="left">5. Query priority</td>
<td align="left">QP1–QP3</td>
<td align="left">Explicit > inferred > session > events; isa depth 2</td>
</tr>
<tr>
<td align="left">6. Memory</td>
<td align="left">MEM1–MEM3 (+ MEM4)</td>
<td align="left">Focus stacks; durable events; reset; short-ask → D67</td>
</tr>
<tr>
<td align="left">7. Render fallback</td>
<td align="left">REN1–REN2</td>
<td align="left">Bare surface; empty-result phrase</td>
</tr>
<tr>
<td align="left">8. Word order</td>
<td align="left">F41–F50</td>
<td align="left">Dialect order / aspect rewrite (algorithmic)</td>
</tr>
<tr>
<td align="left">9. Normalize</td>
<td align="left">G1–G10</td>
<td align="left">Quantity / relative date / fuzzy defaults</td>
</tr>
<tr>
<td align="left">10. Social & punctuation</td>
<td align="left">I1–I3 / I7–I8 / I10 (+ I11)</td>
<td align="left">Greetings; punct collapse; poetry intercept</td>
</tr>
</tbody>
</table>

## Content extras (D66–D67 only)

<table width="100%">
<thead>
<tr>
<th width="32%" align="left">ID</th>
<th width="68%" align="left">Role</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">D66</td>
<td align="left">Write `of(content, entity, text)`; content index + optional disk shard</td>
</tr>
<tr>
<td align="left">D67</td>
<td align="left">Point lookup by entity (memory ∪ sharded store); pin entity/doc/topic</td>
</tr>
<tr>
<td align="left">MEM4</td>
<td align="left">Short follow-up (`那呢` / `违法吗` …) with entity pin → expand to D67</td>
</tr>
</tbody>
</table>

There is **no D68 open-search rule**. Topic questions without a resolvable entity → REN2 / normal D miss. User docs sync to `.tm` + `.content/` for D67 scale.

## Counts

<table width="100%">
<thead>
<tr>
<th width="50%" align="left">Block</th>
<th width="16%" align="center">Count</th>
<th width="34%" align="left">Owner</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">D1–D65</td>
<td align="center">65</td>
<td align="left">Table 1</td>
</tr>
<tr>
<td align="left">E1–E5</td>
<td align="center">5</td>
<td align="left">Table 1</td>
</tr>
<tr>
<td align="left">F41–F50</td>
<td align="center">10</td>
<td align="left">Table 1</td>
</tr>
<tr>
<td align="left">G1–G10</td>
<td align="center">10</td>
<td align="left">Table 1</td>
</tr>
<tr>
<td align="left">I1–I3 / I7–I8 / I10</td>
<td align="center">6</td>
<td align="left">Table 1</td>
</tr>
<tr>
<td align="left">RO + WC + QP + MEM + REN</td>
<td align="center">14</td>
<td align="left">Table 1</td>
</tr>
<tr>
<td align="left">**Table 1 total**</td>
<td align="center">**110**</td>
<td align="left"></td>
</tr>
<tr>
<td align="left">D66–D67 / I11 / MEM4</td>
<td align="center">4</td>
<td align="left">extras (system)</td>
</tr>
<tr>
<td align="left">F1–40 + H1–10 + I4–6 + I9</td>
<td align="center">54</td>
<td align="left">Table 2 (user lexicon)</td>
</tr>
</tbody>
</table>

See [规则全表.md](规则全表.md) for every rule’s pattern and action.
