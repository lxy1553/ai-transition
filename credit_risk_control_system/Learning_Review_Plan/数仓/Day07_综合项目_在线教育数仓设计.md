# Day 07：综合项目 — 为在线教育平台设计完整数仓

> 目标：综合运用 6 天所学，为全新业务独立设计数据仓库。

---

## 一、业务理解（30min）

```
业务: 在线教育平台 "LearnFast"

核心业务:
  - 学生: 观看视频课程、做练习题、参加考试、发表评论
  - 老师: 发布课程、批改作业、回复评论
  - 管理员: 看日报、分析课程质量

数据源:
  - MySQL: 用户表、课程表、订单表（购买课程）
  - 埋点 SDK: 观看行为（播放/暂停/快进/完成）、做题行为
  - 日志文件: 考试系统的答题记录（CSV 格式）
  - 第三方 API: 支付回调、短信通知记录
```

---

## 二、设计任务（2h）

### 任务 1：ODS 层（20min）

定义 5 张 ODS 表，使用 `ODSTable` dataclass：

```python
from dataclasses import dataclass

@dataclass
class ODSTable:
    name: str
    source_system: str
    ingest_method: str    # binlog / sdk / file / api_log
    partition_key: str = "dt"
    description: str = ""

# ★ 参考答案
教育_ODS_TABLES = {
    "ods_user": ODSTable(
        name="ods_user",
        source_system="mysql_user_center",
        ingest_method="binlog",
        description="用户表(学生/老师)。来自MySQL用户中心",
    ),
    "ods_course": ODSTable(
        name="ods_course",
        source_system="mysql_course_center",
        ingest_method="binlog",
        description="课程表。来自MySQL课程中心",
    ),
    "ods_order": ODSTable(
        name="ods_order",
        source_system="mysql_payment",
        ingest_method="binlog",
        description="课程购买订单表。来自支付系统",
    ),
    "ods_watch_behavior": ODSTable(
        name="ods_watch_behavior",
        source_system="sdk_analytics",
        ingest_method="sdk",
        description="观看行为埋点。SDK实时上报",
    ),
    "ods_exam_result": ODSTable(
        name="ods_exam_result",
        source_system="exam_system",
        ingest_method="file",
        description="考试结果。来自考试系统CSV日志",
    ),
}
```

### 任务 2：DWD 层 — 清洗观看行为表（30min）

```python
def clean_watch_behavior(ods_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    清洗规则:
    1. user_id/video_id 为空 → 扣 30 分
    2. watch_duration < 0 或 > video_duration*3 → 扣 20 分（作弊刷时长？）
    3. 视频状态标准化: play/pause/seek/complete/error → 标准枚举
    4. user_id 脱敏（如果涉及 PII）
    5. dq_score < 60 → 隔离
    """
    df = ods_df.copy()
    df['dq_score'] = 100

    # ★ 参考答案
    # 1. 必填检查
    df.loc[df['user_id'].isna() | df['video_id'].isna(), 'dq_score'] -= 30
    # 2. 时长异常
    df.loc[df['watch_duration'] < 0, 'dq_score'] -= 20
    # 3. 状态标准化
    valid_status = {'play', 'pause', 'seek', 'complete', 'error'}
    df['status'] = df['status'].fillna('unknown')
    df.loc[~df['status'].isin(valid_status), 'status'] = 'unknown'
    # 4. 脱敏
    df['user_id'] = df['user_id'].apply(lambda x: x)  # 生产中用hash

    df_clean = df[df['dq_score'] >= 60]
    report = {"total": len(df), "passed": len(df_clean),
              "quarantined": len(df) - len(df_clean)}
    return df_clean, report
```

### 任务 3：DWS 层 — 学生学习画像宽表（40min）

