# QueryForge 阶段 D：部署 + 迁移（能上线）

> **这是"工程化落地"的最后一环**——Docker 编排 + 数据库迁移。
> 对比你 ai_assistant：你的还没部署，QueryForge 有完整 docker-compose + alembic。
>
> **代码位置**：`docker-compose.yml` + `docker/` + `alembic/versions/` + `Makefile`

---

## 三问

- **Q1 解决什么问题**：让服务能一键部署——依赖（PG/Redis/ES/监控）+ 数据库建表
- **Q2 数据流哪一环**：最外层——部署后服务才能跑
- **Q3 删掉会怎样**：只能本地跑，无法上线

---

## 一、Docker 编排（docker-compose.yml）

```yaml
services:
  postgres:            # 主数据库（pgvector 向量 + pg_jieba 分词）
    image: queryforge/postgres-pgvector-jieba:16
  redis:               # 缓存 + 限流
    image: redis:7-alpine
  elasticsearch:       # 可选关键词检索后端
    image: elasticsearch:8.13.4
  prometheus:          # 监控
    image: prom/prometheus:latest
  grafana:             # 监控看板
    image: grafana/grafana:latest
  app:                 # 主服务
    build: .
    depends_on: [postgres, redis]
```

**大白话**：一套 docker-compose 起 6 个服务——数据库、缓存、可选的 ES、监控（Prometheus/Grafana）、主服务。**`docker compose up` 一键起**。

---

## 二、数据库迁移（alembic）

```python
# alembic/versions/ —— 5 个迁移（按顺序执行）
0001_initial.py        # 建基础表
0002_query_cache.py    # 加缓存表
0003_auth_sessions.py  # 加用户/会话表
0004_comments.py       # 加注释
0005_chat_message_turn_id.py  # 加轮次ID
```

```bash
make migrate   # alembic upgrade head（建扩展与表，含 query_cache）
```

**大白话**：alembic = 数据库版本管理——每次改表结构加一个迁移文件，`migrate` 自动按顺序执行。**建表/加列/加索引都通过迁移，不手动改库**。

**关键**（CLAUDE.md）：
```python
# alembic env 用应用配置 DSN 并替换为 postgresql+psycopg://
# 迁移里直接 op.execute 原生 SQL 建 vector/tsvector 列与索引
```

**大白话**：迁移里直接写原生 SQL 建向量列（pgvector）和全文索引（tsvector）。

---

## 三、Makefile（常用命令）

```makefile
make install        # pip install -e ".[eval,dev]"
make infra-up       # docker compose 起 postgres/redis/prometheus/grafana
make migrate        # alembic upgrade head（建表）
make ingest         # 灌 CSpider schema + few-shot 进 pgvector
make run            # uvicorn app.main:app --reload
make test           # pytest（纯逻辑单测，无需基础设施/LLM）
make smoke          # CSpider dev 抽样端到端冒烟
make loadtest       # 100 QPS 开环压测
make lint / fmt     # ruff
```

**大白话**：一条 Makefile 串起完整流程——装依赖 → 起基础设施 → 建表 → 灌数据 → 跑 → 测试 → 压测 → 冒烟。

---

## 四、完整部署流程（一图）

```
make infra-up       # 起 PG/Redis/监控
make migrate        # 建表（含向量/索引）
make ingest         # 灌数据（schema/few-shot）
make run            # 起服务
make smoke          # 冒烟验证
make loadtest       # 压测看 QPS
```

**大白话**：部署 = 起依赖 → 建表 → 灌数据 → 起服务 → 验证。

---

## 五、配置驱动（core/config.py）

```python
# pydantic-settings，从 .env 读
LLM_MODEL          # 模型名
EMBEDDING_DIM      # 向量维度（★ 必须与建表索引一致）
RETRIEVAL_BACKEND  # es / pg_jieba
REDIS_ENABLED      # 是否启用 Redis
RATE_LIMIT_DEFAULT # 限流阈值
```

**大白话**：**配置驱动，换组件不改代码**——模型/维度/检索后端/缓存全在 .env 配。改维度要重建迁移（索引一致）。

---

## 六、对照 ai_assistant 的改造动作

```python
# ① Dockerfile（把你的服务容器化）
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ② docker-compose（起依赖）
services:
  app:
    build: .
    depends_on: [redis]
  redis:
    image: redis:7-alpine
```

**改造要点**：Dockerfile + docker-compose——一键部署你的 ai_assistant。

---

## 七、小结

| 学到 | 一句话 |
|------|--------|
| docker-compose | 一键起依赖（PG/Redis/监控）|
| alembic 迁移 | 数据库版本管理，建表/向量索引 |
| Makefile | 一条命令串流程 |
| 配置驱动 | 换组件不改代码 |
| 部署流程 | 起依赖→建表→灌数据→起服务→验证 |

> **核心心法**：能上线 = Docker 编排 + 数据库迁移 + 配置驱动 + Makefile 流程。你的 ai_assistant 加 Dockerfile + compose，就能一键部署。
