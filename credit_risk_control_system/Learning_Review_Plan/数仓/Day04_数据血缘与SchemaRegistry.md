# Day 04：数据血缘 + SchemaRegistry 元数据管理

> 目标：理解元数据驱动的数据仓库管理，能手写 SchemaRegistry 的核心功能。

---

## 一、没有血缘的数仓 = 没有地图的城市（20min）

```
场景：DWD 层的 apply_amount 列类型从 INT 改成 DOUBLE
  问题：哪些下游表会受影响？

有血缘 → 秒级溯源:
  apply_amount (dwd_application)
    → apply_amount_avg (dws.user_risk_feature_wide)
      → 训练样本表 ads_training_samples
        → XGBoost 模型的特征列
  结论：模型需要重训，因为特征类型变了

没有血缘 → 灾难:
  让各团队自己去排查 → 3 天后才发现模型评分异常
```

---

## 二、SchemaRegistry：数据仓库的"目录服务"（1h）

### 2.1 核心代码

打开 `src/data/schema_registry.py`：

```python
class SchemaRegistry:
    """
    三大职责:
    1. 加载: 从 config/schemas/*.yaml 读取表结构
    2. 写入: 执行 ETL 时将 _TABLE_SCHEMA.json 写入数据目录
    3. 查询: 提供统一的 get_table() / list_tables() 接口
    """

    def __init__(self, config_dir: str = "config"):
        self._tables: dict[str, TableSchema] = {}  # 核心: 内存中的表目录
        self._load_all()  # 启动时一次性加载所有 schema

    # ═══ 职责1: 加载 YAML 配置 ═══
    def _load_dws(self):
        """加载 DWS 宽表的 schema"""
        path = self.schemas_dir / "dws_wide_table.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)

        for cat_key in ['category_profile', 'category_behavior',
                         'category_repayment']:
            for feat in data['wide_table'][cat_key]['features']:
                columns.append(ColumnDef(
                    name=feat['name'],
                    type=feat.get('type', 'STRING'),
                    description=feat.get('description', ''),
                    aggregation=feat.get('aggregation', ''),  # ← 聚合公式
                    risk_direction=feat.get('risk_direction', ''),  # ← 风险方向
                ))

    # ═══ 职责2: 写入数据目录 ═══
    def write_schema_to_data_dir(self, data_dir, table_name, layer):
        """
        将 _TABLE_SCHEMA_{table}.json 写入数据目录。

        为什么数据目录需要自带 schema？
        - Parquet 有列名和类型，但没有 COMMENT（业务含义）
        - COMMENT 是数仓工程师写的 "近30天深夜操作占比>60%→可疑"
        - 数据被复制/迁移时，schema 跟随 → 知识不丢失
        """
        path = Path(data_dir) / f"_TABLE_SCHEMA_{table_name}.json"
        json.dump(schema.to_dict(), open(path, 'w'), indent=2)

    # ═══ 职责3: 统一查询 ═══
    def get_table(self, layer, table_name):
        return self._tables.get(f"{layer}.{table_name}")

    def list_tables(self, layer=None):
        tables = list(self._tables.values())
        return [t for t in tables if not layer or t.layer == layer]
```

### 2.2 运行验证

```bash
cd credit_risk_control_system
python3 -c "
from src.data.schema_registry import SchemaRegistry
r = SchemaRegistry()
print(r.print_summary())
print()
# 查一张具体的表
t = r.get_table('dws', 'user_risk_feature_wide')
print(f'宽表: {t.table_name}, {len(t.columns)}列, 主键={t.primary_key}')
for c in t.columns[:3]:
    print(f'  {c.name}: {c.type} — {c.description[:50]}...')
"
```

---

## 三、数据血缘：每列追溯来源（40min）

### 3.1 血缘的两种形态

打开 `config/schemas/data_lineage.yaml`：

