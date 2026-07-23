---
id: Q068
source: mianshiya
category: MCP 与协议
title: 什么是 MCP 协议，它在 AI ⼤模型系统中的作⽤是什么？
generated: 2026-07-23T15:41:19.804717
---

# 什么是 MCP 协议，它在 AI ⼤模型系统中的作⽤是什么？

> 来源: 面试鸭题库 | 分类: MCP 与协议

MCP 协议并不是⼀个在 AI ⼤模型领域⼴泛通⽤的标准协议，⽬前也没有权威⽂献或主流框架将其定义为类似 HTTP、
gRPC 那样的基础通信协议。它更可能是指特定⼚商或系统内部定义的 模型控制平⾯（Model Control Plane） 协
议，⽤于协调⼤模型服务中的调度、分发与⽣命周期管理。
在典型的推理服务平台⽐如阿⾥云百炼、vLLM 或 Triton Inference Server 中，这类“控制协议”主要⼲三件事：
1）接收推理请求并做路由决策，⽐如该发给哪个模型实例、是否需要扩缩容
2）管理模型加载、卸载、版本切换，确保 GPU 资源⾼效利⽤
3）收集监控指标，配合实现弹性伸缩和故障转移
你可以把它理解成 K8s ⾥的 kubelet 和 API Server 之间的通信逻辑，只不过⾯向的是模型实例⽽不是容器。真正的请
求处理⸺也就是数据平⾯（Data Plane）⸺还是靠 gRPC 或 REST 承载实际的 token 流量，⽽ MCP 这类控制指令通
常⾛独⽴通道，频率低但关键性⾼。
// 伪代码⽰意：控制平⾯接收加载模型指令
void onReceiveLoadModel(String modelId, String version) {
ModelInstance instance = createOrReuseInstance(modelId);
instance.loadFromStorage(); // 可能涉及  mmap 、量化加载等优化
registerToRouter(instance); // 注册到流量路由器
}
要不要⽤这类协议，取决于系统规模。⼩场景直接 API 调⽤就够了，上了百个模型实例后，就得靠统⼀控制平⾯
来“扛住”运维复杂度了。