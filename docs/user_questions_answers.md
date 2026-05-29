# 用户提问与完整回答沉淀

> 用途：保存学习过程中你主动问过、值得反复看的问题和完整回答。

> 维护规则：后续你每次主动提问的问题，都先自动追加到这里，后续再按你的要求筛选、合并或删除。

---

## 目录

| 编号 | 问题 |
|------|------|
| Q001 | 召回优化是什么？ |
| Q002 | RAG 一般有两条链路，那么它们分别如何存储数据？ |
| Q003 | RAG 完整详细生产级别的流程链路是什么，每一步的作用是什么？ |
| Q004 | 删除标题后面重复的锚点内容。 |
| Q005 | RAG 存储过程中具体的存储介质是什么，如何优化？ |
| Q006 | SQLite、PostgreSQL、pgvector、Milvus、Redis、OpenSearch / ELK 有什么区别，应用场景是什么？ |
| Q007 | 这些 RAG 存储库和 Hive、Kafka、ClickHouse 等大数据仓库链路怎么结合？ |
| Q008 | 开始第19天的学习。 |
| Q009 | Prompt 是什么？ |
| Q010 | Confidence 是什么？ |
| Q011 | Expected source 是什么？ |
| Q012 | Prompt。 |
| Q013 | Ingestion 是什么？ |
| Q014 | FastAPI 在 AI 服务化里承担什么角色？ |
| Q015 | 模拟一条数据在代码里的真实流转，在 RAG 中。 |
| Q016 | 模拟一条数据在代码里的真实流转，在 NL2SQL 中。 |

---

> ## Q001：召回优化是什么？

召回优化，简单说就是：

**让 RAG 系统更容易找到真正有用的资料。**

在 RAG 里，用户问一个问题，系统不是马上让大模型回答，
而是先去知识库里“找资料”。
这个“找资料”的过程就叫**召回**。

比如用户问：

```text
SQL 解释助手为什么要检查 dt 分区？
```

如果系统召回的是：

```text
dt 分区可以减少扫描范围，避免全表扫描。
```

这就是好召回。

如果系统召回的是：

```text
FastAPI 怎么写 health 接口？
```

这就是召回错了。

## 召回优化要解决的问题

生产环境里，知识库资料很多，用户问法也很随意。
召回优化就是为了减少这些问题：

- 找不到正确资料
- 找到的资料不够完整
- 找到很多无关资料
- 正确资料排得太靠后
- 表名、字段名、指标名这种精确词没匹配上
- 用户换一种说法，系统就找不到了

## 常见优化方法

- 调整 chunk：文档切得太碎或太大都会影响召回
- 调整 top-k：召回数量太少会漏，太多会带入噪声
- 混合检索：向量检索 + 关键词检索一起用
- query rewrite：把用户问题改写成更适合检索的表达
- metadata 过滤：按业务域、权限、文档类型、时间过滤
- rerank：先召回一批，再重新排序，把最相关的放前面

生产里看召回优化，不是看模型回答漂不漂亮，而是先看：

**正确资料有没有被找出来，并且有没有排在前面。**

---

> ## Q002：RAG 一般有两条链路，那么它们分别如何存储数据？

是的，生产级 RAG 一般有两条链路：

1. 离线入库链路
2. 在线问答链路

它们都会“存数据”，但存的东西不一样。

## 1. 离线入库链路：存知识库数据

离线链路负责把原始资料加工成系统能检索的形式。

### 它存什么？

| 数据 | 存在哪里 | 作用 |
|------|----------|------|
| 原始文档 | 对象存储 / 文件系统 | 保存 PDF、Word、Markdown、网页原文 |
| 解析后的正文 | 数据库 / 文档库 | 保存清洗后的文本内容 |
| chunk 片段 | 数据库 / 文档库 | 保存切分后的知识片段 |
| embedding 向量 | 向量数据库 | 用来做语义检索 |
| metadata 元数据 | 数据库 / 向量库 metadata | 保存来源、标题、权限、时间、版本 |
| 文档版本 | 数据库 | 判断资料是否过期、是否需要更新 |
| 权限标签 | 数据库 / metadata | 控制用户能不能看某段内容 |

### 大白话

离线链路就像“图书馆整理书”。

它要做的事是：

```text
原始文档
-> 解析正文
-> 清洗
-> 切成 chunk
-> 生成 embedding
-> 存入向量库和数据库
```

最终存储结果大概是：

```json
{
  "chunk_id": "chunk_001",
  "doc_id": "doc_1001",
  "content": "dt 分区字段用于控制查询扫描范围...",
  "embedding": [0.12, 0.08, -0.22],
  "metadata": {
    "source": "sql_risk_rules.md",
    "title": "SQL 分区风险规则",
    "business_domain": "data_warehouse",
    "permission": "internal",
    "version": "2026-05-11",
    "status": "active"
  }
}
```

## 2. 在线问答链路：存用户请求和运行过程数据

在线链路负责用户提问、检索、生成答案。

### 它存什么？

| 数据 | 存在哪里 | 作用 |
|------|----------|------|
| 用户问题 | 日志 / 数据库 | 排查问题、分析高频问题 |
| 检索 query | 日志 / trace 系统 | 看用户问题如何进入检索 |
| 召回结果 | 日志 / 评测表 | 分析召回是否准确 |
| rerank 结果 | 日志 / 评测表 | 看排序是否合理 |
| 最终上下文 | 日志，可脱敏 | 排查模型为什么这样回答 |
| LLM 回答 | 数据库 / 日志 | 审计、复盘、优化 |
| 引用来源 | 数据库 / 日志 | 判断答案依据 |
| 用户反馈 | 数据库 | 用于后续优化 |
| 耗时和成本 | 监控系统 | 优化性能和费用 |

### 大白话

在线链路就像“用户来问图书管理员”。

它要记录：

```text
用户问了什么
系统找到了哪些资料
最后用了哪些资料
模型回答了什么
用户满不满意
这次花了多久、多少钱
```

一次在线请求可能会记录成这样：

```json
{
  "request_id": "req_20260511_001",
  "user_id": "u_1001",
  "question": "为什么 SQL 要检查 dt 分区？",
  "retrieved_chunks": ["chunk_001", "chunk_008", "chunk_021"],
  "used_chunks": ["chunk_001", "chunk_008"],
  "answer": "检查 dt 分区是为了避免全表扫描...",
  "citations": [
    {
      "doc_id": "doc_1001",
      "chunk_id": "chunk_001",
      "title": "SQL 分区风险规则"
    }
  ],
  "latency_ms": 1850,
  "token_usage": 1200,
  "feedback": null
}
```

## 核心区别

| 对比 | 离线入库链路 | 在线问答链路 |
|------|--------------|--------------|
| 主要目标 | 把知识整理好 | 用知识回答问题 |
| 处理对象 | 文档、chunk、向量、元数据 | 用户问题、召回结果、答案、日志 |
| 存储重点 | 知识库 | 请求过程和结果 |
| 更新频率 | 文档变化时更新 | 每次用户提问都会产生 |
| 常用存储 | 对象存储、数据库、向量库 | 数据库、日志系统、监控系统 |
| 关注点 | 资料质量、版本、权限 | 召回质量、回答质量、延迟、成本 |

一句话总结：

**离线链路存“知识本身”，在线链路存“使用知识回答问题的过程”。**

---

> ## Q003：RAG 完整详细生产级别的流程链路是什么，每一步的作用是什么？

生产级 RAG 的完整链路，可以分成两大部分：

1. **离线入库链路**：把资料整理成“可检索的知识库”
2. **在线问答链路**：用户提问时，从知识库找资料，再让模型回答

一句话：

**离线链路负责把知识准备好，在线链路负责用知识回答问题。**

---

# 一、离线入库链路

离线入库链路不是用户提问时才跑，而是提前把文档处理好。

完整流程：

```text
原始资料
-> 文档接入
-> 文档解析
-> 清洗去重
-> 脱敏与权限标记
-> chunk 切分
-> metadata 构建
-> embedding 向量化
-> 存入向量库 / 文档库
-> 建索引与版本管理
```

## 1. 原始资料

生产里的知识来源很多，比如：

- 公司制度文档
- 产品文档
- FAQ
- 数据字典
- 表结构说明
- 指标口径文档
- 历史 SQL
- 接口文档
- 工单记录
- 项目 README

作用：

**确定 RAG 到底回答什么范围的问题。**

如果资料本身质量差，后面模型再强也容易答错。

## 2. 文档接入

把不同来源的资料接进系统。

比如：

```text
飞书文档
Confluence
Git 仓库
数据库表
对象存储
本地 Markdown
PDF / Word
```

作用：

**把分散在各处的知识统一接入。**

生产里通常要记录：

- 文档来源
- 文档 ID
- 所属业务线
- 创建人
- 更新时间
- 是否启用
- 权限范围

## 3. 文档解析

不同格式的资料不能直接检索，需要先解析成文本。

| 文件类型 | 解析内容 |
|----------|----------|
| PDF | 正文、标题、页码 |
| Word | 段落、表格 |
| Markdown | 标题层级、代码块 |
| HTML | 正文、链接、结构 |
| 数据表 | 表名、字段、注释 |

作用：

**把复杂文件变成系统能处理的文本结构。**

生产里难点是 PDF 乱码、表格丢结构、图片文字识别、标题层级丢失，
以及代码块和正文混在一起。

## 4. 清洗去重

解析出来的文本通常很脏，需要处理：

- 删除页眉页脚
- 删除无意义空行
- 删除重复内容
- 合并断行
- 过滤广告、目录、导航栏
- 去掉废弃文档
- 处理冲突版本

作用：

**提高知识库质量，减少垃圾内容进入检索。**

大白话：

