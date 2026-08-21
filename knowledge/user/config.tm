# 用户/管理员可改配置（改这里即可，无需动代码；重启或清缓存后生效）
# G7–G10 模糊量默认值

default 几十 30
default 大半 70%
default 一小会儿 5分钟
default 三五 3-5

# 回复模式（影响是非问 yes/no 话术；不影响 D67 正文）
#   default  — 用 form.tm：是的 / 不是
#   bool     — true / false
#   zh_bool  — 是 / 否
# 也可在 knowledge/user/form.tm 里写 out yes … / out no … 覆盖单条话术
reply_mode default

# 歧义策略（多条 D 组都能解时）
#   first   — 取第一条（默认，兼容旧行为）
#   clarify — 反问确认（AMB1）
#   warn    — 仍答第一条，但 Trace/Result 带 warn 与较低 confidence
ambig_mode first

# D69 阈值判定：knowledge/user/**/rules.tm + 各领域 limits.tm（无需改代码）
# judge_cite on|off — 是否附出处相关正文（有 content 则返回条文，不只报行号）
judge_cite on
