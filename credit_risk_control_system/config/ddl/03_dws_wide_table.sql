-- ============================================================
-- DWS 层 DDL — 用户风险特征宽表 ★ 核心
--
-- 粒度: 用户 × 日期 (user_id + dt 为联合主键)
-- 来源: dwd_application + dwd_user_behavior + dwd_repayment
--       三表 left join 聚合
--
-- 特征总数: 17维 (画像6 + 行为6 + 还款5)
-- ============================================================

CREATE TABLE IF NOT EXISTS dws.user_risk_feature_wide (
    -- ═══ 主键 ═══
    user_id              STRING    COMMENT '用户唯一标识',

    -- ═══ 申请行为画像 (6维) ← dwd.dwd_application ═══
    apply_amount_avg     DOUBLE    COMMENT '历史平均申请金额(元)。AVG(apply_amount)',
    apply_amount_max     DOUBLE    COMMENT '历史最大申请金额(元)。MAX(apply_amount)',
    monthly_income       DOUBLE    COMMENT '月收入(元)。多次申请取MAX',
    total_apply_cnt      INT       COMMENT '历史总申请次数。COUNT DISTINCT(application_id)',
    distinct_device_cnt  INT       COMMENT '关联不同设备数。>2→账号可能被盗。COUNT DISTINCT(device_id)',
    distinct_city_cnt    INT       COMMENT '关联不同城市数。频繁跨城→异常。COUNT DISTINCT(city)',

    -- ═══ 行为衍生特征 (6维) ← dwd.dwd_user_behavior + 时间窗口滑动 ═══
    apply_cnt_7d         INT       COMMENT '近7天提交申请次数。SUM(submit WHERE t>=ref-7d)',
    apply_cnt_30d        INT       COMMENT '近30天提交申请次数。SUM(submit WHERE t>=ref-30d)',
    night_ops_ratio_30d  DOUBLE    COMMENT '★ 近30天深夜操作占比(22-05时)。风控强特征。>60%→高度可疑',
    page_view_cnt_7d     INT       COMMENT '近7天页面浏览次数。SUM(page_view WHERE t>=ref-7d)',
    input_cnt_7d         INT       COMMENT '近7天输入次数。极低→可能是脚本。SUM(input WHERE t>=ref-7d)',
    error_event_cnt_7d   INT       COMMENT '近7天错误事件次数。频繁报错→异常。SUM(error WHERE t>=ref-7d)',

    -- ═══ 还款表现特征 (5维) ← dwd.dwd_repayment ═══
    overdue_cnt_hist     INT       COMMENT '★ 历史逾期次数。最直接的还款意愿指标。SUM(OVERDUE)',
    total_due_amount     DOUBLE    COMMENT '历史总应还金额(元)。SUM(due_amount)',
    total_paid_amount    DOUBLE    COMMENT '历史总实还金额(元)。SUM(paid_amount)。远低于due→逾期严重',
    repayment_cnt        INT       COMMENT '总还款笔数。用于计算on_time_rate的分母。COUNT(repayment_id)',
    on_time_rate         DOUBLE    COMMENT '★ 按时还款率=1-逾期次/总次。新用户=1.0。3笔2逾期→0.33→高风险',

    -- ═══ 分区 ═══
    dt                   STRING    COMMENT '分区键 — 特征快照日期 YYYY-MM-DD'
)
COMMENT '★ 用户风险特征宽表 — 每行=一个用户在某天的完整风险画像'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'grain' = 'user × date',
    'feature_count' = '17',
    'feature_categories' = 'profile(6) + behavior(6) + repayment(5)',
    'source_tables' = 'dwd.dwd_application, dwd.dwd_user_behavior, dwd.dwd_repayment',
    'join_type' = 'LEFT JOIN — 保证新用户不丢数据',
    'null_fill_policy' = 'fillna(0) — 无行为/无还款→特征为0',
    'on_time_rate_default' = '1.0 — 新用户无罪推定',
    'pit_principle' = '所有时间窗口以dt为基准向后推算 — 不使用未来信息'
);
