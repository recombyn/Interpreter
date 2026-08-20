<div align="center">

[English](README.md) · **中文**

# CNI — Concept Network Interpreter

</div>

> 人话 → 符号规则引擎 → 世界事实。**无大模型，无正则黑盒。**

## 这是什么

CNI 是一个**纯符号推理的中文语言理解引擎**。

你用自然语言“教”它知识，它用同样的自然语言回答你的问题——背后没有任何神经网络，只有一套可读、可审计、可扩展的符号规则。

```
用户说："电脑是机器"
→ 引擎记录：isa(电脑, 机器)

用户问："电脑是什么"
→ 引擎查询并回答："电脑是机器"
```

## 为什么开发它

**问题**

| 方案 | 问题 |
| --- | --- |
| 正则 / 关键词匹配 | 覆盖窄，维护成本随输入变体爆炸增长 |
| 传统 NLP（分词+词性+依存） | 工具链重，泛化脆，改不了规则 |
| 大语言模型（LLM） | 幻觉、黑盒、成本高、无法精准审计 |

**目标**

CNI 的设计目标是：**可控、可解释、可扩展、零幻觉**。

- 你教进去什么，它只知道什么——不猜、不编造
- 所有推理路径可追溯（`--trace` 开关）
- 语法规则是代码，知识是文件，两者分离
- 在资源受限或隐私敏感的场景下可独立运行

## 与其他方案对比

| 能力 | &emsp;&emsp;正则&emsp;&emsp; | &emsp;传统 NLP&emsp; | &emsp;大模型&emsp; | &emsp;**CNI**&emsp; |
| --- | :---: | :---: | :---: | :---: |
| 自然语言结构 | &emsp;✗&emsp; | △（语料） | &emsp;✓&emsp; | ✓（规则） |
| 可审计 | &emsp;✓&emsp; | &emsp;△&emsp; | ✗（黑盒） | ✓（可追踪） |
| 零幻觉 | &emsp;✓&emsp; | &emsp;△&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; |
| 多种句式 | &emsp;✗&emsp; | &emsp;△&emsp; | &emsp;✓&emsp; | ✓（65 D） |
| 错别字/同音 | &emsp;✗&emsp; | &emsp;△&emsp; | &emsp;✓&emsp; | ✓（E） |
| 方言/口语 | &emsp;✗&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; | ✓（F/G） |
| 离线/无 API | &emsp;✓&emsp; | &emsp;✓&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; |
| 可扩展词典 | &emsp;✗&emsp; | &emsp;△&emsp; | &emsp;✗&emsp; | ✓（`user_dict`） |
| 知识边界清晰 | &emsp;✓&emsp; | &emsp;△&emsp; | &emsp;✗&emsp; | &emsp;✓&emsp; |

## 设计原理

**流水线**

```
输入
 │
 ▼
E（纠错）→ user_dict（用户词典）→ F41–50（语序规整）→ G（数量/时间归一）→ I（社交拦截）
 │                                                                        │
 │（未拦截）                                                              │（命中→直接回复）
 ▼
D（句法解码：65条规则）
 │
 ▼
内核（RO 路由 / WC 一致性 / QP 查询 / MEM 记忆 / REN 渲染）
 │
 ▼
输出（自然语言）
```

**知识形态（落盘谓词）**

```
isa(电脑, 机器)              # 类属
located(电脑, 桌上)          # 位置
has(我, 电脑)                # 领属
of(kind, e.1, 发明)          # 事件角色
of(content, 静夜思, 床前明月光) # 内容
```

**规则分层**

| 层 | 内容 | 条数 | 谁维护 |
| --- | --- | :---: | --- |
| **表1（内核）** | 句法/纠错/语序/时间/社交等核心算法 | 110条 | 引擎内核 |
| **表2（用户）** | 缩写、方言词、中英混写、表情映射等 | 54条 | `user_dict.tm` |

表1 是算法；表2 是词典映射。

## 能干什么

- **教知识**：用自然语言输入事实，引擎解析并持久化
- **问知识**：用自然语言提问，引擎查询已有事实并回答
- **处理复杂句式**：把字句、被字句、因果/转折/条件复句、疑问句等
- **容错输入**：自动纠正错别字、同音字、多余字符
- **口语兼容**：支持粤语语序、模糊数量、相对日期
- **记忆追踪**：维护对话焦点栈，正确处理代词指代
- **推理链**：支持 `isa` 继承链追溯（深度 ≤ 2 层）

## 快速开始

```bash
pip install -e ".[dev]"

# 写入知识
python -m cni teach "电脑是机器"
python -m cni teach "静夜思的内容是床前明月光"

# 查询
python -m cni reply "电脑是什么"
python -m cni reply "静夜思的内容是什么"

# 交互模式
python -m cni repl

# 调试（显示推理链）
python -m cni reply "电脑是什么" --trace

# 运行测试
python -m pytest
```

在 `repl` 中，以 `教|记住|学习|记` 开头自动触发写库，其余为只读查询。

## 自定义词典

编辑 `knowledge/user/user_dict.tm`，格式：

```
map yyds 永远的神
map check 检查
map 偶 我
```

## 目录结构

```
src/cni/
  data/world/  # 引擎自带世界数据（lang/base/lex/form/rules）
knowledge/
  user/        # 用户词典（表2）
docs/
  规则全表.md / rules.en.md
  指南.md / guide.en.md
```

## 设计边界

- 未教过的事实**一律不猜**，返回“我不了解这个信息”
- 不做开放域闲聊（非学习路径不写库）
- 不做诗词赏析（I11 拦截）
- `isa` 链推理深度上限 2 层，不做全图遍历

## 文档

- **规则逐条明细**：[docs/规则全表.md](docs/规则全表.md)
- **架构与使用指南**：[docs/指南.md](docs/指南.md)（含 **用户层 tm 语法**：`!` / `+`、劳动法拆分文件、D69 `rules`/`limits`）
- **English**：[README.md](README.md) · [docs/guide.en.md](docs/guide.en.md) · [docs/rules.en.md](docs/rules.en.md)
