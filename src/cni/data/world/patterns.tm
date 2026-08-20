# 优化六：D 系列触发模式（供启动/开发期冲突检测）
# {变量} → 检测时译为 .*? ；priority A > B 表示允许重叠时 A 优先

pattern D1 {主语} {动词} {宾语}
pattern D2 {主语} {动词}
pattern D3 {主语} 是 {表语}
pattern D4 {处所} 有 {事物}
pattern D5 {人} 有 {事物}
pattern D6 {事物} 在 {处所}
pattern D7 {动词} {宾语}
pattern D8 {主语} 在 {动词} {宾语}
pattern D9 {主语} 把 {宾语} {动词}
pattern D10 {受事} 被 {施事} {动词}
pattern D11 {主语} 给 {间宾} {直宾}
pattern D12 {主语} 帮 {宾语} {动词} {宾语2}
pattern D15 {主语} 让 {兼语} {动词} {宾语}
pattern D17 {主语} 对 {宾语} {动词}
pattern D18 {主语} 比 {宾语} {形容词}
pattern D19 {主语} 不如 {宾语} {形容词}
pattern D20 {主语} {动词} 到 {处所}
pattern D21 {陈述} 吗
pattern D22 {主语} 是不是 {表语}
pattern D23 {主语} 有没有 {事物}
pattern D25 谁 {动词} {宾语}
pattern D26 {主语} {动词} 谁
pattern D27 {主语} 是什么
pattern D28 {主语} 是谁
pattern D29 {事物} 在哪里
pattern D32 {主语} 是 {A} 还是 {B}
pattern D33 {陈述} 对吧
pattern D34 {陈述} 是吗
pattern D35 难道 {陈述} 吗
pattern D37 因为 {原因} 所以 {结果}
pattern D39 虽然 {让步} 但是 {转折}
pattern D40 如果 {条件} 就 {结果}
pattern D44 {A} 和 {B}
pattern D47 {动词} {宾语}
pattern D55 {X} 的
pattern D57 {主语} 不 {动词} {宾语}
pattern D58 {主语} 没 {动词} {宾语}
pattern D59 别 {动词} {宾语}
pattern D66 {实体} 的内容是 {文本}
pattern D67 {实体} 的内容是什么
pattern D69 {主题} {时长或取值} 合法吗

priority D9 > D1
priority D10 > D1
priority D11 > D1
priority D12 > D1
priority D15 > D1
priority D3 > D1
priority D3 > D2
priority D4 > D1
priority D4 > D2
priority D5 > D1
priority D5 > D2
priority D5 > D4
priority D6 > D1
priority D6 > D2
priority D8 > D1
priority D8 > D2
priority D8 > D6
priority D17 > D1
priority D17 > D2
priority D18 > D1
priority D18 > D2
priority D19 > D1
priority D19 > D2
priority D19 > D18
priority D20 > D1
priority D20 > D2
priority D22 > D1
priority D22 > D2
priority D22 > D3
priority D23 > D1
priority D23 > D2
priority D25 > D1
priority D25 > D2
priority D26 > D1
priority D26 > D2
priority D27 > D1
priority D27 > D2
priority D27 > D3
priority D28 > D1
priority D28 > D2
priority D28 > D3
priority D29 > D1
priority D29 > D2
priority D32 > D1
priority D32 > D2
priority D32 > D3
priority D35 > D1
priority D35 > D2
priority D35 > D21
priority D37 > D1
priority D37 > D2
priority D39 > D1
priority D39 > D2
priority D40 > D1
priority D40 > D2
priority D44 > D1
priority D44 > D2
priority D66 > D1
priority D66 > D2
priority D67 > D1
priority D67 > D2
priority D67 > D66
priority D69 > D1
priority D69 > D2
priority D69 > D21
priority D69 > D67
priority D1 > D2
priority D7 > D1
priority D7 > D2
priority D47 > D1
priority D47 > D2
priority D47 > D7
priority D59 > D1
priority D59 > D2
priority D59 > D7
priority D57 > D1
priority D57 > D2
priority D57 > D7
priority D58 > D1
priority D58 > D2
priority D58 > D7
priority D3 > D7
priority D4 > D7
priority D5 > D7
priority D6 > D7
priority D8 > D7
priority D9 > D2
priority D9 > D7
priority D10 > D2
priority D10 > D7
priority D11 > D2
priority D11 > D7
priority D12 > D2
priority D12 > D7
priority D15 > D2
priority D15 > D7
priority D17 > D7
priority D18 > D7
priority D19 > D7
priority D20 > D7
priority D21 > D2
priority D21 > D7
priority D22 > D7
priority D23 > D7
priority D25 > D7
priority D26 > D7
priority D27 > D7
priority D28 > D7
priority D29 > D7
priority D32 > D7
priority D33 > D2
priority D33 > D7
priority D34 > D2
priority D34 > D7
priority D35 > D7
priority D37 > D7
priority D39 > D7
priority D40 > D7
priority D44 > D7
priority D47 > D8
priority D47 > D9
priority D47 > D10
priority D47 > D11
priority D47 > D12
priority D47 > D15
priority D47 > D17
priority D47 > D18
priority D47 > D19
priority D47 > D20
priority D47 > D21
priority D47 > D22
priority D47 > D23
priority D47 > D25
priority D47 > D26
priority D47 > D27
priority D47 > D28
priority D47 > D29
priority D47 > D32
priority D47 > D33
priority D47 > D34
priority D47 > D35
priority D47 > D37
priority D47 > D39
priority D47 > D40
priority D47 > D44
priority D47 > D55
priority D47 > D57
priority D47 > D58
priority D47 > D59
priority D47 > D66
priority D47 > D67
priority D69 > D47
priority D55 > D1
priority D55 > D2
priority D55 > D7
priority D3 > D47
priority D4 > D47
priority D5 > D47
priority D6 > D47
priority D25 > D26
priority D66 > D7
priority D67 > D7
priority D69 > D7
priority D21 > D1
priority D33 > D1
priority D34 > D1
priority D34 > D21
priority D33 > D21
