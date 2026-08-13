# 提问：直接配置好，然后随时能用

## 我的提问

> 直接配置好，然后随时能用

## 回答

做了两件事，把 grill-me 配置成随时能用的 skill：

### 1. 软链接 → 真实目录

Claude Code 之前扫不到软链接，所以把它换成真实目录：

```bash
rm .claude/skills/grill-me
cp -r .agents/skills/grill-me .claude/skills/grill-me
```

### 2. 补全 SKILL.md 方法论

原来的 SKILL.md 只有一句 `Run a /grilling session.`，没有实际内容。我补全了完整的 grilling 流程：

- **工作方式**：先确认对象（没指定就用 AskUserQuestion 列候选）→ 逐条开火 → 分级标注 → 收尾给修正版
- **严重度分级**：🔴致命伤 / 🟠中伤 / 🟡小伤
- **每条三件套**：问题陈述 → 为什么是漏洞（凭据）→ 正确做法（可执行）
- **拷问维度**：技术正确性、时间口径、边界情况、数据质量、假设质疑、可解释性、成本性能、安全合规
- **输出格式**：固定模板

### 结论

配置完成后，**重启一次 Claude Code** 就能用 `/grill-me <对象>` 触发。但本会话因为启动时没加载，还是 `Unknown skill`，所以本会话内用对话触发（消息里说"grill"）。

当时我说明了这一点，并问你要不要把配置提交到 git，你说"先这样"。
