---
id: Q038
source: mianshiya
category: RAG 检索增强
title: 向量数据库中的 HNSW、LSH、PQ 分别是什么意思？
generated: 2026-07-23T15:41:19.800816
---

# 向量数据库中的 HNSW、LSH、PQ 分别是什么意思？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

HNSW、LSH、PQ 是向量数据库⾥常⽤的 近似最近邻搜索（ANN）技术，⽤来在⾼维空间快速找相似向量，毕竟暴⼒
遍历 O(n) 在亿级数据上根本扛不住。
1）HNSW（Hierarchical Navigable Small World）本质是个多层图结构。每⼀层都是个近邻图，⾼层稀疏⽤
来“跳”得快，底层密集做精细搜索。查询时从顶层开始往下⾛，像导航⼀样逐步逼近⽬标点。Milvus、Weaviate 都
⽤它，召回率⾼，延迟也稳，但建索引内存开销⼤。
2）LSH（Locality-Sensitive Hashing）思路更粗暴：把相似的向量通过特定哈希函数尽可能甩到同⼀个桶⾥。查的时
候只搜对应桶，⼤幅缩⼩范围。优点是实现简单、存储省，但召回率不如 HNSW，尤其分布不均时容易漏。早期
Annoy ⽤过类似思想。
3）PQ（Product Quantization）⼲的是降维压缩的脏活。它把⾼维向量切成⼏段，每段独⽴聚类，⽤聚类中⼼代替
原始向量分量，存个码本就⾏。原来 128 维 ﬂoat 能压到 16 字节内，检索时⽤对称距离近似算相似度。Faiss 就拿它和
IVF 搭配，扛住了⼗亿级向量库。
这仨经常混着⽤，⽐如 Faiss ⾥ IVFPQ 就是先⽤聚类定位候选集，再 PQ 压缩算距。选哪个看场景：要精度选
HNSW，要省资源可以试 LSH + PQ 组合。