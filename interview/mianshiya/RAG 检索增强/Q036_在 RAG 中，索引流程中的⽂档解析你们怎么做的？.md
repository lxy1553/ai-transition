---
id: Q036
source: mianshiya
category: RAG 检索增强
title: 在 RAG 中，索引流程中的⽂档解析你们怎么做的？
generated: 2026-07-23T15:41:19.800592
---

# 在 RAG 中，索引流程中的⽂档解析你们怎么做的？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

⽂档解析其实是 RAG 系统⾥特别关键的⼀步，搞不定这环，后⾯ embedding 再准也没⽤。我们⼀般不会直接扔原始
⽂件给模型，得先把 PDF、Word、HTML 这些格式拆成⼲净的⽂本块，还得保留必要的结构信息。
1）先⽤通⽤解析⼯具做预处理。⽐如 PDF ⽤ PyMuPDF 或 pdfplumber，能精准提取⽂字和分⻚；Oﬃce ⽂档⽤
Apache Tika，它⽀持格式多，省⼼得多。HTML 就⽤ BeautifulSoup 去掉脚本和⼴告这类噪⾳。
2）接着是分块策略。不能简单按段落切，否则会把上下⽂割裂。我们会结合语义边界，⽐如标题层级变化时强制分
块，同时控制每块在 300~500 token 左右。像 LlamaIndex 或 LangChain 提供的 RecursiveCharacterTextSplitter 就
挺好⽤，能优先按 \n\n 、句号这些符号切分。
3）结构化信息保留也很重要。⽐如从企业⽂档中抽章节标题，打上 section=3.1  这样的元数据，后续检索时能结
合标题过滤，召回准确率能提 20% 以上。
代码上基本⻓这样：
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(
chunk_size=400,
chunk_overlap=50,
separators=["\n\n", "\n", " 。 ", ". "]
)
chunks = splitter.split_text(text)
整个过程其实就是在“保语义”和“控⻓度”之间找平衡，太碎了影响上下⽂理解，太⼤了⼜容易混⼊⽆关内容。