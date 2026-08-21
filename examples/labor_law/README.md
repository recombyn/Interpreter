# 案例：劳动法（用户知识包）

把 Para 当作**可插拔汉语解码器**：语法在引擎，劳动法知识全部在 `knowledge/user/`。

## 知识布局

| 文件 | 作用 |
| --- | --- |
| `knowledge/user/劳动法/labor_law.tm` | 小规模概念图（isa / has / content） |
| `knowledge/user/劳动法/劳动法.text` → `劳动法.tm` | 整部法原文行索引（D66/D67） |
| `knowledge/user/劳动法/limits.tm` | 试用期/竞业限制等上限事实 |
| `knowledge/user/劳动法/rules.tm` | D69 判定声明（`rule` / `tier`） |
| `knowledge/user/user_dict.tm` | 口语/法条用语 → 概念图术语 |
| `knowledge/user/劳动法/eval_cases.json` | 回归用例 |

词典方向：法条用语归到概念图（`劳动者→员工`，`用人单位→公司`）。

## 一键演示

```bash
pip install -e ".[dev]"
PYTHONPATH=src python examples/labor_law/demo.py
```

演示走公开 API `Para.decode` → `DecodeOutcome`（`status` / `rule` / `spoken` / `facts_added` / `miss`）。

## 主机接入（最短）

```python
from para import Para
from para.paths import USER_DIR

eng = Para(user_dir=USER_DIR)  # 加载劳动法记忆 + 判定规则

q = eng.decode("试用期六个月合法吗")
# q.status == "query", q.rule == "D69", "合法" in q.spoken
# q.evidence → [{kind, ref, text, topic}] 有理有据的条文正文

w = eng.decode("教兼职是工作", write=True)
# w.status == "write", facts_added 含 isa(兼职, 工作)
```

CLI：

```bash
python -m para decode "试用期六个月合法吗"
python -m para decode "教兼职是工作" --write true
```

`DecodeOutcome.evidence` separately carries retrieved knowledge (ref + body), decoupled from `spoken` so hosts can show “why this answer.”  
Gaps surface as **`suggestions`** (proposed `rules.tm` / `limits.tm` lines or `need_doc`) — confirm before writing; never auto-apply.

## 长句与一次多问

口语前缀、叙事铺垫仍可剥出判定/条文问句；一句里多个问句时，`spoken` 用 `；` 拼接各段答案，条文依据在 `evidence` 列表里（与 `spoken` 解耦）。

示例：

- `请问一下我们公司约定试用期六个月合法吗` → D69「合法」+ evidence
- `试用期六个月合法吗竞业限制二年合法吗` → 两段判定，中间 `；`
- `员工入职签一年合同试用期两个月合法吗另外竞业限制两年合法吗` → 叙事 + `另外` 仍多段 `；` 作答

## 回归

```bash
PYTHONPATH=src python -m para.tools.eval_labor_law
```

覆盖：词典、概念图问答、教↔查、D69 判定、长句/一次多问、已知边界（空世界 refuse）。

## 产品契约在本案例中的体现

1. **In-scope 忠实**：已教 `员工是人` / 已同步 limits → 确定答案。
2. **Out-of-scope 拒绝**：未教的世界事实 → `miss` / refuse，不编造。
3. **知识外置**：删掉 `knowledge/user/劳动法/` 后，引擎不再“懂劳动法”。
4. **可审计**：每条结果带 `rule`（如 `D3.echo` / `D69` / `REN2`）。
