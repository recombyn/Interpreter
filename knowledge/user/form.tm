# 用户层输出话术覆盖（可选）
# 格式与 src/cni/data/world/form.tm 相同：out <名> <表面>
# 会叠在世界 form.tm 之上；reply_mode bool/zh_bool 仍会覆盖 yes/no。
#
# 示例（取消注释即生效）：
# out yes true
# out no false
# out unknown_q unknown
# out unknown_info unknown
# out greet Hi
