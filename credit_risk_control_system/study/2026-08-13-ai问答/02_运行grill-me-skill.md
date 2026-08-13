# 提问：我下载了一个 skill 叫 grill-me，运行它

## 我的提问

> 我下载了一个 skill 叫 grill-me，运行它

## 回答

我先定位了这个 skill，发现它在项目里是一个软链接：

```
.claude/skills/grill-me → ../../.agents/skills/grill-me
```

它的 SKILL.md 内容很简短：

```yaml
---
name: grill-me
description: A relentless interview to sharpen a plan or design.
disable-model-invocation: true
---

Run a `/grilling` session.
```

**关键发现**：
1. `disable-model-invocation: true` —— 它刻意禁止模型"自动"调用，只能你主动触发（grill-me 很消耗，不该自己冒出来）
2. SKILL.md 正文只有一句 `Run a /grilling session.`，但项目里**并没有定义 `/grilling` 命令**——这是个不完整的 stub
3. 它的 `agents/openai.yaml` 是给 OpenAI Agents SDK 用的，Claude Code 不读

所以当时我尝试调用 `Skill(grill-me)` 时报了 `Unknown skill`，原因是：**Claude Code 的可用 skills 列表是会话启动时加载固定的**，而且软链接可能没被扫描到。

我直接进入了 grilling 模式，问你"想拷问哪个对象"，你选了"刚讲的数据流转模拟"。
