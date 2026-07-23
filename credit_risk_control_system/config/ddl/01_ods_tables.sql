-- ============================================================
-- ODS 层 DDL — 原始数据层
-- 存储引擎: Apache Iceberg (生产) / Parquet (本地模拟)
-- 分区策略: dt (日期分区, YYYY-MM-DD)
-- ============================================================

-- ── 1. 用户申请表 ──
CREATE TABLE IF NOT EXISTS ods.ods_application (
    user_id           STRING    COMMENT '用户唯一标识',
    application_id    STRING    COMMENT '申请单号',
    apply_amount      DOUBLE    COMMENT '申请金额(元)。含脏数据: 负数/0/NULL',
    product_type      STRING    COMMENT '产品类型原始值。含NULL/异常枚举',
    user_name         STRING    COMMENT '★ 用户真实姓名(明文PII)',
    id_card           STRING    COMMENT '★ 身份证号(明文PII)',
    phone             STRING    COMMENT '★ 手机号(明文PII)',
    occupation        STRING    COMMENT '职业。原始值',
    monthly_income    DOUBLE    COMMENT '月收入(元)。可能为0/NULL',
    education         STRING    COMMENT '学历',
    city              STRING    COMMENT '所在城市',
    ip_address        STRING    COMMENT '★ 客户端IP(明文PII)',
    device_id         STRING    COMMENT '设备指纹ID',
    channel           STRING    COMMENT '渠道: app_android/app_ios/h5/partner_a/partner_b',
    apply_time        TIMESTAMP COMMENT '申请提交时间',
    dt                STRING    COMMENT '分区键 — 申请日期'
)
COMMENT '用户贷款申请表 — 1:1镜像MySQL信贷核心库binlog'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_system' = 'mysql_credit_core',
    'ingest_method' = 'binlog',
    'pii_columns' = 'user_name,id_card,phone,ip_address',
    'retention_days' = '90'
);


-- ── 2. 用户行为埋点表 ──
CREATE TABLE IF NOT EXISTS ods.ods_user_behavior (
    user_id           STRING    COMMENT '用户ID。未登录用户为NULL或anonymous',
    event_type        STRING    COMMENT '事件类型: page_view/click/input/submit/app_install/app_uninstall/error',
    event_detail      STRING    COMMENT '事件详情JSON: {x, y, duration_ms, ...}',
    device_id         STRING    COMMENT '设备指纹ID',
    session_id        STRING    COMMENT '会话ID。可能为NULL',
    page_url          STRING    COMMENT '页面路径: /apply, /products等',
    ip                STRING    COMMENT '客户端IP(PII)',
    event_time        TIMESTAMP COMMENT '事件发生时间(客户端时间戳)',
    dt                STRING    COMMENT '分区键 — 事件日期'
)
COMMENT '用户行为埋点流 — SDK实时上报'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_system' = 'sdk_analytics',
    'ingest_method' = 'sdk',
    'pii_columns' = 'ip',
    'retention_days' = '30'
);


-- ── 3. 还款记录表 ──
CREATE TABLE IF NOT EXISTS ods.ods_repayment (
    repayment_id      STRING    COMMENT '还款记录唯一ID',
    application_id    STRING    COMMENT '关联申请单号',
    user_id           STRING    COMMENT '用户ID',
    due_date          TIMESTAMP COMMENT '应还款日期',
    paid_date         TIMESTAMP COMMENT '实际还款日期。未还则为NULL',
    due_amount        DOUBLE    COMMENT '应还金额(元)',
    paid_amount       DOUBLE    COMMENT '实还金额(元)。可能为NULL',
    status            STRING    COMMENT '还款状态原始值: pending/paid/overdue',
    dt                STRING    COMMENT '分区键 — 日期'
)
COMMENT '还款计划与还款记录 — binlog同步'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_system' = 'mysql_credit_core',
    'ingest_method' = 'binlog',
    'retention_days' = '365'
);