**脏资料进知识库，模型就会基于脏资料认真胡说。**

## 5. 脱敏与权限标记

企业资料里经常有敏感信息，比如用户手机号、身份证、客户合同、
内部财务数据、人事信息和未发布产品信息。

所以入库前要做：

- 敏感字段识别
- 脱敏
- 权限标签
- 部门标签
- 项目标签
- 访问级别标记

作用：

**防止 RAG 把不该给用户看的资料检索出来。**

比如一个 chunk 可能带这样的 metadata：

```json
{
  "permission": "project_internal",
  "department": "data_platform",
  "security_level": "confidential"
}
```

## 6. chunk 切分

文档通常很长，不能整篇直接塞进模型，所以要切成小片段，也就是 chunk。

| 文档类型 | 切分方式 |
|----------|----------|
| 制度文档 | 按标题和段落切 |
| FAQ | 一问一答切 |
| 指标文档 | 一个指标一个 chunk |
| 表结构 | 一张表或一组字段一个 chunk |
| 接口文档 | 一个接口一个 chunk |
| SQL 文档 | 一个 SQL 案例一个 chunk |

作用：

**让系统能更精确地找到和问题相关的内容。**

切太大，召回不精准，会带入很多无关内容。
切太小，上下文不完整，模型看不懂前因后果。

## 7. metadata 构建

metadata 是 chunk 的附加信息。

```json
{
  "chunk_id": "chunk_001",
  "doc_id": "doc_1001",
  "title": "SQL 分区风险规则",
  "source": "sql_risk_rules.md",
  "business_domain": "data_warehouse",
  "doc_type": "risk_rule",
  "updated_at": "2026-05-11",
  "permission": "internal"
}
```

作用：

**帮助检索、过滤、排序、引用和权限控制。**

生产里 metadata 非常重要。比如用户问 SQL 风险问题，系统可以优先检索：

```text
business_domain = data_warehouse
doc_type = risk_rule
permission <= 当前用户权限
```

## 8. embedding 向量化

embedding 是把文本变成向量。

比如：

```text
"dt 分区用于减少扫描范围"
```

会变成类似：

```text
[0.12, -0.08, 0.31, ...]
```

作用：

**让系统可以计算用户问题和文档片段的语义相似度。**

大白话：

**embedding 就是把文字变成机器能比较“像不像”的数字。**

## 9. 存入向量库 / 文档库

生产里通常不会只存一种数据。

| 数据 | 存储位置 |
|------|----------|
| 原始文档 | 对象存储 / 文件系统 |
| chunk 正文 | 数据库 / 文档库 |
| embedding 向量 | 向量数据库 |
| metadata | 数据库 / 向量库 metadata |
| 版本信息 | 数据库 |
| 权限信息 | 权限系统 / metadata |

作用：

**让系统既能检索向量，也能拿回原文、来源、权限和版本。**

## 10. 索引与版本管理

文档会更新，所以知识库也要更新。

生产里要处理：

- 新增文档
- 修改文档
- 删除文档
- 废弃文档
- 文档版本回滚
- 增量 embedding
- 索引重建

作用：

**保证用户查到的是最新、有效、可信的知识。**

---

# 二、在线问答链路

在线链路是用户真正提问时发生的流程。

完整流程：

```text
用户提问
-> 用户鉴权
-> 问题预处理
-> query rewrite
-> 检索召回
-> metadata / 权限过滤
-> rerank 重排
-> 上下文构造
-> prompt 构造
-> LLM 生成
-> 后处理与校验
-> 返回答案和引用
-> 日志、监控、反馈
```

## 1. 用户提问

用户输入自然语言问题，比如：

```text
为什么 SQL 解释助手要检查 dt 分区？
```

作用：

**触发 RAG 在线链路。**

生产里会同时记录 request_id、user_id、用户部门、用户角色、问题内容和请求时间。

## 2. 用户鉴权

先判断用户是谁，有没有权限问这个范围的问题。

作用：

**防止用户访问无权限知识。**

| 用户 | 可访问内容 |
|------|------------|
| 普通员工 | 公开制度、通用 FAQ |
| 数据开发 | 数据字典、SQL 规范 |
| 财务人员 | 财务口径文档 |
| 管理层 | 汇总分析和敏感报表 |

RAG 不能只做“回答准确”，还要做“回答合规”。

## 3. 问题预处理

对用户问题做基础处理。

- 去掉无意义空格
- 识别语言
- 识别问题类型
- 识别业务域
- 识别是否是闲聊
- 识别是否越权
- 识别是否需要拒答

作用：

**判断这个问题应该走哪条处理路径。**

比如“帮我写 SQL”可能走 NL2SQL。
“解释这段 SQL 有什么风险”可能走 SQL 解释助手。
“公司报销规则是什么”可能走普通 RAG。

## 4. query rewrite

用户的问题经常不适合直接检索，所以需要改写成更适合检索的 query。

用户原问题：

```text
这个 SQL 为啥慢？
```

改写后：

```text
SQL 查询慢的原因，select *，缺少 where，缺少 dt 分区，group by，order by
```

作用：

**提升召回质量。**

query rewrite 常见做法包括补充同义词、补充专业术语、拆成多个子问题、
提取关键词，以及改写成更标准的检索表达。

## 5. 检索召回

根据 query 去知识库找候选资料。

| 检索方式 | 适合场景 |
|----------|----------|
| 向量检索 | 语义相近的问题 |
| 关键词检索 | 表名、字段名、错误码、编号 |
| 混合检索 | 生产环境常用 |
| metadata 过滤 | 按业务域、权限、时间过滤 |

作用：

**先把可能相关的资料找出来。**

比如先召回 top 20：

```text
chunk_001
chunk_008
chunk_021
...
```

## 6. metadata / 权限过滤

召回出来的资料不一定都能用。

要过滤：

- 用户无权限的 chunk
- 已废弃的文档
- 业务域不匹配的内容
- 时间版本过旧的内容
- 安全等级不允许的内容

作用：

**保证进入模型上下文的资料是可用、合规、有效的。**

这一步非常关键。因为模型一旦看到无权限内容，就可能把它写进答案里。

## 7. rerank 重排

第一阶段召回通常追求“别漏掉”，但召回结果里会有噪声。

rerank 会重新判断：

```text
用户问题和每个 chunk 到底有多相关？
```

作用：

**把最适合回答问题的资料排到前面。**

比如向量检索召回 top 20，rerank 后选 top 5 放进上下文。

## 8. 上下文构造

把最终选中的 chunk 拼成给模型看的上下文。

需要控制：

- chunk 数量
- 总 token 长度
- 去重
- 顺序
- 来源标记
- 引用编号
- 是否保留标题层级

作用：

**让模型看到足够但不冗余的资料。**

示例：

```text
[资料1]
来源：SQL 分区风险规则
内容：dt 分区字段用于减少查询扫描范围...

[资料2]
来源：SQL 发布规范
内容：生产 SQL 必须包含分区过滤条件...
```

## 9. prompt 构造

把系统规则、用户问题、上下文、输出格式组合成 prompt。

通常包括：

```text
system prompt
+ 用户问题
+ 检索上下文
+ 回答约束
+ 输出格式
```

作用：

**告诉模型应该怎么基于资料回答。**

生产 RAG 的 prompt 一般会要求：

- 只能基于上下文回答
- 不要编造资料中没有的信息
- 资料不足时要说明无法判断
- 必须返回引用
- 输出格式要稳定

## 10. LLM 生成

模型基于上下文生成答案。

作用：

**把检索到的资料组织成用户能看懂的回答。**

注意：LLM 不是知识来源。
在 RAG 里，LLM 更像是资料阅读器、总结器和表达器。
真正的依据来自知识库。

## 11. 后处理与校验

模型输出后，还要检查。

常见检查：

- JSON 是否合法
- 字段是否完整
- 引用是否存在
- 是否引用了上下文
- 是否出现敏感信息
- 是否包含编造表名或字段
- 是否需要拒答
- 是否符合业务规则

作用：

**防止错误答案直接返回给用户。**

比如 SQL 风险场景里：

```text
risk_level = high
```

那 `can_publish` 就不能是 `true`。

## 12. 返回答案和引用

最终返回给用户的不只是答案，还应该有来源。

```json
{
  "answer": "检查 dt 分区是为了避免全表扫描，降低查询成本。",
  "citations": [
    {
      "doc": "SQL 分区风险规则",
      "chunk_id": "chunk_001"
    }
  ]
}
```

作用：

**让用户能核对依据，提高可信度。**

## 13. 日志、监控、反馈

每次请求都要记录运行过程。

记录内容包括：

- 用户问题
- 改写后的 query
- 召回 chunk
- rerank 结果
- 最终上下文
- 模型回答
- 引用来源
- token 消耗
- 响应耗时
- 错误信息
- 用户反馈

作用：

**用于排查问题、优化召回、控制成本和评估效果。**

生产里没有监控，RAG 就没法持续变好。

---

# 三、完整生产级链路总图

```text
                    离线入库链路
-----------------------------------------------------
原始资料
  ↓
文档接入
  ↓
文档解析
  ↓
清洗去重
  ↓
脱敏与权限标记
  ↓
chunk 切分
  ↓
metadata 构建
  ↓
embedding 向量化
  ↓
向量库 / 文档库 / 元数据库
  ↓
索引与版本管理


                    在线问答链路
-----------------------------------------------------
用户提问
  ↓
用户鉴权
  ↓
问题预处理
  ↓
query rewrite
  ↓
检索召回
  ↓
metadata / 权限过滤
  ↓
rerank 重排
  ↓
上下文构造
  ↓
prompt 构造
  ↓
LLM 生成
  ↓
后处理与校验
  ↓
返回答案和引用
  ↓
日志、监控、反馈
```

