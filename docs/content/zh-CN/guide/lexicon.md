# 自定义词典

编辑 `knowledge/user/user_dict.tm`，格式：

```
map yyds 永远的神
map check 检查
map 偶 我
```


表2：编辑 `knowledge/user/user_dict.tm`：`map 原文 标准词`。  
**禁止**把「是/有/在/把/被/吗…」等语法骨架当作原文替换（加载时忽略，见 `src/cni/data/world/system.tm`）。

G7–G10 模糊默认：编辑 `knowledge/user/config.tm` 的 `default …` 行即可，无需改代码。
表1算法不靠改词典“补”；口语映射只加表2。
