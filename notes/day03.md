# Day 3 - 2026-04-24

## 今日主题

数据处理基础

## 今日目标

- 掌握pandas基础操作
- 学会SQL数据库连接
- 完成数据清洗实战项目

## 今日任务拆解

### 任务 1：pandas基础

**学习内容：**
- [ ] DataFrame创建与基本操作
- [ ] 数据读取（CSV、Excel）
- [ ] 数据选择与过滤
- [ ] 数据统计与聚合
- [ ] 数据清洗（缺失值、重复值）

### 任务 2：SQL连接

**学习内容：**
- [ ] SQLite数据库基础
- [ ] 使用sqlite3模块连接数据库
- [ ] 执行SQL查询
- [ ] 数据导入导出

### 任务 3：实战项目

**项目：招聘数据分析器**

基于Day 1收集的JD数据，完成：
- [ ] 读取JD数据（CSV格式）
- [ ] 数据清洗（处理缺失值、标准化）
- [ ] 数据分析（薪资统计、技能词频）
- [ ] 生成分析报告
- [ ] 数据存储到SQLite

## 项目结构

```
day03_data_processing/
├── main.py              # 主函数入口
├── utils/               # 工具类模块
│   ├── data_loader.py   # 数据加载器
│   ├── data_cleaner.py  # 数据清洗器
│   └── data_analyzer.py # 数据分析器
├── data/                # 原始数据
│   └── jobs.csv         # JD数据
├── output/              # 产出报告
│   ├── analysis_report.txt
│   └── jobs.db          # SQLite数据库
└── README.md            # 项目说明
```

## 建议时间安排

### 上午（09:30 - 12:00）

- 09:30 - 10:30：pandas基础学习
- 10:30 - 11:30：SQL连接学习
- 11:30 - 12:00：整理笔记

### 下午（14:00 - 18:00）

- 14:00 - 15:00：准备数据
- 15:00 - 17:00：开发分析器
- 17:00 - 18:00：测试与优化

## 今日产出物

- [ ] pandas练习代码
- [ ] SQL连接示例
- [ ] 招聘数据分析器项目
- [ ] 数据分析报告
- [ ] SQLite数据库
- [ ] Day 3学习笔记

## 注意事项

⚠️ **今天的重点：**
- pandas是数据分析的核心工具，要多练习
- SQL查询要注意防注入
- 数据清洗要考虑边界情况
- 分析结果要可视化展示

⚠️ **避免的坑：**
- pandas索引问题（iloc vs loc）
- 数据类型转换
- 缺失值处理方式
- SQL连接记得关闭

---

*开始时间：2026-04-24 上午*

---

## 📚 今日核心知识点详解

### 1️⃣ pandas基础操作

**DataFrame是什么？**
就是一张表格，像Excel一样：

```python
import pandas as pd

# 创建DataFrame（创建一张表）
df = pd.DataFrame({
    'name': ['张三', '李四', '王五'],
    'age': [25, 30, 28],
    'salary': [20, 30, 25]
})

# 结果：
#   name  age  salary
# 0  张三   25      20
# 1  李四   30      30
# 2  王五   28      25
```

**读取数据：**
```python
# 从CSV文件读取
df = pd.read_csv('data.csv')

# 从Excel读取
df = pd.read_excel('data.xlsx')
```

**查看数据：**
```python
df.head()        # 看前5行
df.tail()        # 看后5行
df.info()        # 看数据类型和缺失值
df.describe()    # 看统计信息
```

**选择数据：**
```python
# 选择一列
df['name']

# 选择多列
df[['name', 'salary']]

# 筛选行（条件过滤）
df[df['salary'] > 25]  # 薪资大于25的
```

**统计操作：**
```python
df['salary'].mean()    # 平均值
df['salary'].median()  # 中位数
df['salary'].max()     # 最大值
df['salary'].min()     # 最小值
df['salary'].sum()     # 总和
```

---

### 2️⃣ 数据清洗

**为什么要清洗？**
原始数据往往是"脏"的：
- 薪资写成 "20-35K"，不能直接计算
- 有缺失值（空白）
- 有重复数据
- 格式不统一

**字符串解析示例：**
```python
# 原始数据："20-35K"
# 目标：提取最小值20，最大值35

def parse_salary(salary_str):
    # 去掉K
    salary_str = salary_str.replace('K', '')
    
    # 分割
    if '-' in salary_str:
        parts = salary_str.split('-')
        min_sal = int(parts[0])  # 20
        max_sal = int(parts[1])  # 35
        avg_sal = (min_sal + max_sal) / 2  # 27.5
        return (min_sal, max_sal, avg_sal)
```

**应用到整列：**
```python
# 对每一行应用函数
df['salary_data'] = df['salary'].apply(parse_salary)

# 拆分成三列
df['salary_min'] = df['salary_data'].apply(lambda x: x[0])
df['salary_max'] = df['salary_data'].apply(lambda x: x[1])
df['salary_avg'] = df['salary_data'].apply(lambda x: x[2])
```

