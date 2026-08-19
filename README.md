# 机器世界解释器

人话 → 纠错（词表 / 已有名字）→ 精确解码 → 世界。不靠大模型。

聊天只问答和纠错回述，**不写知识**。写库走程序接口：`hear` / `MachineWorld.apply`。

```
hear("电脑是机器")     写入 isa(电脑, 机器)
电脑是什么             问句
电脑是机气             纠成已有名字后回述
电脑是桥梁             不改库，仍按「电脑是机器」说
```

这是受控小世界：短句、浅层事件、有界前向链。不是 Prolog，也不是 OWL。

```
knowledge/world/lang.tm    语言核
knowledge/world/base.tm    闭集名字与关系
knowledge/world/rules.tm   前向规则（仍只用 isa/of）
knowledge/world/form.tm    闭集构式
knowledge/world/ch.tm      汉语词表
knowledge/world/en.tm      英语词表
knowledge/world/ch.pin.tm  封闭类同音（纠错用）
```

```bash
python -m pip install -e ".[dev]"
python -m cni reply "你好"
python -m cni repl
python -m cni gui
python -m cni --infer-depth 0 repl
```

## 一句中文怎么走

```
程序        hear("电脑是机器")
tell        isa(电脑, 机器)

人话        电脑是什么
ask         of(to, e.n, 电脑)  of(with, e.n, what)
find        isa(电脑, x)
speak       电脑是机器
```

再 `hear("机器是设备")`，规则 `isa.trans` 会推出 `isa(电脑, 设备)`。问「电脑是什么」仍优先说库里**显式**教过的「机器」。

陌生句式、库里没有的问句：`world-miss`。

## 边界

- `drop` 是忘掉事实；`of(pol, e.n, no)` 是这次话为否定。两者不是逻辑 ¬。
- 一小句一个事件 `e.n`。
- `find` 一次绑一个变量；多条件用 `∧`。
- 新关系只加 `base.tm`，新句型只加 `form.tm` / 词表。
- 纠错只改表面字，不把新说法写进库。

CLI 把**程序写入**的事实（含 `last` / `focus`）记到 `runtime/world.tm`（`--remember` 路径）。
