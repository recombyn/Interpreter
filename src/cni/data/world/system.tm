# 系统词表/闭集（表1算法数据；改这里无需改 Python）
# 用户词典禁止项见 forbid_user_dict；词表抽查见 require_lex

forbid_user_dict 是
forbid_user_dict 有
forbid_user_dict 在
forbid_user_dict 的
forbid_user_dict 了
forbid_user_dict 着
forbid_user_dict 过
forbid_user_dict 吗
forbid_user_dict 谁
forbid_user_dict 什么
forbid_user_dict 哪里
forbid_user_dict 哪儿
forbid_user_dict 怎么
forbid_user_dict 为什么
forbid_user_dict 多少
forbid_user_dict 把
forbid_user_dict 被
forbid_user_dict 给
forbid_user_dict 让
forbid_user_dict 叫
forbid_user_dict 使
forbid_user_dict 令
forbid_user_dict 请
forbid_user_dict 派
forbid_user_dict 帮
forbid_user_dict 比
forbid_user_dict 不如
forbid_user_dict 和
forbid_user_dict 还是
forbid_user_dict 因为
forbid_user_dict 所以
forbid_user_dict 虽然
forbid_user_dict 但是
forbid_user_dict 如果
forbid_user_dict 就

require_lex 是
require_lex 有
require_lex 在
require_lex 的
require_lex 吗
require_lex 谁
require_lex 什么
require_lex 把
require_lex 被
require_lex 给
require_lex 让
require_lex 比

# --- I 社交闭集 ---
i_thanks 谢谢
i_greet 你好
i_greet 您好
i_bye 再见
i_bye 拜拜
i_ack 哦
i_ack 嗯
i_ack 行
i11_msg 我擅长处理事实性问题，不懂诗词赏析。
i11_ask 谁
i11_ask 什么
i11_ask 吗
i11_ask 哪儿
i11_ask 哪里
i11_ask 怎么
i11_ask 为什么
i11_ask 多少
i11_ask 几个
i11_classical 之
i11_classical 乎
i11_classical 者
i11_classical 也
i11_classical 矣
i11_classical 焉
i11_classical 哉
i11_modern 有
i11_modern 在
i11_modern 把
i11_modern 被
i11_modern 的
i11_modern 了
i11_modern 着
i11_modern 过
i11_modern 呢
i11_modern 吧
i11_modern 啊
i11_modern 不
i11_modern 没
i11_modern 能
i11_modern 会
i11_modern 要
i11_modern 吃
i11_modern 喝
i11_modern 看
i11_modern 去
i11_modern 来
i11_modern 走
i11_modern 到
i11_modern 对
i11_modern 给
i11_modern 帮
i11_modern 让
i11_modern 做
i11_modern 说
i11_modern 讲
i11_modern 介绍
i11_modern 我
i11_modern 你
i11_modern 他
i11_modern 她
i11_modern 们
i11_modern 这
i11_modern 那
i11_modern 发明
i11_modern 电脑
i11_modern 机器
i11_modern 内容
i11_modern 因为
i11_modern 所以
i11_modern 但是
i11_modern 如果
i11_modern 正在
i11_modern 知道
i11_modern 喜欢
i11_modern 打
i11_modern 骂
i11_modern 踢
i11_modern 买
i11_modern 卖
i11_modern 写
i11_modern 读
i11_modern 问
i11_modern 答
i11_modern 开
i11_modern 关
i11_modern 用
i11_modern 找
i11_modern 拿
i11_modern 放

# --- RO 教学前缀 ---
teach_prefix 教
teach_prefix 记住
teach_prefix 学习
teach_prefix 记

# --- E2 同音组：首字为规范字 ---
pin_group 机 积 基
pin_group 器 气 期
pin_group 是 时 事 市 试
pin_group 有 又 友
pin_group 在 再
pin_group 的 地 得
pin_group 和 合
pin_group 比 笔
pin_group 吗 嘛
pin_group 没 每
pin_group 不 部

# --- F41–F50 语序数据 ---
f_verb_char 去
f_verb_char 来
f_verb_char 吃
f_verb_char 看
f_verb_char 做
f_verb_char 喝
f_verb_char 说
f_verb_char 走
f_verb_char 读
f_verb_char 写
f_verb_char 听
f_verb_char 玩
f_verb_char 食
f_verb_char 睇
f_verb_multi 吃饭
f_verb_multi 食饭
f_verb_multi 看看
f_verb_multi 听听
f_verb_multi 走走
f_verb_multi 下载
f_adj_char 高
f_adj_char 矮
f_adj_char 大
f_adj_char 小
f_adj_char 好
f_adj_char 坏
f_adj_char 强
f_adj_char 弱
f_adj_char 快
f_adj_char 慢
f_adj_char 长
f_adj_char 短
f_adj_char 新
f_adj_char 旧
f_adj_char 美
f_adj_char 丑
f_adj_char 远
f_adj_char 近
f_complete 咗 了
f_complete 嘞 了
f_polar 有冇 有没有
f_polar 系咪 是不是
f_polar 啱唔啱 对不对
f_prog_fixed 紧食饭 正在吃饭
f_prog_map 紧食 正在吃
f_prog_map 紧睇 正在看
f_source_suffix 来的
f_source_rewrite 是从哪里来
f_tell_pattern 讲(.+?)我知
f_tell_empty 讲我知
f_tell_to 告诉我
f_tail_many 很多
f_tail_many 得多

# --- G 相对日 ---
rel_day 大后天 3
rel_day 大前天 -3
rel_day 昨天 -1
rel_day 前天 -2
rel_day 明天 1
rel_day 后天 2
rel_day 今天 0

# --- D66 截断：逗号后后续主语 ---
d66_next_subj 它
d66_next_subj 他
d66_next_subj 她
d66_next_subj 这
d66_next_subj 那
d66_next_subj 你
d66_next_subj 我

# --- 事件指代量词 ---
event_deixis 事
event_deixis 次
event_deixis 回
event_deixis 遍

# --- 用户词典：lex 结构义项名（英文 sense）---
struct_sense copula
struct_sense have
struct_sense loc
struct_sense ba
struct_sense bei
struct_sense de
struct_sense ask
struct_sense who
struct_sense what
struct_sense where
struct_sense how
struct_sense why
struct_sense howmany
struct_sense give_mark
struct_sense let
struct_sense help
struct_sense call
struct_sense invite
struct_sense cmp
struct_sense less
struct_sense or
struct_sense with_mark
struct_sense cause_mark
struct_sense so_mark
struct_sense if_mark
struct_sense then_mark
struct_sense although
struct_sense but
struct_sense target_mark
struct_sense dest_mark

# --- 复句连接（左 右 关系 规则号）---
clause_pair 虽然 但是 contrast D39
clause_pair 虽然 可是 contrast D39
clause_pair 因为 所以 cause D37
clause_pair 如果 就 condition D40
clause_pair 不但 而且 progression D45
clause_pair 先 然后 before D42
clause_pair 先 再 before D42
# clause_single 标记 关系 规则 [除非含此词]
clause_single 的时候 during D41
clause_single 因此 cause D38
clause_single 然后 before D43 先
clause_single 但是 contrast D46 虽然

# --- 附加问语气尾 ---
tag_tone D33 ，对吧
tag_tone D34 ，是吗

# --- MEM 重置口令 ---
mem_reset 重置
mem_reset 新会话
mem_reset 重新开始
