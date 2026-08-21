<div align="center">

# Para

<p>
  <a href="./README.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README.zh.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
</p>

</div>

> **A pluggable Chinese decoder**: precise understanding, zero hallucination; knowledge owned entirely by the host.

## Contract

| Promise | Meaning |
| --- | --- |
| **Faithful in-scope** | Covered constructions + taught facts → deterministic |
| **Refuse out-of-scope** | Untaught world knowledge → explicit miss, **never invent** |
| **Knowledge outside** | Grammar in the engine; facts in `knowledge/user/` (or your injected dir) |
| **Auditable** | Every outcome carries `rule`; optional `facts_added` |

Not an open-domain chatbot. Coverage grows by rules, not by guessing.

## Plug into any host

```python
from para import Para

eng = Para(load_user_docs=False, user_dir="./my_knowledge")

w = eng.decode("教电脑是机器", write=True)
# w.status == "write"; w.facts_added includes isa(电脑, 机器)

q = eng.decode("电脑是什么", write=False)
# q.status == "query"; q.spoken == "电脑是机器"

u = eng.decode("火星上有独角兽吗")
# u.miss / refuse — no fabricated yes
```

Hosts consume `DecodeOutcome` (or `.to_dict()`). Justification for answers lives in `evidence` (retrieved knowledge snippets), separate from `spoken`. Convenience: `teach()` / `reply()` / `interpret()`.

## Case study: labor law

End-to-end user knowledge pack (concepts + statute lines + D69 limits):

- Walkthrough: [examples/labor_law/README.md](examples/labor_law/README.md)
- Demo: `PYTHONPATH=src python examples/labor_law/demo.py`
- Eval: `PYTHONPATH=src python -m para.tools.eval_labor_law`

## Install

```bash
pip install -e ".[dev]"
python -m para teach "电脑是机器"
python -m para reply "电脑是什么"
python -m para decode "电脑是什么"
```

## Layout

```
src/para/           # decode algorithms (no domain knowledge)
knowledge/user/            # user knowledge & surfaces
knowledge/user/劳动法/     # labor-law case pack
examples/labor_law/        # host integration demo
docs/                      # rules & guides
```

## Docs

- [docs/guide.en.md](docs/guide.en.md) · [docs/rules.en.md](docs/rules.en.md)
- 中文：[README.zh.md](README.zh.md) · [docs/指南.md](docs/指南.md)
