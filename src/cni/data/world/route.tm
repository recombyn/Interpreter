# 优化三：规则特征路由表（性能短路）
# 命中特征 → 优先只跑对应组；未命中则顺延下一组

group social
  features 谢谢 你好 您好 再见 拜拜 哦 嗯 行
  rules I1 I2 I3 I10

group query
  features 吗 是不是 有没有 能不能 谁 什么 哪里 哪儿 怎么 为什么 多少 几个 还是 对吧 是吗 难道
  rules D21-D36

group special
  features 把 被 给 让 叫 使 令 请 派 帮 比 不如 到 对
  # 且非疑问（实现里若已命中 query 组则跳过本组优先）
  rules D9-D20

group compound
  features 因为 所以 因此 虽然 但是 可是 如果 就 先 再 然后 不但 而且 的时候
  rules D37-D46

group deixis
  features 这 这个 那 那个 他 她 的
  rules D47-D56

group basic
  features
  rules D1-D8 D57-D65 D66 D67 D69