**处理缺失值：**
```python
# 查看缺失值
df.isnull().sum()

# 删除有缺失值的行
df.dropna()

# 填充缺失值
df.fillna(0)
```

**去重：**
```python
# 删除完全重复的行
df.drop_duplicates()
```

---

### 3️⃣ 数据分析

**分组统计：**
```python
# 按城市分组，计算平均薪资
df.groupby('city')['salary_avg'].mean()

# 结果：
# city
# 北京    27.5
# 上海    31.0
# 深圳    27.5
```

**计数统计：**
```python
# 统计每个城市有多少岗位
df['city'].value_counts()

# 结果：
# 北京    5
# 上海    2
# 深圳    2
```

**词频统计：**
```python
from collections import Counter

# 假设技能列表：[['Python', 'SQL'], ['Python', 'RAG'], ...]
all_skills = []
for skills in df['skills_list']:
    all_skills.extend(skills)

# 统计词频
skill_counter = Counter(all_skills)
skill_counter.most_common(5)  # Top 5

# 结果：
# [('Python', 10), ('SQL', 4), ('RAG', 4), ...]
```

**聚合操作：**
```python
# 多种统计一起做
df.groupby('city').agg({
    'salary_avg': ['mean', 'min', 'max'],
    'position': 'count'
})
```

---

### 4️⃣ SQLite数据库

**为什么用数据库？**
- CSV文件大了会慢
- 数据库可以快速查询
- 支持复杂的SQL操作

**连接数据库：**
```python
import sqlite3

# 连接（如果不存在会自动创建）
conn = sqlite3.connect('jobs.db')
```

**保存数据到数据库：**
```python
# pandas直接保存
df.to_sql('jobs', conn, if_exists='replace', index=False)

# if_exists参数：
# - 'fail': 表存在就报错
# - 'replace': 删除旧表，创建新表
# - 'append': 追加数据
```

**查询数据：**
```python
# 执行SQL查询
sql = "SELECT * FROM jobs WHERE city='北京'"
df_result = pd.read_sql_query(sql, conn)
```

**关闭连接：**
```python
conn.close()
```

**使用上下文管理器（推荐）：**
```python
with sqlite3.connect('jobs.db') as conn:
    df.to_sql('jobs', conn, if_exists='replace')
    # 自动关闭连接
```

---

### 5️⃣ 完整数据处理流程

**实际工作中的流程：**

```
原始数据 → 加载 → 清洗 → 分析 → 存储 → 报告
```

**代码示例：**
```python
# 1. 加载数据
df = pd.read_csv('jobs.csv')

# 2. 数据清洗
df['salary_avg'] = df['salary'].apply(parse_salary)
df = df.dropna()
df = df.drop_duplicates()

# 3. 数据分析
avg_salary = df['salary_avg'].mean()
city_dist = df['city'].value_counts()

# 4. 保存到数据库
with sqlite3.connect('jobs.db') as conn:
    df.to_sql('jobs', conn, if_exists='replace')

# 5. 生成报告
print(f"平均薪资: {avg_salary}K")
print(f"城市分布:\n{city_dist}")
```

---

## 💡 关键概念总结

| 概念 | 大白话 | 代码示例 |
|---|---|---|
| DataFrame | 一张表格 | `pd.DataFrame()` |
| 读取CSV | 从文件加载数据 | `pd.read_csv()` |
| 选择列 | 拿出某一列 | `df['name']` |
| 筛选行 | 按条件过滤 | `df[df['age'] > 25]` |
| apply | 对每行应用函数 | `df['col'].apply(func)` |
| groupby | 分组统计 | `df.groupby('city')` |
| value_counts | 计数 | `df['city'].value_counts()` |
| to_sql | 保存到数据库 | `df.to_sql('table', conn)` |
| read_sql_query | SQL查询 | `pd.read_sql_query(sql, conn)` |

---

## 📊 今日实战成果

### 项目：招聘数据分析器

**数据来源：** Day 1收集的10个JD数据

**分析结果：**
- 平均薪资：28.1K（范围24-31K）
- 城市分布：北京50%，上海20%，深圳20%
- 岗位方向：RAG/NL2SQL占50%，AI应用40%
- 核心技能：Python 100%，LLM/RAG/SQL 40%

**产出文件：**
- `output/analysis_report.txt` - 完整分析报告
- `output/jobs.db` - SQLite数据库

---

## 🎯 今日收获

**技术能力：**
- ✅ 掌握pandas基础操作
- ✅ 学会数据清洗技巧
- ✅ 完成数据统计分析
- ✅ 使用SQLite存储数据
- ✅ 走通完整数据处理流程

**工程能力：**
- ✅ 专业项目结构（工具类分离）
- ✅ 代码模块化设计
- ✅ 数据处理流程化
- ✅ 生成可视化报告

---

*完成时间：2026-04-24 下午*
