-- ============================================================
-- ADS 层 DDL — 应用数据层
-- 原则: 预聚合、即查即用。直接服务上层应用
-- ============================================================

-- ── 1. 模型训练样本集 ──
CREATE TABLE IF NOT EXISTS ads.ads_training_samples (
    -- DWS 宽表的全部 17 维特征
    user_id              STRING    COMMENT '用户ID',
    apply_amount_avg     DOUBLE    COMMENT '← DWS宽表特征',
    apply_amount_max     DOUBLE,
    monthly_income       DOUBLE,
    total_apply_cnt      INT,
    distinct_device_cnt  INT,
    distinct_city_cnt    INT,
    apply_cnt_7d         INT,
    apply_cnt_30d        INT,
    night_ops_ratio_30d  DOUBLE,
    page_view_cnt_7d     INT,
    input_cnt_7d         INT,
    error_event_cnt_7d   INT,
    overdue_cnt_hist     INT,
    total_due_amount     DOUBLE,
    total_paid_amount    DOUBLE,
    repayment_cnt        INT,
    on_time_rate         DOUBLE,

    -- ★ 标签列
    label                INT       COMMENT '★ 逾期标签。0=好样本(正常还款), 1=坏样本(DPD30+逾期)。XGBoost的y',
    label_date           STRING    COMMENT '标签观察日期 = dt + 30天',

    -- 分区
    dt                   STRING    COMMENT '分区键 — 特征快照日期'
)
COMMENT '模型训练样本集 — DWS宽表 + T+30逾期标签。严格遵守PIT原则'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'pit_principle' = 'dt_特征 < dt_标签 — 严禁时间泄漏',
    'label_definition' = 'T+30 DPD30+ 逾期',
    'positive_sample_rate_target' = '10-15%'
);


-- ── 2. 模型监控日报 ──
CREATE TABLE IF NOT EXISTS ads.ads_model_monitor_daily (
    dt                   STRING    COMMENT '统计日期',
    total_applications   INT       COMMENT '当日总申请数',
    approval_rate        DOUBLE    COMMENT '通过率 = APPROVE/总数',
    reject_rate          DOUBLE    COMMENT '拒绝率',
    manual_review_rate   DOUBLE    COMMENT '人工审核率。>20%→模型区分力不足',
    avg_score            DOUBLE    COMMENT '平均信用评分(300-900)',
    score_std            DOUBLE    COMMENT '评分标准差',
    score_p10            DOUBLE    COMMENT '评分P10分位数',
    score_p50            DOUBLE    COMMENT '评分中位数',
    score_p90            DOUBLE    COMMENT '评分P90分位数',
    avg_credit_limit     DOUBLE    COMMENT '平均授信额度(元)',
    avg_latency_ms       DOUBLE    COMMENT '平均推理延迟(ms)。>300→告警'
)
COMMENT '模型监控日报 — Grafana直接消费。每日一条记录'
STORED AS parquet
TBLPROPERTIES (
    'consumer' = 'Grafana',
    'alert_approval_rate' = '>0.90 OR <0.30 → WARNING',
    'alert_latency' = '>300ms → CRITICAL',
    'alert_manual_review' = '>0.20 → WARNING'
);


-- ── 3. 资产组合分析（JSON格式）──
CREATE TABLE IF NOT EXISTS ads.ads_portfolio_analysis (
    dt                   STRING    COMMENT '统计日期',
    report_json          STRING    COMMENT '资产组合分析JSON: {total_portfolio, total_credit_exposure, score_distribution, ...}'
)
COMMENT '资产组合分析 — JSON格式,供风控报表/BI消费'
STORED AS parquet;
