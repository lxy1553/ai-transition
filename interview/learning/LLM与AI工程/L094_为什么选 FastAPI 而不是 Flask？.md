---
id: L094
source: learning
category: LLM与AI工程
title: 为什么选 FastAPI 而不是 Flask？
generated: 2026-07-23T15:41:19.871863
---

# 为什么选 FastAPI 而不是 Flask？

> 来源: 学习复习计划 | 分类: LLM与AI工程

| 维度 | FastAPI | Flask |
|------|---------|-------|
| 异步支持 | 原生 async/await，性能高 | 需额外扩展（gevent/asyncio） |
| 数据校验 | 自动基于 Pydantic，类型安全 | 需手动写校验逻辑或插件 |
| API 文档 | 自动生成 Swagger/ReDoc | 需额外安装 flasgger 等 |
| 性能 | 接近 NodeJS/Go | 同步模型下并发能力受限 |
| 生态 | 完美兼容 Starlette 生态，与 Pydantic、SQLAlchemy 无缝集成 | 庞大但逐渐老旧 |

生产级 AI 应用对**低延迟、高并发、严格的输入输出定义**要求很高，FastAPI 在这些方面是当前 Python 生态的最优解。

---

**一句话总结：FastAPI 是现代 Python 构建高性能、类型安全 API 的事实标准，
它在 AI 系统中充当推理网关，通过异步能力、自动校验和文档生成，将模型服务化过程变得极其高效和可靠。**