```yaml
# 形态1: 层间流转（表级血缘）
lineage:
  ods_to_dwd:
    - source: ods_application
      target: dwd_application
      relationship: "1:1 + 新增 dq_score 列"

  dwd_to_dws:
    - sources: [dwd_application, dwd_behavior, dwd_repayment]
      target: dws.user_risk_feature_wide
      relationship: "N:1 聚合"

# 形态2: 宽表列追溯（列级血缘）
wide_table_lineage:
  night_ops_ratio_30d:
    source_column: dwd_user_behavior.event_time
    aggregation: "AVG(hour IN 22-05) WHERE event_time >= ref-30d"

  on_time_rate:
    source_columns: [dwd_repayment.status, dwd_repayment.repayment_id]
    aggregation: "1 - SUM(OVERDUE) / COUNT(*)"
```

### 3.2 一个特征的完整追溯路径

```
night_ops_ratio_30d = 0.27
  ↑ DWS 聚合: AVG(hour IN [22,23,0,1,2,3,4,5]) 时间窗口30天
  ← dwd_user_behavior.event_time
    ↑ DWD 继承自 ODS（未转换）
    ← ods_user_behavior.event_time
      ↑ SDK 上报
      ← 客户端 App 埋点代码: trackEvent('page_view', timestamp=now())
```

### 3.3 练习：画一条血缘链（20min）

在纸上画出 `on_time_rate` 的完整血缘链：

```
on_time_rate = 1 - overdue_cnt_hist / repayment_cnt

overdue_cnt_hist 的来源: → ... → 一直追溯到 App 的还款页面
repayment_cnt 的来源: → ... → 一直追溯到 MySQL 还款表的 repayment_id
```

---

## 四、动手练习：为 SchemaRegistry 添加新功能（1h）

```python
# 为 src/data/schema_registry.py 添加一个校验方法

def validate_dataframe(self, layer: str, table_name: str,
                       df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    校验 DataFrame 是否与注册的 schema 一致。

    检查项:
    1. 是否有多余的列（不在 schema 中）
    2. 是否有缺失的必填列
    3. 必填列是否有空值

    返回: (是否通过, [错误列表])
    """
    schema = self.get_table(layer, table_name)
    if schema is None:
        return False, [f"表 {layer}.{table_name} 未注册"]

    errors = []
    schema_cols = {c.name for c in schema.columns}
    df_cols = set(df.columns)

    # 多余列
    extra = df_cols - schema_cols
    if extra:
        errors.append(f"多余列: {extra}")

    # 缺少的必填列
    required = {c.name for c in schema.columns if not c.nullable}
    missing = required - df_cols
    if missing:
        errors.append(f"缺少必填列: {missing}")

    # 必填列空值检查
    for col in required & df_cols:
        null_count = df[col].isna().sum()
        if null_count > 0:
            errors.append(f"列 {col} 有 {null_count} 个空值")

    return len(errors) == 0, errors


# 测试
import pandas as pd
r = SchemaRegistry()
df = pd.DataFrame({
    'user_id': ['u1', 'u2', None],  # ← 有空值
    'apply_amount': [1000, 2000, 3000],
    'extra_col': [1, 2, 3],         # ← schema 中没有的列
})
ok, errors = r.validate_dataframe('ods', 'ods_application', df)
print(f"通过: {ok}")
for e in errors:
    print(f"  - {e}")
```

---

## 五、今天要点

```
SchemaRegistry 的三个价值:
  1. 代码可消费: NL2SQL 可以直接读 schema 构造 LLM Prompt
  2. 数据可自描述: 数据目录下的 _TABLE_SCHEMA.json 让别人也能读懂
  3. 变更可追溯: schema 和代码一起用 git 管理

数据血缘的两种形态:
  1. 表级: 层与层之间的流转关系（哪张 DWD 表生成了哪张 DWS 表）
  2. 列级: 每个特征追溯到 DWD 源列和聚合公式
```

---

## 六、检查清单

- [ ] 能解释 SchemaRegistry 的三个职责
- [ ] 运行过 SchemaRegistry.print_summary() 看所有表
- [ ] 实现了 validate_dataframe() 方法
- [ ] 能画出 night_ops_ratio_30d 的完整血缘链
- [ ] 理解了 COMMENT 注释对 NL2SQL 的价值（回顾 AI Day02）
