-- ============================================================
-- DWD 层 DDL — 明细数据层（清洗后）
-- ODS → DWD 转换: 脱敏 + 清洗 + 标准化 + 质量评分
-- 新增列: dq_score(数据质量分), dq_quarantined(隔离标记)
-- ============================================================

-- ── 1. 清洗后申请表 ──
CREATE TABLE IF NOT EXISTS dwd.dwd_application (
    user_id           STRING    COMMENT '用户ID。原始为空→填充MISSING',
    application_id    STRING    COMMENT '申请单号',
    apply_amount      DOUBLE    COMMENT '申请金额(元)。已修正: 负数→0, NULL→0',
    product_type      STRING    COMMENT '产品类型(已标准化): CASH_LOAN/INSTALLMENT/REVOLVING/UNKNOWN',
    user_name         STRING    COMMENT '★ 已脱敏: 黄敏→黄*',
    id_card           STRING    COMMENT '★ 已脱敏: 934184********8691',
    phone             STRING    COMMENT '★ 已脱敏: 138****8795',
    occupation        STRING    COMMENT '职业(已标准化): employee/self_employed/freelancer/unemployed/UNKNOWN',
    monthly_income    DOUBLE    COMMENT '月收入(元)。已修正: NULL→0, 负数→0',
    education         STRING    COMMENT '学历',
    city              STRING    COMMENT '所在城市',
    ip_address        STRING    COMMENT '★ 已脱敏IP',
    device_id         STRING    COMMENT '设备指纹ID',
    channel           STRING    COMMENT '渠道(已标准化): APP_ANDROID/APP_IOS/H5/PARTNER_A/PARTNER_B/UNKNOWN',
    apply_time        TIMESTAMP COMMENT '申请提交时间',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。初始100,逐项扣分。≥60通过',
    dq_quarantined    BOOLEAN   COMMENT '★ 隔离标记。dq_score<60→TRUE,不入DWS层',
    dt                STRING    COMMENT '分区键 — 日期'
)
COMMENT '清洗+脱敏后的用户申请明细 — dq_score<60记录被隔离'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_application',
    'transformation' = 'clean_application()',
    'quarantine_threshold' = 'dq_score < 60'
);


-- ── 2. 清洗后行为日志表 ──
CREATE TABLE IF NOT EXISTS dwd.dwd_user_behavior (
    user_id           STRING    COMMENT '用户ID。空值→anonymous,扣20分但不丢弃',
    event_type        STRING    COMMENT '事件类型(已标准化): page_view/click/input/submit/app_install/app_uninstall/error/unknown',
    event_detail      STRING    COMMENT '事件详情JSON',
    device_id         STRING    COMMENT '设备指纹ID',
    session_id        STRING    COMMENT '会话ID。NULL→session_generated',
    page_url          STRING    COMMENT '页面路径',
    ip                STRING    COMMENT '客户端IP',
    event_time        TIMESTAMP COMMENT '事件发生时间',
    dq_score          INT       COMMENT '★ 数据质量评分。匿名用户-20',
    dt                STRING    COMMENT '分区键 — 日期'
)
COMMENT '清洗后的用户行为事件明细'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_user_behavior',
    'transformation' = 'clean_behavior()'
);


-- ── 3. 清洗后还款记录表 ──
CREATE TABLE IF NOT EXISTS dwd.dwd_repayment (
    repayment_id      STRING    COMMENT '还款记录ID',
    application_id    STRING    COMMENT '关联申请单号',
    user_id           STRING    COMMENT '用户ID',
    due_date          TIMESTAMP COMMENT '应还款日期',
    paid_date         TIMESTAMP COMMENT '实际还款日期',
    due_amount        DOUBLE    COMMENT '应还金额(元)。已修正: 负数→0',
    paid_amount       DOUBLE    COMMENT '实还金额(元)。已修正: 负数→0',
    status            STRING    COMMENT '还款状态(已标准化): PENDING/PAID/OVERDUE/UNKNOWN',
    dq_score          INT       COMMENT '★ 数据质量评分。金额为0-10',
    dt                STRING    COMMENT '分区键 — 日期'
)
COMMENT '清洗后的还款记录明细'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_repayment',
    'transformation' = 'clean_repayment()'
);
