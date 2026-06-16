# AI 面试题库网站

在线刷题网站，题库从 GitHub 实时拉取最新内容，支持浏览、搜索、分类筛选、顺序练习、随机练习和错题集。

## 题库来源

网站启动时自动从 GitHub Raw 拉取两份题库文件：
- [面试鸭 LLM 题库](https://raw.githubusercontent.com/lxy1553/ai-transition/main/docs/mianshiya_llm_interview_questions.md) — 93 题（微调/PEFT、RAG、Prompt、Agent、MCP、工程）
- [核心面试题库](https://raw.githubusercontent.com/lxy1553/ai-transition/main/docs/interview_core_questions.md) — ~123 题（RAG、NL2SQL、Agent、工程化、金融信贷仓库）

更新 GitHub 上的 md 文件后，刷新页面即可获取最新题目。

## 功能

- **浏览模式**：分类树筛选 + 全文搜索 + 难度/来源过滤，点击展开答案
- **Markdown 渲染**：支持代码高亮（highlight.js）、数学公式（KaTeX）
- **顺序练习**：按分类逐题学习，标记已掌握/需复习/跳过
- **随机练习**：随机出题，检验掌握程度
- **错题集**：自动记录需复习的题目（localStorage 持久化）
- **难度标签**：困难/中等/简单（从重要程度映射）
- **响应式**：桌面三栏布局，移动端自适应

## 启动

```bash
cd projects/interview_qa_website
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

也可以部署到 GitHub Pages、Vercel 等静态托管平台。

## 快捷键

- `Ctrl+K`：聚焦搜索框

## 技术栈

纯静态站，无框架依赖：
- marked.js — Markdown 渲染
- highlight.js — 代码高亮
- KaTeX — 数学公式
- localStorage — 错题集 + 练习进度 + 题库缓存
