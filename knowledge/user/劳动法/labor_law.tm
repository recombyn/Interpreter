# User-layer labor-law knowledge (NOT system world data).
# Loaded only when an eval/app passes this file as memory_path.
# Format: same as runtime memory (! name : sort / + facts).

# --- Domain individuals / kinds ---
! 员工 : e
! 人 : e
! 公司 : e
! 组织 : e
! 合同 : e
! 劳动合同 : e
! 加班 : e
! 工作 : e
! 工资 : e
! 最低工资 : e
! 休息权 : e
! 报酬权 : e
! 期限 : e
! 试用期 : e
! 社会保险 : e
! 劳动法 : e
! 劳动合同法 : e
! 八小时 : e
! 法定工时 : e
! 休息日 : e
! 休息 : e
! 保护劳动者的合法权益 : e
! 规范劳动合同的订立履行 : e

# --- Taxonomy (isa) ---
+ isa(员工, 人)
+ isa(公司, 组织)
+ isa(劳动合同, 合同)
+ isa(加班, 工作)
+ isa(最低工资, 工资)
+ isa(试用期, 期限)
+ isa(休息日, 休息)
+ isa(法定工时, 八小时)

# --- Possession (has) ---
+ has(员工, 休息权)
+ has(员工, 报酬权)
+ has(公司, 员工)
+ has(员工, 工资)

# --- Document content (of content) ---
+ of(content, 劳动法, 保护劳动者的合法权益)
+ of(content, 劳动合同法, 规范劳动合同的订立履行)