```python
def build_student_profile_wide_table(
    dwd_order,          # 购买记录
    dwd_watch_behavior, # 观看行为
    dwd_exam_result,    # 考试结果
    dt: str,
) -> pd.DataFrame:
    """
    粒度: 学生 × 日期
    要求至少 10 个特征:

    购买画像(3个): 总购买课程数、总消费金额、最近购买距今天数
    学习行为(4个): 近7天观看视频数、近7天观看总时长(分钟)、
                  平均完成率(completed/total_watch)、跳过率(seek/total_watch)
    考试表现(3个): 近30天考试次数、平均得分、通过率

    关键设计决策:
    - 聚合函数选择: 为什么平均完成率用 mean 而不是 sum？
    - left join or inner join: 新学生没有考试记录怎么办？
    """
    # ★ 参考答案
    # 1. 购买画像聚合
    order_agg = dwd_order.groupby('user_id').agg(
        total_courses=('course_id', 'nunique'),
        total_spend=('amount', 'sum'),
        days_since_last_purchase=('purchase_time', lambda x:
            (pd.to_datetime(dt) - x.max()).days),
    ).reset_index()

    # 2. 观看行为聚合
    in_7d = dwd_watch_behavior['watch_time'] >= pd.to_datetime(dt) - timedelta(days=7)
    watch_7d = dwd_watch_behavior[in_7d].groupby('user_id').agg(
        video_watched_7d=('video_id', 'nunique'),
        total_watch_minutes_7d=('duration_sec', lambda x: x.sum() / 60),
        completion_rate=('is_complete', 'mean'),
        skip_rate=('event_type', lambda x: (x == 'seek').mean()),
    ).reset_index()

    # 3. 考试表现聚合
    exam_agg = dwd_exam_result[dwd_exam_result['exam_time'] >=
                               pd.to_datetime(dt) - timedelta(days=30)].groupby('user_id').agg(
        exam_cnt_30d=('exam_id', 'nunique'),
        avg_score=('score', 'mean'),
        pass_rate=('is_pass', 'mean'),
    ).reset_index()

    # 4. left join + fillna（新学生无考试记录→fillna(0)）
    wide = order_agg.merge(watch_7d, on='user_id', how='left') \
                    .merge(exam_agg, on='user_id', how='left')
    numeric_cols = wide.select_dtypes(include=[np.number]).columns
    wide[numeric_cols] = wide[numeric_cols].fillna(0)

    return wide
```

### 任务 4：分区策略（15min）

```
★ 参考答案

1. 分区键: 统一 dt 日期分区
   所有表按 dt 分区 → ETL 统一按天调度

2. 观看行为: 保留 30 天
   日增 1000 万，按天分区后每天 1000 万行可管理
   超过 30 天的用户行为数据价值低

3. 考试结果: 永久保留（学业记录）
   但需要冷热分离:
   - 活跃数据(2年): Parquet 保留在 HDFS
   - 历史数据(2年+): 压缩归档到对象存储(S3/OSS)

4. 二级分区:
   课程类别可以作为二级分区 → 优化"按课程查"场景
   但只在 DWS/ADS 层加，ODS/DWD 不用（保持简单）
```

### 任务 5：PII 脱敏（15min）

```
教育平台的敏感数据:
  - 学生姓名 / 手机号
  - 老师身份证（提现需要实名认证）
  - 支付信息
  - 考试分数（属于个人隐私，GDPR 保护范围）

为每个字段选脱敏策略（Mask/Hash/Generalize/Encrypt）并写理由
```

### 任务 6：ADS 数据产品（20min）

设计 2 个数据产品：

```
产品 1: 学习效果预测训练样本
  - 消费者: ML 模型训练（预测学生是否会中途退课）
  - 格式: Parquet
  - 结构: DWS 宽表 + label (30天后是否退课)
  - PIT 约束: 特征时间 < 标签时间

产品 2: 课程质量日报
  - 消费者: 运营看板 / Grafana
  - 格式: CSV
  - 粒度: 课程 × 日期
  - 指标: 观看人数、平均完成率、平均评分、退课率
```

---

## 三、自评表（20min）

| 能力 | 自评(1-5) | 在线教育项目中的体现 |
|------|---------|-------------------|
| 分层架构 | | 定义了 4 层 + ODS 5 张表 |
| 数据质量 | | 设计了观看行为表的扣分规则 |
| 维度建模 | | 设计了学生学习画像 10+ 特征宽表 |
| 血缘管理 | | — （本练习未涉及） |
| PII 脱敏 | | 设计了教育数据的脱敏策略 |
| 分区策略 | | 设计了不同表的分区和保留期 |
| 数据产品 | | 设计了训练样本 + 课程日报 |

---

## 四、产出物

- [ ] ODS 5 张表定义（Python dataclass）
- [ ] `clean_watch_behavior()` 清洗函数
- [ ] `build_student_profile_wide_table()` 宽表构建
- [ ] 分区 + 脱敏策略文档
- [ ] 2 个 ADS 数据产品设计