---

# 四、每一步最核心的作用

| 步骤 | 核心作用 |
|------|----------|
| 文档接入 | 把分散资料接入系统 |
| 文档解析 | 把 PDF、Word、网页等变成文本 |
| 清洗去重 | 去掉垃圾、重复、过期内容 |
| 脱敏权限 | 防止敏感信息泄露 |
| chunk 切分 | 让检索更精准 |
| metadata | 支持过滤、权限、引用、版本 |
| embedding | 让文本可以做语义相似度检索 |
| 向量库 | 存储向量并支持快速检索 |
| 用户鉴权 | 判断用户能看什么 |
| query rewrite | 让问题更适合检索 |
| 检索召回 | 找到候选资料 |
| 权限过滤 | 去掉用户不能看的资料 |
| rerank | 把最相关资料排前面 |
| 上下文构造 | 控制给模型看的资料 |
| prompt 构造 | 约束模型按规则回答 |
| LLM 生成 | 生成自然语言答案 |
| 后处理校验 | 防止错误、越权、格式异常 |
| 引用返回 | 让答案可追溯 |
| 监控反馈 | 支持持续优化 |

最重要的一句话：

**生产级 RAG 不是“把文档丢进向量库再问模型”，而是一个包含资料治理、
权限安全、检索优化、生成控制、引用溯源和监控评测的完整工程链路。**

---

> ## Q004：删除标题后面重复的锚点内容。

已处理。

`docs/user_questions_answers.md` 目录里原来使用的是 Markdown 跳转链接。
这种写法会在源码里显示一段重复的锚点内容。
现在已经改成只保留问题标题文本。

后续这个文件的目录默认也按这种格式维护，不再在问题标题后面追加锚点链接。

---

> ## Q005：RAG 存储过程中具体的存储介质是什么，如何优化？

RAG 生产环境里不会只用一个数据库。

更常见的设计是：

```text
原始文件              -> 对象存储 / 文件系统
解析后的文档和 chunk   -> 关系型数据库 / 文档数据库
embedding 向量        -> 向量数据库
权限、版本、任务状态    -> 关系型数据库
请求日志、trace        -> 日志系统 / 分析型数据库
热点结果              -> Redis / 内存缓存
```

一句话：

**原文用便宜稳定的存储，结构化信息用数据库，向量用向量库，
高频访问数据用缓存，运行过程用日志和监控系统。**

## 1. 原始文档存哪里？

原始文档包括 PDF、Word、Markdown、HTML、图片、压缩包和导出的业务文档。

生产里一般存：

| 存储介质 | 常见选择 | 适合存什么 |
|----------|----------|------------|
| 对象存储 | S3、OSS、COS、MinIO | PDF、Word、图片、原始文件 |
| 文件系统 | NFS、本地磁盘 | 小团队、本地开发、内部 Demo |
| Git 仓库 | GitLab、GitHub | Markdown、配置文档、代码文档 |

生产更推荐对象存储，因为它便宜、稳定、容量大，也方便做版本管理和备份。
本地磁盘适合开发环境，不适合作为企业知识库的唯一存储。

## 2. 解析后的正文和 chunk 存哪里？

解析后的正文、chunk 内容、标题、来源、页码、段落位置、文档状态，
一般会存到普通数据库里。

常见选择：

| 数据库 | 适合场景 |
|--------|----------|
| PostgreSQL | 通用生产首选，适合文档表、chunk 表、权限表、任务表 |
| MySQL | 企业已有 MySQL 体系时使用，适合结构化元数据 |
| MongoDB | 文档结构变化大、JSON 内容多时使用 |
| SQLite | 本地 Demo、小工具、单机实验 |

如果是生产系统，我会优先考虑 PostgreSQL。
因为它稳定、支持事务、JSON 字段、索引能力好，也方便和业务系统集成。

## 3. 向量存哪里？

embedding 向量一般存向量数据库，或者存支持向量索引的数据库。

常见选择：

| 向量存储 | 适合场景 |
|----------|----------|
| Milvus | 数据量大、独立向量检索服务、生产级 RAG |
| pgvector | 中小规模、已有 PostgreSQL、想减少系统复杂度 |
| Elasticsearch / OpenSearch | 需要关键词检索 + 向量检索 + 日志检索 |
| Qdrant | 部署轻量、API 简洁、中小团队常用 |
| FAISS | 本地实验、离线索引、需要自己管理持久化 |
| Chroma | 本地开发、原型验证、学习项目 |

简单选型可以这样记：

```text
本地学习 / Demo：Chroma、FAISS、SQLite
中小生产系统：PostgreSQL + pgvector
大规模生产系统：Milvus / Elasticsearch / OpenSearch / Qdrant
```

## 4. metadata 存哪里？

metadata 包括：

- doc_id
- chunk_id
- 文档标题
- 来源系统
- 业务域
- 文档类型
- 更新时间
- 版本号
- 权限标签
- 是否启用

metadata 可以存在两个地方：

| 存储位置 | 作用 |
|----------|------|
| 关系型数据库 | 作为主数据，方便管理、更新、审计 |
| 向量库 metadata | 检索时快速过滤，比如按权限、业务域、时间过滤 |

生产里通常两边都存。
数据库里存完整、权威的 metadata；向量库里存检索时必须用的轻量字段。

## 5. 日志和运行过程存哪里？

在线问答链路会产生很多运行数据：

- 用户问题
- 改写后的 query
- 召回 chunk
- rerank 分数
- 最终上下文
- LLM 回答
- 引用来源
- token 消耗
- 响应耗时
- 错误信息
- 用户反馈

常见存储：

| 数据 | 常见选择 |
|------|----------|
| 应用日志 | 文件日志、ELK、OpenSearch |
| trace 链路 | OpenTelemetry、Jaeger |
| 监控指标 | Prometheus、Grafana |
| 用户反馈 | PostgreSQL / MySQL |
| 离线分析 | ClickHouse、BigQuery、Hive |

这些数据不是用来做实时检索的，主要用于排查问题、评估效果、优化召回和控制成本。

## 6. 存本地磁盘还是内存？

生产里不能简单理解成“存磁盘”或“存内存”。

一般是：

| 介质 | 用途 |
|------|------|
| 磁盘 / 对象存储 | 长期保存原始文档、chunk、向量索引、日志 |
| 内存 | 缓存热点数据、加速查询、保存临时上下文 |
| Redis | 缓存高频问题、用户会话、短期结果、限流计数 |
| 本地磁盘 | 开发调试、临时文件、单机小 Demo |

核心原则：

**长期数据必须落盘或进可靠存储，内存只做加速和临时缓存。**

如果只存在内存里，服务重启就没了，不适合保存知识库。

## 7. 存储如何优化？

RAG 存储优化主要看四个目标：检索快、成本低、更新稳、权限安全。

### 7.1 原始文档优化

- 原始文件存对象存储，不直接塞数据库。
- 数据库只存文件地址、hash、版本、状态。
- 用 hash 判断文档是否变化，避免重复解析。
- 废弃文档不立刻物理删除，先标记 disabled，方便回滚。

### 7.2 chunk 存储优化

- chunk 表按 `doc_id`、`business_domain`、`status` 建索引。
- chunk 内容和 metadata 分开管理，避免每次查询都加载大文本。
- 保留 chunk 的来源位置，方便引用和排查。
- 控制 chunk 大小，避免太碎导致数量爆炸。

### 7.3 向量库优化

- 选择合适索引，比如 HNSW、IVF、DiskANN。
- 按业务域、租户或权限做 collection / partition。
- 只把检索必需的 metadata 放进向量库。
- 控制 embedding 维度和 chunk 数量，降低存储成本。
- 高频知识可以预热索引或缓存结果。

### 7.4 在线查询优化

- 高频问题用 Redis 缓存答案或召回结果。
- 先用 metadata 过滤业务域和权限，再做向量检索。
- 控制 top-k，避免召回过多导致 rerank 和 LLM 成本变高。
- 对长上下文去重和压缩，减少 token 消耗。
- 日志异步写入，避免拖慢用户请求。

## 8. 一个比较常见的生产组合

中小型生产 RAG 可以这样搭：

```text
对象存储：MinIO / S3 / OSS
业务数据库：PostgreSQL
向量检索：pgvector 或 Qdrant
缓存：Redis
日志检索：OpenSearch / ELK
监控：Prometheus + Grafana
```

更大规模可以这样搭：

```text
对象存储：S3 / OSS
元数据数据库：PostgreSQL
向量数据库：Milvus / OpenSearch / Elasticsearch
缓存：Redis
日志分析：ClickHouse / OpenSearch
链路追踪：OpenTelemetry + Jaeger
监控告警：Prometheus + Grafana
```

本地学习可以简化成：

```text
原始文档：本地 docs / notes 目录
chunk 和 metadata：SQLite
向量索引：FAISS / Chroma
缓存：暂时不用，或者用 Python dict
日志：本地 log 文件
```

## 9. 最重要的判断

如果面试里被问“RAG 存储怎么设计”，可以这样回答：

**我不会把所有东西都塞进向量数据库。向量库主要负责相似度检索，
原始文档适合放对象存储，chunk 正文和 metadata 适合放 PostgreSQL，
热点结果可以放 Redis，日志和 trace 进入可观测系统。这样既能检索，
也能管理版本、权限、审计和成本。**

---

> ## Q006：SQLite、PostgreSQL、pgvector、Milvus、Redis、OpenSearch / ELK 有什么区别，应用场景是什么？

这几个工具不是互相替代关系，而是负责不同层的数据。

一句话区分：

