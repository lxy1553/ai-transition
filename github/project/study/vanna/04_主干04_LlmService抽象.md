# 主干 ④：LlmService 抽象

> **状态**：⬜ 未学完
> **代码位置**：`src/vanna/core/llm/base.py`（40 行）

---

## 三问（先想清楚再读代码）

- **Q1 解决什么问题**：统一所有 LLM 的接口，让 Agent 不关心底层是 OpenAI 还是 Ollama
- **Q2 数据流哪一环**：Agent 循环里"发 LLM 请求"那一步：`llm_service.send_request(request)`
- **Q3 删掉会怎样**：每种 LLM 一套调用，换模型要改 Agent 代码 → 耦合

## 核心骨架（待填充）

```python
class LlmService(ABC):
    async send_request(request) -> LlmResponse      # 非流式
    async stream_request(request)                   # 流式（async generator）
    async validate_tools(tools) -> List[str]        # 工具校验
```

## 已了解

- 你的 `LLMClient` 接口（chat/chat_json）就是它的雏形
- 但 LlmService 多了：流式（stream_request）+ 工具校验（validate_tools）
- 生产实现都在 `integrations/`：openai/ollama/anthropic 各一个文件，实现同一接口 → 可插拔

## 待学内容

- 接口完整解读
- 一个真实实现（OpenAI 或 Ollama）怎么实现 send_request/stream_request
- 对比你的 LLMClient 缺什么

## 对照 ai_assistant

你的 `LLMClient` 已有 chat/chat_json → 补流式（stream_chat），对接 SSE 前端。

> 核心心法：所有 LLM 实现同一接口，Agent 只认接口——这就是可插拔。
