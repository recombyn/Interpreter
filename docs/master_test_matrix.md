# Para Master Test Matrix

工业级结构化单测总表（8 维 / 42 模块）。**验收口径以引擎真实契约为准**，不是黑盒闲聊。

## 契约（禁止虚假断言）

| 项 | 现实 |
|----|------|
| 解码产物 | `DecodeOutcome`：`spoken` / `rule` / `facts_added` / `evidence` / `status` |
| 「AST 100%」 | **无 AST**。结构验收 = `facts_added` + `world.find` / `apply(? …)` |
| 性能 L4「1000 例 <1s」 | **Stretch**：全量 `boot()` 单测远超 1s；纯函数层（E/F/G）可毫秒级。CI 门禁分 `L1`/`L2`/`L3`/`slow` |
| 多领域隔离 | 单 `Para` 下 `user/**` **合并**进同一 world；真隔离 = 不同 `user_dir` / 不同 `Para` 实例 |
| D68 | 已退役，矩阵中标记 N/A |

## 四级 Pass

| 级 | 范围 | Pass |
|----|------|------|
| **L1** | 维一 preprocess + 维二 D1–D65 结构 | 规则命中 + 事实/角色正确；纯函数零 boot 优先 |
| **L2** | 维三 MEM + 维四 D66/D67/D69/MULTI + 维五 WC/QP | 多轮指代、D69.ask 续答、多火拼接 |
| **L3** | 维六 REN + 维七 Fuzz | 零 Crash、REN2 降级、超长输入有界 |
| **L4** | 维八 Domain/CI | 多 `user_dir` 隔离；回归脚本可重复；性能基线单独跟踪 |

## 覆盖地图（模块 → 状态）

状态：`GREEN` 有自动化 · `PARTIAL` 有部分 · `GAP` 待补 · `N/A` 引擎不做 · `STRETCH` 目标非当前门禁

### 维一 Preprocess（E/F/G/I）

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 1.1 | E1–E5 repair | GREEN | `tests/master/test_dim1_e_repair.py`（含 pin-aware E4） |
| 1.1b | user_dict F/H/I4–6 | GREEN | `tests/test_preprocess.py` |
| 1.2 | F41–F50 | GREEN | `tests/test_preprocess.py` |
| 1.3 | G1–G10 | GREEN | `tests/test_preprocess.py` |
| 1.4 | I1–3/I7–8/I10–11 | GREEN | `tests/test_preprocess.py` |

### 维二 Decode（D1–D65）

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 2.1 | D1–D8 | GREEN | `tests/test_design_kernel.py` |
| 2.2 | D9–D20 | GREEN | `tests/test_design_kernel.py` |
| 2.3 | D21–D36 | GREEN | `tests/master/test_dim2_questions.py` |
| 2.4 | D37–D46 | GREEN | `tests/master/test_dim2_compound_deixis.py` |
| 2.5 | D47–D56 | GREEN | `tests/master/test_dim2_compound_deixis.py` + design_kernel |
| 2.6 | D57–D65 | GREEN | design_kernel + decode_robust |

### 维三 Memory

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 3.1 | MEM1 focus 长度 5 | GREEN | `tests/master/test_dim3_mem.py` |
| 3.1b | MEM2 永久/临时 | GREEN | `tests/master/test_dim3_mem.py` |
| 3.1c | MEM3 重置 | GREEN | dim3_mem + design_kernel |
| 3.2 | MEM4 短问接钉 | GREEN | user_docs + d69_judge |
| 3.2b | MEM5 共指 | GREEN | dim3_mem + decode_robust |

### 维四 Content & D69

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 4.1 | D66/D67 | GREEN | user_docs + design_kernel |
| 4.2 | D69 tier/ask/合取/枚举 | GREEN | d69_judge + labor_case + eval_d69_100 |
| 4.3 | MULTI | GREEN | d69_judge multi-fire |

### 维五 WC / QP

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 5.1 | WC1 重复忽略 | GREEN | `tests/master/test_dim5_wc_qp.py` |
| 5.1b | WC2 矛盾并存 | GREEN | 同上（**不做冲销**即正确） |
| 5.1c | WC3 精准 drop | GREEN | 同上 |
| 5.2 | QP1–QP3 / isa.trans | GREEN | design_kernel + master |

### 维六 REN

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 6.1 | REN1/REN2 / reply_mode / judge_cite | GREEN | design_kernel + reply_mode + d69 |

### 维七 Robustness

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 7.1 | 无标点粘连 | GREEN | `tests/master/test_dim7_fuzz_smoke.py` |
| 7.2 | Fuzz / 溢出 | GREEN | 同上（零 Crash） |
| 7.3 | 超长有界 | GREEN | ~1k 前缀 <60s smoke；50k ReDoS 仍为 STRETCH |
| 7.4 | ambig_mode | GREEN | decode_robust |

### 维八 Domain / CI

| # | 模块 | 状态 | 主要位置 |
|---|------|------|----------|
| 8.1 | 多领域隔离 | GREEN | `tests/master/test_dim8_domain.py`（双 `user_dir` + judge_topics） |
| 8.2 | 1000+ / <1s / 泄漏 | PARTIAL | `test_dim8_stretch_smoke.py`：纯函数 1000 次 <1s + 10k push 栈有界；全量 boot/10 万轮仍为 stretch |

## 怎么跑

```bat
cd /d c:\Users\DELL\concept-network-interpreter
set PYTHONPATH=src
python -m pytest tests/master -q
python -m pytest -m L1 -q
python -m pytest -m "L2 and not stretch" -q
python -m para.tools.eval_d69_100
```

## 与「全套 42 模块」的关系

用户规划中的模块名全部登记在 `tests/master/registry.py`。  
`test_registry_complete` 保证 **42 个槽位不丢**；GREEN/PARTIAL/GAP 由 registry 状态字段驱动文档与 CI 报告，避免口头宣称完备。
