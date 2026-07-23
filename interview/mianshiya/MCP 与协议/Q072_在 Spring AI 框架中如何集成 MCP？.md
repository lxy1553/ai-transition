---
id: Q072
source: mianshiya
category: MCP 与协议
title: 在 Spring AI 框架中如何集成 MCP？
generated: 2026-07-23T15:41:19.805188
---

# 在 Spring AI 框架中如何集成 MCP？

> 来源: 面试鸭题库 | 分类: MCP 与协议

Spring AI 框架本⾝是 Spring ⽣态中⽤于接⼊⼤模型服务的抽象层，它的设计⽬标是让 Java 应⽤能统⼀⽅式调⽤不同
AI 平台的能⼒。MCP（Model Context Protocol）是⼀种⽤于在客户端与模型服务之间传递上下⽂信息的协议，常⻅
于某些私有化部署或定制化推理平台。
要把 MCP 集成进 Spring AI，关键在于⾃定义客户端适配器。Spring AI ⽀持扩展 ChatClient  接⼝，你可以基于
RestClient  或 WebClient  实现⼀个专⽤于与⽀持 MCP 协议的服务通信的客户端。
1）你需要先定义请求结构体，匹配 MCP 规范⾥的字段，⽐如 context , prompt , model  等。 2）通过
@RegisterAiClient  注解注册你的实现，或者⼿动配置为 Bean 。 3）在调⽤时注⼊ ChatClient ，框架会⾃
动路由到你的 MCP 适配器。
@Bean
ChatClient mcpChatClient(WebClient webClient) {
return ChatClient.builder()
.baseUrl("https://mcp-gateway.example.com")
.webClient(webClient)
.build();
}
实际请求中，header 或 payload ⾥要带上 MCP 要求的元数据，⽐如会话 ID、租户上下⽂等。这类脏活累活⼀般封装
在拦截器⾥处理。
如果使⽤ Spring AI 0.8.0+ 版本，已经⽀持 SPI 扩展机制，可以更⼲净地插拔协议实现。不过⽬前主流⼚商如通义千
问、百川都不⾛ MCP，它更多出现在内部统⼀推理⽹关场景，⽐如阿⾥云灵积的部分私有实例。