---
id: Q133
source: interview_core
category: Agent
title: 为什么金融信贷 Agent 服务化必须先定 request_id 和审计结构？
generated: 2026-07-23T15:41:19.826988
---

# 为什么金融信贷 Agent 服务化必须先定 request_id 和审计结构？

> 来源: 核心题库 | 分类: Agent

Agent 不能只停留在本地脚本，因为本地脚本无法接入前端、调试平台或演示接口，
没有 request_id 和 trace_id，bad case 无法定位和回放。
服务化的核心是先定审计字段骨架，再逐步扩展接口能力。

**request_id 和 trace_id 分别解决什么问题？**
request_id 是一次业务请求的唯一标识，对外暴露给调用方，用于请求定位和状态查询。
trace_id 是分布式链路追踪 ID，在 Agent、工具、数据源之间传播，用于串联所有节点。
一个 request_id 下可以有多个 span，trace_id 负责把它们串成完整调用链。
request_id 定位"哪个请求出了问题"，trace_id 定位"问题出在哪个节点"。

**审计需要分类记录，通常分为四类：**
- 查询审计：记录用户问了什么、查了哪张表、SQL 是什么、返回了多少行
- 告警审计：记录告警是否正常触发、延迟状态、告警规则版本和证据快照
- 任务审计：记录调度任务执行状态、产出分区、失败原因和补偿执行情况
- 权限审计：记录用户访问了哪些表字段、是否触发安全阻断、阻断原因是什么

**审计字段必须结构化，不能只存自然语言日志。**
原因有三：第一，结构化字段可以被程序稳定解析、校验和路由，status 和 error_code
必须用固定枚举；第二，可以触发告警，比如 safely_blocked 比例超过阈值自动报警；
第三，回归测试可以按结构化字段精准匹配预期结果。

**服务化接口至少应该固定这些状态和错误码：**
- `success`：正常回答
- `safely_blocked`：安全阻断（权限不足、敏感字段、危险 SQL）
- `clarification_required`：缺少必要参数（时间范围、窗口、维度）
- `execution_failed`：工具执行失败（超时、数据库异常、模型不可用）
- `system_error`：系统异常（配置错误、依赖缺失）

如果每次请求没有 request_id、trace_id 和统一状态，后续即使发现错误答案，
也很难知道问题出在模型、工具还是数据链路。先定审计字段骨架，
包括 request_id、trace_id、user_id、scenario、intent、tool_route、model_id、status、
latency_ms 和 error_code，再逐步扩展接口能力。