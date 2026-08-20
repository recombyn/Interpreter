# 快速开始

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
