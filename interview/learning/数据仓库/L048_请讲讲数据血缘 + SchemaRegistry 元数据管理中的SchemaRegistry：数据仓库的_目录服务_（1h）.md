---
id: L048
source: learning
category: 数据仓库
title: 请讲讲数据血缘 + SchemaRegistry 元数据管理中的SchemaRegistry：数据仓库的"目录服务"（1h）
generated: 2026-07-23T15:41:19.864453
---

# 请讲讲数据血缘 + SchemaRegistry 元数据管理中的SchemaRegistry：数据仓库的"目录服务"（1h）

> 来源: 学习复习计划 | 分类: 数据仓库

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