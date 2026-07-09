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

# TODO: 完成以下 5 张表
教育_ODS_TABLES = {
    "ods_user":        ODSTable(...),  # 来自 MySQL
    "ods_course":      ODSTable(...),  # 来自 MySQL
    "ods_order":       ODSTable(...),  # 来自 MySQL（购买课程）
    "ods_watch_behavior": ODSTable(...),  # 来自埋点 SDK
    "ods_exam_result": ODSTable(...),  # 来自日志文件
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

    # TODO: 实现清洗逻辑

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
    # 1. 三路分别 groupby
    # 2. left join
    # 3. fillna(0)
    pass
```

### 任务 4：分区策略（15min）

```
1. 分区键选什么？所有表统一 dt 吗？
2. 观看行为表: 日增 1000 万条 → 保留多久？
3. 考试结果表: 日增 10 万条 → 需要保留多久（学业记录可能永久保存）？
4. 是否需要二级分区（如按课程类别）？
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
