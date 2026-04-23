# Day 1 - 2026-04-22

## 今日主题

定位与环境搭建

## 今日目标

- 明确目标岗位与优先级
- 搭建 Python 开发环境
- 初始化 AI 转型学习仓库
- 产出岗位目标文档和学习笔记

## 今日任务拆解

### 任务 1：明确岗位目标

- [x] 阅读并补充 `docs/job_targets.md`
- [x] 选定主攻方向：RAG / NL2SQL / 数据问答工程师
- [x] 列出 3 个备选岗位名称
- [ ] 从招聘平台收集 10 个 JD，填写 `docs/jd_tracking_day01.md`

### 任务 2：搭建 Python 环境

- [x] 确认 Python 版本：`Python 3.9.6`
- [x] 创建虚拟环境：`.venv`
- [x] 安装基础依赖
- [x] 导出 `requirements.txt`

建议依赖：

- `openai`
- `fastapi`
- `uvicorn`
- `pandas`
- `python-dotenv`
- `requests`

### 任务 3：初始化仓库结构

- [x] 检查当前目录结构
- [x] 补齐 `docs/`、`notes/`、`projects/`
- [x] 完善 `README.md`
- [x] 当前目录已位于 `bi_cube1` Git 仓库内，无需单独初始化

### 任务 4：做一个最小可运行产物

二选一即可： 

- [ ] 写一个读取 CSV 的 Python 脚本
- [x] 写一个 FastAPI `/health` 接口

## 建议时间安排

### 上午

- 09:30 - 10:30：岗位定位
- 10:30 - 12:00：环境搭建

### 下午

- 14:00 - 15:30：仓库初始化
- 15:30 - 17:00：写最小代码产物
- 17:00 - 18:00：整理文档和复盘

## 今日产出物

- [x] `README.md`
- [x] `docs/job_targets.md`
- [x] `notes/day01.md`
- [x] Python 虚拟环境
- [x] `requirements.txt`
- [x] 一个最小可运行 API

## 当前验证结果

- 虚拟环境路径：`/Users/longfeiguo/PycharmProjects/bi_cube1/ai_transition/.venv`
- 关键依赖导入验证：`fastapi`、`pandas`、`openai`、`requests`
- FastAPI 示例路径：`projects/day01_fastapi_demo/app.py`
- `/health` 返回：

```json
{"status":"ok","day":1,"topic":"positioning-and-environment-setup"}
```

## 今日学习记录

### 我今天实际做了什么

- 把 AI 转型学习资料迁移到了 `bi_cube1/ai_transition`
- 确定了两个月主攻方向：RAG / NL2SQL / 数据问答工程师
- 创建了 Day 1 文档、岗位目标文档和总 README
- 创建了 `.venv` 并安装了 Day 1 基础依赖
- 写了一个最小 FastAPI `/health` 示例，并完成本地验证

### 我遇到的问题

- 原来的钉钉提醒脚本从 `Documents` 目录运行时被后台权限限制
- 本地沙箱直接绑定端口被拦截，导致启动 FastAPI 初次失败
- `urllib3` 在当前 Python 环境下提示 `LibreSSL` 警告

### 我怎么解决的

- 把定时任务运行时目录迁到 `~/.codex/dingtalk-study`
- 在需要时用本地授权方式启动 FastAPI，并完成 `/health` 校验
- 记录 `LibreSSL` 警告为当前环境提示，Day 1 不阻塞继续学习

## 今日复盘

### 今天完成得最好的 3 件事

1. 把学习目录正式迁到 `bi_cube1/ai_transition`
2. 把岗位方向收敛到了最适合当前背景的路径
3. 今天没有只停留在搭环境，已经做出了最小可运行 API

### 今天最卡的 3 个点

1. 后台定时任务对 `Documents` 目录访问不稳定
2. 本地端口启动受限，需要额外授权验证
3. 还没有完成 10 个目标 JD 的技能词整理

### 明天要避免什么

- 不要一开始就学太多框架
- 不要跳过 Python 基础直接冲 RAG 实战

## 明日预告
a

Day 2：Python 基础补齐

重点：

- 函数
- 模块
- 文件处理
- 小脚本拆分能力

## 今天剩余待完成

- [ ] 从招聘平台收集 10 个目标 JD，填写 `docs/.md`
- [ ] 补充 `docs/job_targets.md` 中的高频技能词
- [ ] 在今天下班前把 Day 1 笔记再补一遍个人真实感受