```text
SQLite        -> 本地 Demo / 单机小项目
PostgreSQL    -> 生产里的结构化主数据库
pgvector      -> PostgreSQL 里的向量检索插件
Milvus        -> 专业向量数据库，适合大规模向量检索
Redis         -> 内存缓存，适合热点数据和短期状态
OpenSearch/ELK -> 日志检索、全文检索、可观测分析
```

## 1. SQLite

SQLite 是一个轻量级本地数据库。

它不是一个独立服务，而是一个本地文件，比如：

```text
rag_index.sqlite
```

适合：

- 本地学习
- Demo
- 小工具
- 单机脚本
- 快速验证数据结构

不适合：

- 多人高并发写入
- 企业级权限管理
- 大规模生产服务
- 分布式部署

在当前学习项目里，SQLite 用来模拟：

```text
documents 表
chunks 表
embeddings 表
ingestion_runs 表
```

大白话：

**SQLite 适合先把 RAG 数据结构跑通，但不是企业 RAG 的最终生产存储。**

## 2. PostgreSQL

PostgreSQL 是生产环境常用的关系型数据库。

它适合存结构化、需要事务、需要长期管理的数据。

在 RAG 里通常存：

- documents 文档表
- chunks 正文表
- metadata
- 权限字段
- 版本状态
- 入库任务记录
- 用户反馈

比如：

```text
documents(doc_id, title, source_path, version, status)
chunks(chunk_id, doc_id, content, position, metadata)
```

适合：

- 中小型生产系统
- 文档和 chunk 主数据管理
- 权限、版本、状态管理
- 和业务系统集成

不适合：

- 单独承担超大规模向量检索
- 单独做复杂日志分析
- 当作内存缓存使用

大白话：

**PostgreSQL 是 RAG 的“账本”和主数据中心，负责把文档、chunk、权限、
版本这些信息管清楚。**

## 3. pgvector

pgvector 是 PostgreSQL 的向量扩展。

它让 PostgreSQL 也能存 embedding，并做向量相似度检索。

适合：

- 已经在用 PostgreSQL
- 数据量中小规模
- 想减少系统复杂度
- 不想额外维护 Milvus / Qdrant

典型组合：

```text
PostgreSQL documents/chunks
+ pgvector embeddings
```

优点：

- 架构简单
- 数据和向量在一个库里
- 权限、metadata、向量查询更容易 join
- 很适合第一版生产 RAG

缺点：

- 超大规模向量检索能力不如专业向量库
- 高并发、大量向量、复杂索引时需要更仔细调优

大白话：

**pgvector 适合“先把生产 RAG 做起来”，尤其适合中小规模项目。**

## 4. Milvus

Milvus 是专业向量数据库。

它主要解决的问题是：

```text
海量 embedding 怎么存、怎么快速相似度检索、怎么扩展
```

适合：

- 百万级、千万级甚至更大规模向量
- 检索性能要求高
- 需要独立向量检索服务
- 多业务共用一个向量平台

在 RAG 里通常存：

- chunk_id
- embedding
- 轻量 metadata

注意：Milvus 里通常不建议存完整原文。

更常见的是：

```text
Milvus 存 embedding + chunk_id
PostgreSQL 存 chunk 正文 + metadata
```

检索流程：

```text
问题 embedding
-> Milvus 找到相似 chunk_id
-> 用 chunk_id 去 PostgreSQL 查正文和 metadata
-> 拼上下文给 LLM
```

大白话：

**Milvus 是“专业找相似内容的引擎”，但它不是文档管理系统。**

## 5. Redis

Redis 是内存数据库，速度很快。

它主要用来缓存，不适合做长期唯一存储。

在 RAG 里适合缓存：

- 高频问题答案
- 高频问题的召回结果
- 用户短期会话
- token / 权限临时状态
- 限流计数
- 任务进度

比如很多人都问：

```text
SQL 解释助手有哪些风险检查？
```

可以把这个问题的检索结果或最终答案缓存到 Redis。

下次再问时：

```text
先查 Redis
命中则直接返回
未命中再走向量检索 + LLM
```

优点：

- 快
- 适合热点数据
- 能降低数据库和 LLM 压力
- 能降低延迟和成本

缺点：

- 内存成本高
- 数据可能过期或丢失
- 不适合当知识库主存储

大白话：

**Redis 是加速器，不是知识库本体。**

## 6. OpenSearch / ELK

ELK 通常指：

```text
Elasticsearch
Logstash
Kibana
```

OpenSearch 是 Elasticsearch 生态的开源替代方案之一。

它们常用于：

- 日志检索
- 全文搜索
- 监控分析
- 错误排查
- 请求 trace 分析

在 RAG 里可以存：

- 用户问题日志
- 检索 query
- 召回 chunk
- rerank 结果
- LLM 回答
- 错误日志
- 延迟和成本信息

也可以用于关键词检索，比如：

```text
表名、字段名、错误码、文档标题、SQL 片段
```

适合：

- 日志量大
- 需要按关键词快速查问题
- 需要 dashboard 看请求量、错误率、耗时
- 需要做关键词检索或混合检索

不适合：

- 当事务型主数据库
- 管复杂业务关系
- 单独替代 PostgreSQL

大白话：

**OpenSearch / ELK 更像“日志和搜索中心”，方便排查 RAG 为什么答错、
慢在哪里、用户都在问什么。**

## 7. 它们在 RAG 里怎么配合？

一个比较合理的中小型生产组合：

```text
PostgreSQL:
  存 documents、chunks、metadata、权限、版本

pgvector:
  存 embedding，做向量相似度检索

Redis:
  缓存高频问题、召回结果、答案、会话状态

OpenSearch / ELK:
  存日志、trace、错误信息，做搜索和分析
```

更大规模时：

```text
PostgreSQL:
  存文档、chunk、metadata、权限、版本

Milvus:
  存 embedding，做大规模向量检索

Redis:
  做缓存、限流、会话状态

OpenSearch / ELK:
  做日志检索、全文检索、监控分析
```

## 8. 最简单的选型建议

| 阶段 | 推荐组合 |
|------|----------|
| 本地学习 | SQLite |
| 本地 RAG Demo | SQLite + 本地 embedding |
| 第一版生产 | PostgreSQL + pgvector + Redis + 日志 |
| 中大型生产 | PostgreSQL + Milvus / Qdrant + Redis + OpenSearch |
| 日志和排查加强 | OpenSearch / ELK |

## 9. 面试表达

可以这样说：

**SQLite 适合本地 Demo，PostgreSQL 适合管理文档、chunk、metadata、
权限和版本；pgvector 是 PostgreSQL 的向量扩展，适合中小规模 RAG；
Milvus 是专业向量数据库，适合大规模 embedding 检索；Redis 主要做热点缓存，
降低延迟和成本；OpenSearch / ELK 主要做日志、全文检索和问题排查。
生产里不会用一个库解决所有问题，而是按数据类型和访问模式分层存储。**

---

> ## Q007：这些 RAG 存储库和 Hive、Kafka、ClickHouse 等大数据仓库链路怎么结合？

它们不是两套完全割裂的系统。

更准确地说：

**Hive、Kafka、ClickHouse 是企业数据链路；PostgreSQL、Milvus、
Redis、OpenSearch 是 AI 应用服务链路。RAG / NL2SQL 会站在两者中间，
把“数据资产”和“智能问答应用”接起来。**

## 1. 先看你原来的大数据仓库链路

典型数仓链路大概是：

```text
业务系统 / 埋点 / 日志
-> Kafka
-> Flink / Spark
-> Hive / Iceberg / Hudi
-> ClickHouse / Doris / StarRocks
-> BI 报表 / 数据服务 / 分析查询
```

各层作用：

| 组件 | 主要作用 |
|------|----------|
| Kafka | 接实时数据流，比如埋点、订单、日志 |
| Flink / Spark | 清洗、聚合、宽表加工、实时或离线计算 |
| Hive | 离线数仓，存 ODS、DWD、DWS、ADS 等大规模数据 |
| ClickHouse | OLAP 查询，适合高并发聚合分析和报表 |
| BI / 数据服务 | 给业务看指标、查报表、做分析 |

这些系统主要管的是：

```text
结构化业务数据、指标数据、明细数据、宽表数据、日志明细
```

## 2. RAG / AI 应用链路管的是什么？

RAG 链路通常管的是：

```text
文档、知识、表结构说明、字段解释、指标口径、SQL 规范、历史问答、引用来源
```

也就是：

| 数据类型 | 示例 |
|----------|------|
| 数据字典 | 表名、字段名、字段含义 |
| 指标口径 | GMV、活跃用户、留存率怎么算 |
| SQL 规范 | 必须带 dt 分区，禁止 select * |
| 业务文档 | 产品说明、运营规则、财务口径 |
| 历史 SQL | 常用查询、报表 SQL、口径样例 |
| 问答日志 | 用户问了什么，系统怎么答 |

这些不一定适合直接放 Hive。

Hive 更适合大规模明细和汇总数据；RAG 更关心“怎么解释这些数据”和
“用户问问题时该参考哪些知识”。

## 3. 两条链路怎么接起来？

可以分成三类连接。

### 3.1 元数据接入：Hive / 数仓 -> RAG 知识库

数仓里已经有大量元数据：

- 表名
- 字段名
- 字段类型
- 字段注释
- 分区字段
- 表负责人
- 数据主题域
- 指标口径
- 血缘关系
- 常用 SQL

这些可以进入 RAG 知识库。

链路是：

```text
Hive Metastore / 数据地图 / 指标平台 / SQL 仓库
-> 抽取表结构、字段解释、指标口径
-> 清洗和标准化
-> 切成 chunk
-> 存 PostgreSQL documents/chunks
-> embedding 存 pgvector / Milvus
-> RAG / NL2SQL 检索使用
```

这一步解决的是：

