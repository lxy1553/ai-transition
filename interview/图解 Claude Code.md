---
title: 图解 Claude Code
url: http://xiaolinnote.com/claudecode/
scraped: 2026-07-23T11:37:51.955705
---

# 图解 Claude Code

> 原文链接: http://xiaolinnote.com/claudecode/

# 图解 Claude Code

公众号@小林coding图解Claude Code小于 1 分钟约 248 字

---

[![](https://cdn.xiaolincoding.com//picgo/b43570a4-mewcode-warm-landscape-poster.png)](https://www.xiaolincoding.com/project/mewcode.html)

大家好，我是小林。

这里是「**图解 Claude Code**」专栏，从源码到实战，带你彻底吃透这款最强终端编程 Agent。

无论是面试被追问实现原理，还是日常想把 Claude Code 用得更顺手，都能在这里找到答案。目前分为五个方向：

* **基础入门**：基础使用技巧、/powerup 官方互动教程，新手快速上手。
* **实践技巧**：[CLAUDE.md](http://CLAUDE.md) 维护、大型代码库实战、Skill 编写、规约驱动开发等进阶用法。
* **提示词工程**：拆解 Fable 5 等系统提示词，偷师顶级 Agent 的 prompt 设计。
* **源码解析**：主循环、上下文压缩、代码检索、记忆机制、多 Agent 等核心实现。
* **行业观察**：Anthropic 研究报告解读、AI 编程趋势分析，看清方向再动手。

## 目录

* ### [Claude Code 基础入门](/claudecode/basics/)

  + [Claude Code 使用教程：新手入门必学的基础技巧](/claudecode/basics/cc_use.html)
  + [Claude Code /powerup 教程：18 个官方互动课程全解析](/claudecode/basics/cc_powerup.html)
* ### [Claude Code 实践技巧](/claudecode/playbook/)

  + [CLAUDE.md 指南：Claude Code 的项目记忆该怎么写？](/claudecode/playbook/cc_claude_md.html)
  + [Claude Code 大型代码库实战：百万行代码怎么扛得住？](/claudecode/playbook/cc_large_codebase.html)
  + [Claude Code Skill 揭秘：Skill 真的只是一份 markdown 吗？](/claudecode/playbook/cc_skills.html)
  + [SDD 规约驱动开发实战：在 Claude Code 里跑通先规约后编码](/claudecode/playbook/spec_driven_dev.html)
  + [grill-me 使用指南：写代码前，先让 Claude Code 审问你的需求](/claudecode/playbook/grill_me.html)
  + [superpowers vs grill-me：同一个需求实测，差距到底在哪？](/claudecode/playbook/superpowers_vs_grillme.html)
* ### [Claude Code 提示词工程](/claudecode/prompt/)

  + [Claude Fable 5 系统提示词详解：1600 行泄漏 prompt 里的工程干货](/claudecode/prompt/fable5_prompt_leak_cl4.html)
* ### [Claude Code 源码解析](/claudecode/source/)

  + [Claude Code 源码拆解：51 万行泄漏代码里的架构设计](/claudecode/source/cc_source.html)
  + [Claude Code 主循环 Query 图解：一轮对话是怎么跑起来的？](/claudecode/source/cc_query_loop.html)
  + [Claude Code 上下文管理图解：Compact 压缩机制怎么实现？](/claudecode/source/cc_compact.html)
  + [Claude Code 代码检索图解：为什么用 grep 而不用 RAG？](/claudecode/source/cc_grep.html)
  + [Claude Code 记忆机制图解：为什么不用向量数据库？](/claudecode/source/cc_memory.html)
  + [Claude Code 多 Agent 图解：SubAgent 实现机制怎么做？](/claudecode/source/cc_multi_agent.html)
* ### [Claude Code 行业观察](/claudecode/insights/)

  + [Anthropic 40 万次会话研究：用好 AI 编程的关键不是会写代码](/claudecode/insights/expertise_over_coding.html)