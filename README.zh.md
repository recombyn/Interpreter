<div align="center">

# Para

<p>
  <a href="./README.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README.zh.md"><img alt="简体中文" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
</p>

</div>

> **可插拔的汉语解码器**：精确理解中文，零幻觉；知识完全由用户掌控。

## 产品契约

| 承诺 | 含义 |
| --- | --- |
| **In-scope 忠实** | 已覆盖句式 + 已教知识 → 确定、可复现 |
| **Out-of-scope 拒绝** | 未教过的世界知识 → 明确不知道，**绝不编造** |
| **知识外置** | 语法在引擎；事实在 `knowledge/user/`（或你注入的目录） |
| **可审计** | 每次理解带回 `rule`；可选 `facts_added` |

不是开放域聊天模型；覆盖靠规则扩展，不靠猜测。

## 插到任意系统

```python
from para import Para

# user_dir = 你的知识目录（词典 / 文档 / 记忆）
eng = Para(load_user_docs=False, user_dir="./my_knowledge")

# 写：教事实
w = eng.decode("教电脑是机器", write=True)
# w.status == "write"
# w.facts_added → [{"pred":"isa","args":["电脑","机器"]}, ...]

# 读：查事实
q = eng.decode("电脑是什么", write=False)
# q.status == "query", q.spoken == "电脑是机器", q.rule == "D3.echo"

# 未知：拒绝
u = eng.decode("火星上有独角兽吗")
# u.miss == True 或 status == "refuse" —— 不会捏造答案
```

主机只消费 `DecodeOutcome`（或 `.to_dict()`）：自己渲染 UI、自己持久化。  
**有理有据**：检索到的相关知识在独立字段 `evidence`（`ref` + `text`），与话术 `spoken` 分开。

便捷封装仍可用：`teach()` / `reply()` / `interpret()`。

## 案例：劳动法

完整用户知识包（概念图 + 法条行索引 + D69 阈值）：

- 说明：[examples/labor_law/README.md](examples/labor_law/README.md)
- 演示：`PYTHONPATH=src python examples/labor_law/demo.py`
- 评测：`PYTHONPATH=src python -m para.tools.eval_labor_law`

## 安装

```bash
pip install -e ".[dev]"
python -m para teach "电脑是机器"
python -m para reply "电脑是什么"
python -m para decode "电脑是什么"
python -m para reply "电脑是什么" --trace
```

## 目录

```
src/para/           # 解码算法（无领域知识）
knowledge/user/            # 用户知识与话术
knowledge/user/劳动法/     # 劳动法案例包
examples/labor_law/        # 主机接入演示
docs/                      # 规则与指南
```

## 设计边界

- 无大模型；未教过的不猜
- 写库失败不降级闲聊（RO3）
- `isa` 推理深度默认 ≤ 2

## 文档

- [docs/指南.md](docs/指南.md) · [docs/规则全表.md](docs/规则全表.md)
- English: [README.md](README.md) · [docs/guide.en.md](docs/guide.en.md)
