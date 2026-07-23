---
id: L050
source: learning
category: 数据仓库
title: 请讲讲数据血缘 + SchemaRegistry 元数据管理中的动手练习：为 SchemaRegistry 添加新功能（1h）
generated: 2026-07-23T15:41:19.864870
---

# 请讲讲数据血缘 + SchemaRegistry 元数据管理中的动手练习：为 SchemaRegistry 添加新功能（1h）

> 来源: 学习复习计划 | 分类: 数据仓库

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