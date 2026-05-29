# Day 40 - 存储选型说明

## 当前选择

Week 6 学习版使用 SQLite 保存审计记录：

```text
projects/day36_42_nl2sql_service/output/audit.sqlite
```

保存字段：

- `request_id`
- `question`
- `user_id`
- `final_status`
- `created_at`
- `details_json`

## 为什么先用 SQLite

- 本地可运行，不需要外部数据库；
- 便于提交演示产物和复现；
- 适合保存少量审计记录；
- 和后续 Postgres 表设计很接近，迁移成本低。

## 生产替换方向

真实生产建议使用：

- Postgres / MySQL：保存请求、状态、用户、耗时、行数、错误码；
- 日志平台：保存完整链路日志；
- 对象存储：保存大结果或导出文件；
- 权限系统：控制 trace 接口访问范围。

SQLite 不适合高并发写入、多实例共享和复杂权限管理。

