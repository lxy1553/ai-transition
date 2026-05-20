# Day 16 - RAG 基础 Demo

这个项目用本地代码模拟 RAG 的核心流程，不调用真实 LLM，也不依赖向量数据库。

## 运行

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day16_rag_basics/main.py
```

## 流程

```text
加载文档
-> 切分 chunk
-> 生成简单向量
-> 计算相似度
-> 返回 top-k 结果
-> 生成带引用的回答草稿
```

## 注意

这里的 embedding 是学习用的简化版本，只按关键词做向量。

真实项目里会使用 embedding 模型生成语义向量。