```text
模型怎么知道有哪些表、字段、指标，以及它们是什么意思？
```

### 3.2 查询执行：AI 应用 -> ClickHouse / Hive / 数据服务

如果是 NL2SQL 或数据问答，RAG 不只是回答文档问题，还可能要查真实数据。

链路是：

```text
用户问题
-> RAG 检索表结构、指标口径、权限规则
-> LLM 生成 SQL
-> SQL 安全校验
-> 查询 ClickHouse / Hive / 数据服务
-> 拿到结果
-> LLM 解释结果
-> 返回答案、SQL、引用和口径说明
```

一般选择：

| 查询场景 | 更常查哪里 |
|----------|------------|
| 实时报表、交互分析 | ClickHouse / Doris / StarRocks |
| 离线大规模明细回溯 | Hive / Spark SQL |
| 已封装好的指标 | 指标平台 / 数据服务 API |
| 高频固定查询 | 预聚合表 / Redis 缓存 |

这里要注意：

**RAG 知识库不替代 Hive / ClickHouse。RAG 负责找上下文和解释口径，
真正的数据查询仍然走数仓或 OLAP 引擎。**

### 3.3 行为日志回流：AI 应用 -> Kafka / ClickHouse / OpenSearch

AI 应用上线后，也会产生新数据：

- 用户问题
- 检索 query
- 召回 chunk
- rerank 结果
- 生成答案
- 引用来源
- 用户反馈
- 延迟
- token 成本
- 错误日志

这些数据可以分两类存：

```text
排查问题：OpenSearch / ELK
分析统计：Kafka -> ClickHouse / Hive
```

典型链路：

```text
RAG API 请求日志
-> Kafka
-> Flink 清洗
-> ClickHouse 实时分析
-> Hive 离线沉淀
-> BI 看板 / 召回质量分析 / 成本分析
```

OpenSearch / ELK 更适合研发排查：

```text
某个 request_id 为什么答错？
召回了哪些 chunk？
LLM 返回了什么？
耗时卡在哪里？
```

ClickHouse / Hive 更适合分析：

```text
每天多少问题？
哪些问题最多？
无答案率多少？
平均 token 成本多少？
哪些文档被引用最多？
哪些业务域召回效果差？
```

## 4. 放到一起的完整链路

可以这样理解：

```text
                 ┌──────────────────────────┐
                 │ 原始业务数据 / 埋点 / 日志 │
                 └────────────┬─────────────┘
                              │
                              ▼
                            Kafka
                              │
                              ▼
                      Flink / Spark
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
        Hive / Iceberg                  ClickHouse / Doris
   离线明细、宽表、历史数据              交互查询、报表、聚合分析
              │                                │
              │                                │
              ▼                                ▼
      数据字典 / 指标口径 / 表结构 / 历史 SQL / 血缘
                              │
                              ▼
                      RAG 离线入库链路
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
       PostgreSQL documents/chunks       pgvector / Milvus
       正文、metadata、权限、版本          embedding 向量检索
              │                                │
              └───────────────┬────────────────┘
                              ▼
                        RAG / NL2SQL API
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
      Redis 缓存        ClickHouse/Hive 查询     OpenSearch/ELK 日志排查
  高频问题、会话、结果     真实数据结果             request_id、错误、trace
                              │
                              ▼
                       用户答案 / SQL / 引用
```

## 5. 每个系统在结合链路里的位置

| 系统 | 在大数据链路中的角色 | 在 AI / RAG 链路中的角色 |
|------|----------------------|--------------------------|
| Kafka | 接入实时业务数据和日志 | 接入 AI 应用行为日志、反馈、trace |
| Hive | 离线数仓，存大规模历史数据 | 提供表结构、字段、指标、离线查询能力 |
| ClickHouse | 高性能 OLAP 查询 | 执行数据问答 SQL，分析 RAG 日志和效果 |
| PostgreSQL | 一般不是核心数仓 | 存 RAG 文档、chunk、metadata、权限、版本 |
| pgvector | 不属于传统数仓 | 中小规模 RAG 向量检索 |
| Milvus | 不属于传统数仓 | 大规模 embedding 向量检索 |
| Redis | 缓存层 | 缓存高频问答、召回结果、会话、限流 |
| OpenSearch / ELK | 日志检索和搜索 | 排查 RAG 请求、错误、召回、生成过程 |

## 6. 结合你原来的数仓经验，最容易迁移的能力

你原来的数仓经验非常有用，尤其是这些能力：

- 知道 ODS、DWD、DWS、ADS 的数据分层
- 知道指标口径为什么重要
- 知道 Hive 表、分区、字段注释、血缘关系
- 知道 ClickHouse 适合高性能聚合查询
- 知道 Kafka / Flink 如何处理实时数据
- 知道 SQL 风险，比如全表扫描、缺少 dt 分区、join 成本高
- 知道数据权限和数据质量问题

这些在 RAG / NL2SQL 里会变成：

| 数仓能力 | AI 应用里的对应能力 |
|----------|----------------------|
| 表结构理解 | NL2SQL 选表选字段 |
| 指标口径 | 数据问答解释结果 |
| 分区和性能 | SQL 安全校验 |
| 血缘关系 | 找到指标来源和可信表 |
| 数据质量 | 判断模型答案是否可信 |
| 权限治理 | RAG 和 NL2SQL 权限过滤 |
| 日志分析 | 评估 RAG 效果和成本 |

## 7. 一个真实例子

用户问：

```text
昨天各渠道新客转化率是多少？为什么比前天下降？
```

系统可能这样工作：

```text
1. RAG 检索指标口径：
   新客、转化率、渠道、日期口径分别怎么定义。

2. RAG 检索表结构：
   应该用 dws_user_channel_daily 还是 ads_channel_conversion_daily。

3. LLM 生成 SQL：
   查询昨天和前天各渠道新客转化率。

4. SQL 校验：
   只允许 select，必须带 dt 分区，字段必须存在，用户必须有权限。

5. 查询 ClickHouse：
   因为这是交互分析，优先查 OLAP 宽表。

6. 结果解释：
   模型基于查询结果解释哪个渠道下降明显。

7. 返回引用：
   引用指标口径文档、表结构说明和实际 SQL。

8. 日志入 Kafka / OpenSearch：
   后续分析这个问题是否答对、耗时多少、用了多少 token。
```

## 8. 最重要的一句话

**大数据仓库负责“数据从哪里来、怎么算、存在哪里、怎么查”；
RAG / AI 应用负责“用户怎么用自然语言理解和使用这些数据”。
Hive、Kafka、ClickHouse 是数据底座，PostgreSQL、向量库、Redis、
OpenSearch 是 AI 应用运行时的知识、检索、缓存和观测层。**

---

> ## Q008：开始第19天的学习。

已进入 Day 19：RAG 召回质量优化。

本次学习重点是：

- 什么是召回质量
- 为什么召回质量决定 RAG 答案上限
- 如何对比不同 top-k
- 如何用 query rewrite 提升检索命中
- 如何记录 bad case
- 生产环境里如何结合 chunk、混合检索、metadata 和 rerank 优化召回

本次会生成 Day 19 学习笔记、本地实验脚本、实验报告，并同步更新术语表和面试题库。

---

> ## Q009：Prompt 是什么？

Prompt 就是你给大模型的“任务说明书”。

大白话：

**你怎么跟模型说话，模型就按你说的方式去理解任务、参考资料、遵守规则并输出结果。**

比如你直接问：

```text
解释一下这段 SQL。
```

这是一个很简单的 prompt。

但在真实项目里，prompt 通常会写得更完整：

```text
你是一个数据仓库 SQL 解释助手。
请解释下面 SQL 的业务含义、使用到的表和字段、潜在性能风险。
如果缺少表结构或指标口径，请明确说明缺少哪些上下文。
请按 JSON 格式输出。
```

这个 prompt 里包含了几件事：

| 部分 | 作用 |
|------|------|
| 角色 | 告诉模型它现在扮演谁，比如 SQL 解释助手 |
| 任务 | 告诉模型要做什么，比如解释 SQL |
| 上下文 | 给模型参考资料，比如表结构、指标口径、RAG 检索结果 |
| 约束 | 告诉模型不能做什么，比如不要编造字段 |
| 输出格式 | 要求模型按固定格式返回，比如 JSON |

常见的 prompt 又分成：

| 类型 | 解释 |
|------|------|
| System Prompt | 系统级规则，定义模型角色和边界 |
| User Prompt | 用户这一次具体提出的问题 |
| Prompt Template | 可以复用的提示词模板 |

生产环境里，prompt 不是随便写一句话。

它通常要版本管理、测试、回滚和评估。
因为 prompt 一改，模型输出就可能变化，影响 RAG 问答、NL2SQL、SQL 解释和结构化输出。

一句话总结：

**Prompt 是控制模型工作方式的任务说明书；写得越清楚，模型越容易稳定完成任务。**

---

> ## Q010：Confidence 是什么？

Confidence 中文一般叫**置信度**。

大白话：

**系统觉得这个结果有多靠谱。**

比如 RAG 检索时，系统找到了 3 个 chunk：

```json
[
  {"chunk_id": "chunk_001", "score": 0.91},
  {"chunk_id": "chunk_008", "score": 0.72},
  {"chunk_id": "chunk_021", "score": 0.31}
]
```

这里的 `score` 可以理解成一种相关性分数。
分数越高，表示系统认为这个 chunk 和用户问题越相关。

但要注意：

**confidence 不等于一定正确。**

它只是系统根据某种规则、模型分数或统计结果算出来的“把握程度”。
分数高，说明更可能相关；但如果知识库本身是错的，或者问题理解错了，
高 confidence 也可能答错。

在 AI / RAG 项目里，confidence 常见于这些地方：

