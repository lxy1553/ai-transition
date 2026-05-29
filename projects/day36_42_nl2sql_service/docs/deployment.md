# Day 42 - 部署说明

## 本地启动

```bash
cd /Users/lxy/Documents/ai_transition
PYTHONPATH=projects/day36_42_nl2sql_service \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 冒烟检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/nl2sql/questions
curl -X POST http://127.0.0.1:8000/nl2sql/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"导出客户手机号列表","user_id":"demo_user"}'
```

期望结果：

- `/health` 返回 `demo_ready=true`；
- 成功查询返回 `final_status=answered`；
- 敏感查询返回 `final_status=safely_blocked`；
- `output/audit.sqlite` 中能查到审计记录。

## Docker

```bash
docker build -f projects/day36_42_nl2sql_service/Dockerfile -t nl2sql-week6 .
docker run --rm -p 8000:8000 nl2sql-week6
```

## 常见问题

### `demo_artifact_missing`

先运行 Day 35：

```bash
python3 projects/day35_nl2sql_assistant/main.py
```

### 模块导入失败

确认设置了 `PYTHONPATH`：

```bash
export PYTHONPATH=projects/day36_42_nl2sql_service
```

### 审计文件不可写

确认 `projects/day36_42_nl2sql_service/output/` 存在且当前用户可写。

