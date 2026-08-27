# QueryForge 阶段 B：评测实验方法论

> **这是"怎么验证 RAG 有没有用"**——A/B 对比 + 难度分桶 + 消融。
> 对比你 ai_assistant：你的 eval_qa.py 只跑准确率，QueryForge 有 A/B + 消融（能证明"加 X 有没有用"）。
>
> **代码位置**：`eval/`（ex_eval.py + ab_eval.py + rag_ablation_eval.py + hardness.py + ragas_eval.py）

---

## 三问

- **Q1 解决什么问题**：不只"准确率多少"，还要"加 RAG 有没有用""哪类语料最有用""难的问题掉哪"
- **Q2 数据流哪一环**：独立于服务——离线跑评测，衡量链路好坏 + 验证改动
- **Q3 删掉会怎样**：无法量化效果，改坏不知道，面试说不出数字

---

## 一、基础：执行准确率 + 难度分桶（ex_eval.py）

### 执行准确率（结果集比较）

```python
def _normalize_rows(rows) -> set:
    """把结果集转成可比较的集合（每行排序后转 tuple，规避列序差异）"""
    return {tuple(sorted(map(str, r))) for r in rows}

# 对每个测试问题：
resp = await run_query(...)            # 系统生成的 SQL 执行
gold = await execute(db_id, gold_sql)  # gold SQL 执行
pred = _normalize_rows(resp.rows)      # 预测结果集
match = pred == gold                   # ★ 结果集一致 = 对
```

**大白话**：SQL 写法可以不同，但**结果集一样就算对**——测效果，不测写法。

### 难度分桶（定位短板）

```python
# eval/hardness.py —— SQL 难度分级（easy/medium/hard/extra）
def sql_hardness(sql, dialect="sqlite") -> str:
    tree = sqlglot.parse_one(sql)
    # 集合操作/嵌套子查询 → extra
    if list(tree.find_all(exp.Union, exp.Intersect, exp.Except)):
        return "extra"
    # 多子查询 → extra
    if len([s for s in tree.find_all(exp.Select)]) > 1:
        return "extra"
    joins = len(list(tree.find_all(exp.Join)))
    # 2+ JOIN 或 JOIN+GROUP+HAVING → hard
    if joins >= 2 or (joins >= 1 and has_group and has_having):
        return "hard"
    # 1 JOIN 或 GROUP/HAVING → medium
    if joins == 1 or has_group or has_having:
        return "medium"
    return "easy"
```

**大白话**：按 SQL 复杂度分档（简单/中等/难/超难）。**各桶算准确率 → 看出哪类问题掉点**（如简单 90%、超难 30% = 短板在复杂查询）。

---

## 二、A/B 评测：RAG 有没有用（ab_eval.py）

### 核心：同一批问题，两条路径对比

```python
async def evaluate(db_id, limit, seed):
    examples = load_examples("dev")   # 同一批 CSpider 题

    for ex in examples:
        # 路径 1：RAG（完整链路：检索+重排+few-shot+自纠错）
        rag = await run_query(QueryRequest(question=q, db_id=db_id))
        # 路径 2：noRAG（整库 schema + 单次生成）
        norag = await run_query_no_rag(q, db_id)

        # 都跟 gold 结果集比
        rag_m = _normalize_rows(rag.rows) == gold
        norag_m = _normalize_rows(norag.rows) == gold

        # 按难度分桶记录两条路径的准确率
        buckets[level] = {"total": +1, "rag": +rag_m, "norag": +norag_m}
```

**大白话**：同一批题，RAG 链路跑一遍、noRAG 链路跑一遍，都跟标准答案比。**得出"RAG 比 noRAG 准多少"**。

### README 实验结论（真实数据）

| 实验 | RAG | noRAG | 结论 |
|------|-----|-------|------|
| 单库 concert_singer | 0.889 | 0.800 | RAG 明显收益 |
| 单库 cre_Doc_Template | 0.940 | 0.880 | 中等难度收益明显 |
| 跨库 100 题 | 0.760 | 0.780 | **RAG 不一定提升** |

**大白话**：**RAG 不是万能的**——单库明显收益，跨库小样本反而不稳定。**加 RAG 要 A/B 验证**。

---

## 三、RAG 消融：哪类语料最有用（rag_ablation_eval.py）

```python
# 分别去掉 schema / few-shot / docs，看准确率变化
# 找"哪类语料贡献最大"
```

**README 结论**：
| 配置 | 准确率 |
|------|--------|
| schema_fewshot | 0.790 |
| full_rag | 0.750 |

**大白话**：**few-shot（NL→SQL 示例）是最稳定收益来源**，full RAG 不一定最优。**这提醒你：ai_assistant 加 RAG 时，few-shot 示例优先**。

---

## 四、检索质量评测（ragas_eval.py）

```python
# 用 ragas 评检索质量（context_precision/recall 等）
# 不是评最终 SQL，而是评"检索到的文档质量"
```

**大白话**：两层都评——**SQL 对没对**（EX）+ **检索准不准**（ragas）。

---

## 五、对照 ai_assistant 的改造动作

```python
# ① 加执行准确率（结果集比较，不是文本）
def exec_accuracy(cases):
    correct = 0
    for c in cases:
        pred = run_sql(c.generated_sql)
        gold = run_sql(c.gold_sql)
        if normalize(pred) == normalize(gold): correct += 1
    return correct / len(cases)

# ② 加难度分桶（定位短板）
for c in cases:
    level = classify_hardness(c.gold_sql)   # easy/medium/hard
    buckets[level].append(c)
# 各桶算准确率 → 看出哪类掉点

# ③ 加 A/B：验证 RAG/few-shot 有没有用
for case in cases:
    acc_rag = eval_with(case, use_rag=True)
    acc_norag = eval_with(case, use_rag=False)
# 对比 → 决定要不要 RAG（不是加上就更好）
```

**改造要点**：执行准确率（结果集）+ 难度分桶 + A/B（验证改动）。

---

## 六、小结

| 学到 | 一句话 |
|------|--------|
| 执行准确率 | 结果集一致 = 对（不测写法）|
| 难度分桶 | sqlglot 分析 SQL 复杂度，定位短板 |
| A/B | RAG vs noRAG 对比，证明有没有用 |
| 消融 | few-shot 最稳定收益 |
| ragas | 评检索质量 |

> **核心心法**：评测方法论 = 执行准确率 + 难度分桶 + A/B + 消融。你的 eval_qa.py 最该加 **执行准确率 + 难度分桶 + A/B**——尤其验证 RAG/few-shot 有没有用，不是加上就更好。