| 场景 | confidence 表示什么 |
|------|---------------------|
| RAG 检索 | 问题和 chunk 的相关程度 |
| rerank | 候选资料重新排序后的相关程度 |
| 分类任务 | 模型认为某个类别有多可能 |
| 风险判断 | 系统认为风险等级判断有多可靠 |
| 语音 / OCR | 识别结果有多可信 |

生产环境里，confidence 通常用来做决策：

| confidence 情况 | 处理方式 |
|-----------------|----------|
| 很高 | 可以直接回答，但仍然返回引用 |
| 中等 | 回答时加上限制条件，提示需要人工确认 |
| 很低 | 不强答，返回“资料不足”或转人工 |

比如 RAG 问答里可以这样设计：

```text
top1_score >= 0.8：正常回答
0.5 <= top1_score < 0.8：回答但提示依据有限
top1_score < 0.5：拒答，说明知识库没有足够资料
```

一句话总结：

**confidence 是系统对结果可靠程度的估计，不是事实正确性的保证。**

---

> ## Q011：Expected source 是什么？

Expected source 可以理解成**预期来源**。

在 RAG 召回评估里，它表示：

**对于某个测试问题，我们预期系统应该检索到哪份文档、哪个 chunk 或哪类资料。**

比如测试问题是：

```text
RAG 知识入库在生产环境里怎么设计？
```

那 expected source 可能是：

```text
notes/day17_rag_ingestion.md
```

意思是：

**这个问题的正确依据，应该主要来自 Day 17 的知识入库笔记。**

如果系统召回结果里包含这个来源，就说明这次检索命中了关键资料。
如果没有召回这个来源，就说明这是一个 bad case，需要继续排查。

在 Day 19 的召回评估脚本里，测试样例大概长这样：

```json
{
  "question": "RAG 知识入库在生产环境里怎么设计？",
  "expected_sources": ["notes/day17_rag_ingestion.md"]
}
```

然后系统实际召回：

```json
[
  {"source_path": "notes/day17_rag_ingestion.md", "score": 0.82},
  {"source_path": "notes/day16_rag_basics.md", "score": 0.64}
]
```

这就算命中。

如果实际召回是：

```json
[
  {"source_path": "notes/day05_fastapi.md", "score": 0.77},
  {"source_path": "notes/day08_llm_basics.md", "score": 0.62}
]
```

这就没有命中 expected source。

## 它有什么用？

Expected source 主要用于评估 RAG 的召回质量。

| 指标 | 解释 |
|------|------|
| expected source | 这个问题应该命中的资料 |
| retrieved source | 系统实际召回的资料 |
| hit | 实际召回里是否包含 expected source |
| hit rank | expected source 排在第几名 |
| bad case | 没命中 expected source 的失败样例 |

大白话：

**expected source 就是考试标准答案里的“应该查哪本书”。**

用户问一个问题，系统不一定立刻回答对。
我们先看它有没有把正确资料找出来。

如果正确资料都没找出来，后面的 LLM 再会写，也很容易答偏。

## 和 citation 的区别

| 概念 | 含义 |
|------|------|
| expected source | 测试前人工指定的“应该命中的资料” |
| citation | 系统回答时实际返回给用户看的引用来源 |

expected source 是评测用的。
citation 是回答时展示给用户看的。

一句话总结：

**expected source 是 RAG 评测里预期应该召回的资料来源，用来判断检索是否命中关键依据。**

---

> ## Q012：Prompt。

Prompt 就是给大模型看的**任务说明**。

大白话：

**你告诉模型“你是谁、要干什么、参考什么、不能干什么、按什么格式回答”。**

最简单的 prompt：

```text
解释一下 RAG 是什么。
```

更像生产项目里的 prompt：

```text
你是一个 RAG 问答助手。
请只基于给定资料回答用户问题。
如果资料不足，请回答“当前资料不足，无法判断”。
回答必须包含引用来源。
```

Prompt 常见组成：

| 部分 | 例子 |
|------|------|
| 角色 | 你是 SQL 解释助手 |
| 任务 | 解释 SQL 风险 |
| 上下文 | 表结构、指标口径、检索到的 chunk |
| 约束 | 不要编造字段，不要越权回答 |
| 输出格式 | JSON、Markdown、表格 |

在 RAG 里，prompt 通常会把检索到的资料塞进去：

```text
用户问题：active_users 怎么算？

参考资料：
1. active_users = 指定时间内 app_open 的去重 user_id

要求：
只能基于参考资料回答，并返回引用。
```

一句话：

**Prompt 是控制模型怎么工作的说明书。**

---

> ## Q013：Ingestion 是什么？

Ingestion 中文一般叫**入库**、**数据接入**或**资料导入**。

在 RAG 里，ingestion 指的是：

**把原始资料加工成知识库能检索的数据。**

它不是简单“把文件存进去”。

更完整的流程是：

```text
原始文档
-> 读取 / 接入
-> 解析正文
-> 清洗去重
-> 脱敏和权限标记
-> 切成 chunk
-> 生成 metadata
-> 生成 embedding
-> 写入数据库 / 向量库
```

大白话：

**ingestion 就是 RAG 里的“把书整理进图书馆”。**

如果书没整理好，用户来问问题时，系统就找不到正确资料。

比如一份文档：

```text
SQL 解释助手能识别 select *、缺少 where、缺少 dt 分区等风险。
```

ingestion 后可能变成：

```json
{
  "chunk_id": "chunk_001",
  "content": "SQL 解释助手能识别 select *、缺少 where、缺少 dt 分区等风险。",
  "metadata": {
    "source": "notes/day13_sql_explainer_enhancement.md",
    "doc_type": "sql_risk_rule",
    "permission": "local_learning",
    "status": "active"
  },
  "embedding": [0.12, 0.08, -0.31]
}
```

生产环境里，ingestion 需要关注：

| 问题 | 为什么重要 |
|------|------------|
| 文档来源 | 判断资料是否可信 |
| 文档版本 | 避免回答过期内容 |
| 文档 hash | 判断是否需要增量更新 |
| 权限标签 | 防止用户看到无权限资料 |
| chunk 策略 | 影响后续召回质量 |
| metadata | 支持过滤、引用和审计 |
| embedding | 支持语义检索 |

一句话：

**ingestion 是 RAG 的离线入库链路，负责把原始资料变成可检索、可过滤、可引用的知识单元。**

---

> ## Q014：FastAPI 在 AI 服务化里承担什么角色？

FastAPI 在 AI 服务化里，主要承担**后端 API 服务层**的角色。

大白话：

**它把 Python 里的模型调用、RAG 检索、SQL 解释、NL2SQL 等能力，
包装成前端或其他系统可以调用的 HTTP 接口。**

比如本地脚本只能这样运行：

```bash
python3 main.py
```

但服务化以后，可以变成：

```text
POST /rag/ask
POST /sql/explain
POST /nl2sql
GET /health
```

前端、飞书机器人、内部系统、调度平台都可以通过接口调用它。

## 它在 AI 系统里的位置

一个常见 AI 服务链路是：

```text
前端 / 机器人 / 业务系统
-> FastAPI
-> 鉴权、参数校验、日志
-> RAG 检索 / Tool Use / SQL 校验
-> LLM 调用
-> 结构化输出校验
-> 返回 JSON 响应
```

FastAPI 不负责训练模型，也不负责当向量数据库。
它更像一个**服务入口和流程编排层**。

## FastAPI 具体负责什么？

| 职责 | 例子 |
|------|------|
| 提供 HTTP 接口 | `POST /rag/ask`、`POST /sql/explain` |
| 参数校验 | 检查 question、sql、top_k 是否合法 |
| 响应格式约束 | 返回 answer、citations、confidence、trace_id |
| 鉴权 | 判断用户是否能访问某个知识库 |
| 调用业务逻辑 | 调用 RAG 检索、SQL 风险检查、LLM |
| 统一异常处理 | 模型超时、向量库失败、参数错误 |
| 日志和监控 | 记录耗时、token、错误、用户请求 |
| API 文档 | 自动生成 Swagger / OpenAPI |

## 生产例子

RAG 问答接口可能长这样：

```python
@app.post("/rag/ask")
def ask(request: AskRequest) -> AskResponse:
    results = retriever.search(request.question, top_k=request.top_k)
    answer = llm.generate(question=request.question, context=results)
    return AskResponse(answer=answer.text, citations=answer.citations)
```

SQL 解释接口可能长这样：

```python
@app.post("/sql/explain")
def explain_sql(request: SQLExplainRequest) -> SQLExplainResponse:
    risk_result = sql_checker.check(request.sql)
    return risk_result
```

## 为什么 AI 项目需要 FastAPI？

因为真实项目里，AI 能力不能只停留在脚本。

脚本适合本地验证：

```text
我自己运行一次，看结果对不对。
```

API 服务适合生产接入：

```text
别人可以通过接口稳定调用，有鉴权、有日志、有错误处理、有监控。
```

一句话：

**FastAPI 是把 AI 能力从“本地脚本”变成“可被系统调用的线上服务”的关键后端层。**

---

> ## Q015：模拟一条数据在代码里的真实流转，在 RAG 中。

下面用信贷场景模拟一条数据在 RAG 代码里的真实流转。

假设原始数据是一份授信政策文档里的一条规则：

```text
文档：credit_policy_2026_v3.pdf
段落：近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。
业务域：授信准入
权限：risk_policy
版本：2026_v3
```

这条数据从进入系统到最终回答用户问题，大致会经历两条链路：

```text
离线入库链路：
原始文档 -> 解析清洗 -> 切分 chunk -> 生成 metadata -> embedding -> 写入索引

在线问答链路：
用户问题 -> 鉴权 -> 问题改写 -> query embedding -> metadata filter
-> 向量召回 -> rerank -> 拼 prompt -> LLM 生成 -> 安全校验 -> 返回答案
```

