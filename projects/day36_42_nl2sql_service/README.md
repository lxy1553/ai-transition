# Day 36-42 - NL2SQL 服务化交付项目

这个项目把 Day 35 的 NL2SQL 助手演示包封装成一个 FastAPI 后端服务。

第 6 周目标不是继续增加 NL2SQL 规则，而是把已有能力整理成更接近生产交付的形态：

- Day 36：后端重构，拆分 `config / schemas / services / storage / errors / main`；
- Day 37：接口设计，统一请求、响应和错误格式；
- Day 38：Docker 化，提供可构建镜像的 Dockerfile；
- Day 39：配置管理，使用环境变量和 `.env.example`；
- Day 40：数据存储，用 SQLite 保存审计轨迹；
- Day 41：测试基础，提供最小 API 回归测试；
- Day 42：部署说明，整理启动、验证、故障排查和交付清单。

## 本地启动

```bash
cd /Users/lxy/Documents/ai_transition
PYTHONPATH=projects/day36_42_nl2sql_service \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 常用接口

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/nl2sql/questions
curl -X POST http://127.0.0.1:8000/nl2sql/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"本周逾期率比上周变化多少？","user_id":"demo_user"}'
```

## 运行测试

```bash
cd /Users/lxy/Documents/ai_transition
PYTHONPATH=projects/day36_42_nl2sql_service python3 -m unittest discover \
  -s projects/day36_42_nl2sql_service/tests
```

也可以用接口手动回归：

```bash
PYTHONPATH=projects/day36_42_nl2sql_service python3 - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
print(client.get("/health").json())
print(client.post("/nl2sql/ask", json={"question": "导出客户手机号列表"}).json())
PY
```

## Docker 构建

```bash
cd /Users/lxy/Documents/ai_transition
docker build -f projects/day36_42_nl2sql_service/Dockerfile -t nl2sql-week6 .
docker run --rm -p 8000:8000 nl2sql-week6
```

## 生产映射

这个服务仍然是学习版，查询结果来自 Day 35 的演示 JSON。
但它已经具备生产项目的基本形态：

- API 层只负责请求响应；
- service 层负责业务编排；
- storage 层负责审计记录；
- config 层负责环境差异；
- errors 层统一错误输出；
- tests 负责最小回归。

后续可以把 Day 35 的静态 JSON 替换成真实 parser、generator、validator、executor 和 interpreter。
