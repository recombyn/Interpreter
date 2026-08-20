# Getting started

```bash
pip install -e ".[dev]"

# Teach
python -m cni teach "电脑是机器"
python -m cni teach "静夜思的内容是床前明月光"

# Query
python -m cni reply "电脑是什么"
python -m cni reply "静夜思的内容是什么"

# Interactive
python -m cni repl

# Debug (show inference chain)
python -m cni reply "电脑是什么" --trace

# Tests
python -m pytest
```

In `repl`, lines starting with `教|记住|学习|记` write to the world; everything else is read-only query.