## 1. 原始文档进入 Loader

代码里第一步通常不是模型，而是文档加载。

```python
raw_doc = Document(
    doc_id="credit_policy_2026_v3",
    source_path="credit_policy_2026_v3.pdf",
    text="近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。",
    metadata={
        "business_domain": "credit_approval",
        "doc_type": "policy",
        "version": "2026_v3",
        "permission_level": "risk_policy"
    }
)
```

这时的数据还是“文档级数据”。它带着来源、版本、权限、业务域，但还不适合直接检索。

生产里这一层要处理 PDF、Word、HTML、数据库配置表、知识库页面等不同来源。
如果是信贷系统，还要特别关注政策版本、生效时间、产品线和权限级别。

## 2. Parser 和 Cleaner 清洗正文

接下来代码会解析文档正文，去掉页眉、页脚、乱码、重复空格和无意义字符。

```python
clean_text = clean_policy_text(raw_doc.text)
```

清洗后的结果可能是：

```text
近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。
```

这一步看起来普通，但很关键。
如果 PDF 解析错，把“不得通过”解析成“得通过”，后面 embedding、检索和生成都会建立在错误资料上。

## 3. Chunker 把文档切成知识单元

RAG 不会把整份政策文档都塞进向量库，而是切成 chunk。

```python
chunk = Chunk(
    chunk_id="credit_policy_2026_v3_chunk_018",
    doc_id=raw_doc.doc_id,
    content="近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。",
    page_no=12,
    start_offset=2380,
    end_offset=2428
)
```

这个 chunk 就是后续检索和引用的基本单位。

在生产里，chunk 不能只追求固定长度。
信贷政策、风控规则、指标口径这类内容，更适合按语义边界切分。
例如一条准入规则、一条拒绝规则、一条例外规则，最好不要被切断。

## 4. Metadata Tagger 给 chunk 打标签

然后系统会补充 metadata。

```python
chunk.metadata = {
    "business_domain": "credit_approval",
    "product": "cash_loan",
    "policy_type": "admission_rule",
    "risk_topic": "overdue_history",
    "permission_level": "risk_policy",
    "effective_date": "2026-01-01",
    "expire_date": None,
    "source_path": "credit_policy_2026_v3.pdf",
    "page_no": 12,
    "version": "2026_v3"
}
```

metadata 不是装饰字段，它决定后面能不能精准过滤。

比如用户问“近 90 天逾期还能不能授信”，系统应该优先找：

- `business_domain = credit_approval`
- `policy_type = admission_rule`
- `risk_topic = overdue_history`
- 当前日期仍在 `effective_date` 和 `expire_date` 范围内
- 用户权限允许访问 `risk_policy`

这就是 metadata filter 在真实代码里的价值。
它让 RAG 不是在全库里盲搜，而是在业务、权限、版本都正确的资料范围里检索。

## 5. Embedding Service 把 chunk 变成向量

接下来系统会调用 embedding 模型。

```python
vector = embedding_model.embed(chunk.content)
```

得到的不是文本，而是一组数字：

```python
vector = [0.021, -0.134, 0.088, ...]
```

这组数字表示这段文本的语义位置。

用户后面问“有过 M2 逾期还能自动审批吗”，即使没有完全命中原文里的“近 90 天”，向量检索也可能知道两者语义相关。

## 6. Index Writer 写入存储

入库时通常至少写两类存储：

```python
vector_store.upsert(
    id=chunk.chunk_id,
    vector=vector,
    metadata=chunk.metadata
)

doc_store.upsert(
    chunk_id=chunk.chunk_id,
    content=chunk.content,
    doc_id=chunk.doc_id,
    metadata=chunk.metadata
)
```

向量库负责相似度检索。
文档库或关系型数据库负责保存 chunk 正文、来源、版本、权限和审计字段。

生产里常见组合是：

- PostgreSQL：存文档、chunk、metadata、权限、版本、任务状态
- pgvector / Milvus：存 embedding，做向量检索
- OpenSearch：做关键词检索和日志检索
- Redis：缓存高频问题、召回结果或答案
- ClickHouse / Hive：分析日志、问题分布、召回效果和成本

到这里，原始段落已经从“一段政策文字”变成了可检索、可过滤、可引用的知识单元。

## 7. 用户发起在线问题

现在风控运营同学在系统里问：

```text
近 90 天有 M2 逾期记录的客户还能自动授信吗？
```

API 层收到请求：

```python
request = AskRequest(
    request_id="req_20260527_0001",
    user_id="u_10086",
    user_role="risk_operator",
    question="近 90 天有 M2 逾期记录的客户还能自动授信吗？",
    top_k=5
)
```

这时进入在线问答链路。

## 8. Auth Service 先做权限判断

RAG 不是先检索再说，而是先判断用户能不能访问这类资料。

```python
allowed_permissions = auth_service.get_allowed_permissions(request.user_id)
```

返回：

```python
allowed_permissions = ["public", "internal", "risk_policy"]
```

后面检索时会带上权限过滤条件。
如果用户只是客服角色，可能只能访问 `public` 和 `internal`，不能访问 `risk_policy`。

## 9. Query Preprocessor 处理用户问题

用户问题通常要先做标准化、意图识别和 query rewrite。

```python
normalized_query = normalize_question(request.question)
intent = classify_intent(normalized_query)
rewritten_query = rewrite_query(normalized_query, intent)
```

结果可能是：

```python
intent = "credit_policy_admission"

rewritten_query = (
    "授信准入 自动审批 近90天 M2逾期 逾期记录 风控政策"
)
```

用户原话更口语，改写后的 query 更适合检索。
但 rewrite 不能改变问题本意，只能补充业务同义词和检索关键词。

## 10. Query Embedding 生成问题向量

然后系统把改写后的 query 也变成向量。

```python
query_vector = embedding_model.embed(rewritten_query)
```

现在系统有两类向量：

- 入库时生成的 chunk vector
- 查询时生成的 query vector

向量检索就是计算 query vector 和 chunk vector 的相似度。

## 11. Retriever 带 metadata filter 检索

检索时不会只传一个向量，还会带过滤条件。

```python
filter_expr = {
    "business_domain": "credit_approval",
    "policy_type": "admission_rule",
    "permission_level": {"$in": allowed_permissions},
    "effective_date": {"$lte": "2026-05-27"},
    "expire_date": {"$is_null_or_gte": "2026-05-27"}
}

candidates = vector_store.search(
    vector=query_vector,
    top_k=20,
    filter=filter_expr
)
```

这一步会返回候选 chunk：

```python
candidates = [
    {
        "chunk_id": "credit_policy_2026_v3_chunk_018",
        "score": 0.89,
        "metadata": {
            "business_domain": "credit_approval",
            "policy_type": "admission_rule",
            "risk_topic": "overdue_history",
            "page_no": 12
        }
    }
]
```

注意这里先返回的可能只是 chunk id、score 和 metadata。
系统还要根据 chunk id 去 doc_store 取正文。

```python
chunks = doc_store.batch_get([item["chunk_id"] for item in candidates])
```

## 12. Reranker 对候选结果重新排序

向量检索负责“找一批可能相关的资料”，reranker 负责“把最能回答问题的资料排前面”。

```python
ranked_chunks = reranker.rank(
    query=request.question,
    chunks=chunks
)

top_chunks = ranked_chunks[:5]
```

生产里常见做法是先召回 20 到 100 条，再 rerank 到 3 到 8 条。
这样可以兼顾召回率和上下文成本。

## 13. Context Builder 组装上下文

系统会把 top chunks 组装成带引用编号的上下文。

```python
context_blocks = [
    {
        "citation_id": "C1",
        "content": "近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。",
        "source": "credit_policy_2026_v3.pdf",
        "page_no": 12
    }
]
```

真正进入 LLM 的不是向量，而是文本上下文。
向量只负责找到资料，LLM 最终读的是 chunk 正文。

## 14. Prompt Builder 拼接提示词

系统把系统规则、用户问题、检索上下文和输出格式拼成 prompt。

```python
prompt = build_prompt(
    system_rules=[
        "你是信贷政策问答助手。",
        "只能基于给定资料回答。",
        "如果资料不足，必须说明无法确定。",
        "回答必须给出引用。"
    ],
    question=request.question,
    context_blocks=context_blocks,
    output_schema={
        "answer": "string",
        "citations": "list",
        "confidence": "float"
    }
)
```

拼出来的核心内容类似：

```text
资料：
[C1] 近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。
来源：credit_policy_2026_v3.pdf，第 12 页

问题：
近 90 天有 M2 逾期记录的客户还能自动授信吗？

要求：
只基于资料回答，并给出引用。
```

## 15. LLM Client 生成答案

LLM 接收 prompt 后生成结构化结果。

```python
llm_result = llm_client.generate(prompt)
```

可能返回：

```json
{
  "answer": "根据现有授信政策，近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。",
  "citations": ["C1"],
  "confidence": 0.86
}
```

这里要注意：LLM 不是在数据库里查资料。
数据库检索已经由 retriever 完成，LLM 的职责是基于上下文做阅读、归纳和表达。

## 16. Guardrail 做安全和质量校验

返回用户前，系统还要检查答案是否合规。

```python
checked = guardrail.validate(
    question=request.question,
    answer=llm_result["answer"],
    citations=llm_result["citations"],
    context_blocks=context_blocks,
    user_role=request.user_role
)
```

常见校验包括：

- 是否引用了资料
- 是否回答了资料里没有的信息
- 是否泄露身份证号、手机号、银行卡号等敏感信息
- 是否越权展示风险策略细节
- 是否需要人工复核
- confidence 是否低于阈值

如果资料不足，系统应该拒答或要求补充条件，而不是编造。

## 17. API 返回最终响应

最终返回给前端的不是一段裸文本，而是结构化 JSON。

```json
{
  "request_id": "req_20260527_0001",
  "answer": "根据现有授信政策，近 90 天内出现 M2 及以上逾期记录的客户，原则上不得通过自动授信审批。",
  "citations": [
    {
      "citation_id": "C1",
      "source": "credit_policy_2026_v3.pdf",
      "page_no": 12
    }
  ],
  "confidence": 0.86,
  "can_answer": true
}
```

前端展示时，可以把引用来源展示出来，方便业务人员确认依据。

## 18. Trace Logger 记录整条链路

生产 RAG 必须记录链路日志，否则答错时无法排查。

```python
trace_logger.info({
    "request_id": request.request_id,
    "user_id": request.user_id,
    "question": request.question,
    "rewritten_query": rewritten_query,
    "filters": filter_expr,
    "retrieved_chunk_ids": [c["chunk_id"] for c in candidates],
    "reranked_chunk_ids": [c.chunk_id for c in top_chunks],
    "citations": llm_result["citations"],
    "confidence": llm_result["confidence"],
    "latency_ms": 830,
    "token_usage": {
        "prompt_tokens": 1320,
        "completion_tokens": 120
    }
})
```

这些日志后面可以用于：

- 排查某次回答为什么错
- 分析哪些问题高频
- 评估召回是否命中 expected source
- 统计 token 成本
- 优化 query rewrite、chunk、metadata 和 rerank
- 满足审计要求

## 一条数据的完整轨迹

如果把上面压缩成一条线，就是：

```text
政策段落
-> Document 对象
-> clean_text
-> Chunk 对象
-> metadata
-> embedding vector
-> vector_store / doc_store 记录
-> 用户 AskRequest
-> rewritten_query
-> query_vector
-> metadata filter
-> retrieved chunk_ids
-> chunk 正文
-> reranked context
-> prompt
-> LLM answer
-> guardrail checked answer
-> API response
-> trace log
```

## 对应到真实代码模块

生产项目里通常会拆成这些模块：

```text
api/rag_router.py          接收 HTTP 请求，返回 JSON
services/rag_service.py    编排完整 RAG 链路
ingestion/loader.py        读取原始文档
ingestion/parser.py        解析和清洗正文
ingestion/chunker.py       切分 chunk
ingestion/metadata.py      生成业务标签、权限标签、版本标签
stores/vector_store.py     写入和查询向量库
stores/doc_store.py        保存 chunk 正文和来源
retrieval/query_rewrite.py 改写用户问题
retrieval/retriever.py     向量检索和 metadata filter
retrieval/reranker.py      候选结果重排
llm/prompt_builder.py      拼接 prompt
llm/client.py              调用模型
guardrails/validator.py    校验引用、权限、敏感信息和拒答逻辑
observability/tracing.py   记录 request_id、耗时、召回和 token
```

所以，一条数据在 RAG 里不是“文档进去，答案出来”这么简单。

它会不断变形：

```text
原始业务资料 -> 可解析文本 -> 可检索 chunk -> 可过滤 metadata
-> 可计算相似度的 vector -> 可引用 context -> 可审计 answer
```

站在信贷开发视角，最重要的是理解：

RAG 的核心不是让模型记住授信政策，而是让代码链路在正确权限、正确版本、正确业务域下，把最相关的政策片段找出来，再让模型基于这些片段生成可引用、可审计、可回放的回答。

---

> ## Q016：模拟一条数据在代码里的真实流转，在 NL2SQL 中。

这条问题用下面这个真实样例来模拟：

```text
本周逾期率比上周变化多少？
```

当前项目里的真实链路不是一个函数直接一层层调用，而是 Day 30-Day 34 先各自产出 JSON，
Day 35 再把这些 JSON 按 `question` 串起来。
整合入口是：

```text
projects/day35_nl2sql_assistant/main.py
```

完整链路是：

```text
用户问题
-> 问题解析
-> SQL 生成
-> SQL 校验
-> 查询执行
-> 结果解释
-> 业务回答
```

## 1. 原始输入

用户输入：

```text
本周逾期率比上周变化多少？
```

Day 35 会读取前面各阶段产物：

```python
parse_payload = load_json(PARSE_RESULT_PATH)
generation_payload = load_json(GENERATION_RESULT_PATH)
validation_payload = load_json(VALIDATION_RESULT_PATH)
execution_payload = load_json(EXECUTION_RESULT_PATH)
interpretation_payload = load_json(INTERPRETATION_RESULT_PATH)
```

然后按 `question` 建索引，把同一个问题在不同阶段的结果合并成一条 trace。

## 2. 问题解析

Day 30 把自然语言问题解析成结构化意图：

```json
{
  "query_type": "comparison",
  "metrics": ["overdue_rate"],
  "dimensions": [],
  "time_range": "this_week_vs_last_week",
  "filters": {},
  "risk_flags": []
}
```

这说明系统已经理解到：

```text
这是一个对比查询；
要看的指标是逾期率；
时间范围是本周对比上周；
没有额外过滤条件；
没有命中敏感风险。
```

## 3. SQL 生成

Day 31 根据 `overdue_rate` 和 `this_week_vs_last_week` 生成对比 SQL：

```sql
with current_period as (
  select sum(overdue_amount) / nullif(sum(due_amount), 0) as current_value
  from dws_repayment_overdue_daily
  where dt >= date_trunc('week', current_date) and dt < current_date + interval '1' day
),
previous_period as (
  select sum(overdue_amount) / nullif(sum(due_amount), 0) as previous_value
  from dws_repayment_overdue_daily
  where dt between date_trunc('week', current_date) - interval '7' day and date_trunc('week', current_date) - interval '1' day
)
select
  current_value,
  previous_value,
  current_value - previous_value as diff_value
from current_period
cross join previous_period;
```

这里最关键的一点是：

```text
逾期率不是 avg(overdue_rate)，而是 sum(overdue_amount) / sum(due_amount)。
```

比例指标不能随便平均，否则业务口径会错。

## 4. SQL 校验

Day 32 对 SQL 做执行前校验：

```json
{
  "can_execute": true,
  "risk_level": "low",
  "issues": [],
  "warnings": []
}
```

这表示：

```text
SQL 是只读查询；
表在 Schema Catalog 白名单里；
没有敏感字段；
有时间范围；
没有 delete、update、drop 等危险关键字；
可以进入查询执行层。
```

## 5. 查询执行

Day 33 执行通过校验的 SQL，并返回结构化结果：

```json
{
  "status": "executed",
  "response_type": "comparison",
  "row_count": 1,
  "summary_text": "当前值 0.0703，上期值 0.0856，差值 -0.0153。"
}
```

数据库查询出的核心结果是：

```json
{
  "current_value": 0.0703,
  "previous_value": 0.0856,
  "diff_value": -0.0153
}
```

## 6. 结果解释

Day 34 把结构化结果解释成业务语言：

```json
{
  "business_answer": "当前周期逾期率为 7.03%，上期为 8.56%，较上期下降 1.53 个百分点。",
  "key_findings": [
    "当前值：7.03%。",
    "上期值：8.56%。",
    "变化值：-1.53 个百分点。"
  ],
  "risk_notes": [
    "比例指标必须说明分子分母口径，不能只看差值判断风险已经改善。"
  ],
  "follow_up_questions": [
    "是否需要按产品、风险等级或逾期账龄拆分变化原因？"
  ]
}
```

这一步只解释查询结果，不编造业务原因。
比如它可以说“逾期率下降 1.53 个百分点”，但不能直接说“因为风控策略变好了”，
除非继续查询产品、风险等级、账龄等拆分数据来验证。

## 7. 最终 trace

Day 35 整合后的链路状态是：

```json
{
  "question": "本周逾期率比上周变化多少？",
  "final_status": "answered",
  "query_type": "comparison",
  "pipeline": {
    "parse": "available",
    "sql_generation": "passed",
    "sql_validation": "passed",
    "query_execution": "executed",
    "result_interpretation": "available"
  }
}
```

如果把它压成一条线，就是：

```text
用户问题
-> comparison + overdue_rate + this_week_vs_last_week
-> 生成本周/上周两个时间窗口 SQL
-> SQL Validator 放行
-> 执行层查出 0.0703、0.0856、-0.0153
-> 解释层输出“逾期率下降 1.53 个百分点”
```

## 8. 对应代码模块

当前项目里对应这些位置：

```text
projects/day30_nl2sql_question_parser/
  负责问题解析：指标、时间、过滤条件、风险标记

projects/day31_nl2sql_sql_generator/
  负责根据结构化解析结果生成 SQL

projects/day32_nl2sql_sql_validator/
  负责执行前校验：只读、白名单、敏感字段、时间范围

projects/day33_nl2sql_query_executor/
  负责执行安全 SQL，并格式化结果

projects/day34_nl2sql_result_interpreter/
  负责把结构化查询结果解释成业务语言

projects/day35_nl2sql_assistant/
  负责把 Day 30-Day 34 的结果串成端到端演示 trace
```

所以，NL2SQL 中一条数据不是“问题进去，SQL 出来”这么简单。

它会不断变形：

```text
自然语言问题
-> 结构化意图
-> 只读 SQL
-> 校验结果
-> 查询结果
-> 业务解释
-> 可审计 trace
```

站在信贷开发视角，最重要的是理解：

NL2SQL 的核心不是让模型会写 SQL，而是让代码链路在正确表字段、正确指标口径、正确权限、
正确时间范围和正确安全边界下，把用户问题变成可执行、可解释、可审计的数据问答结果。
