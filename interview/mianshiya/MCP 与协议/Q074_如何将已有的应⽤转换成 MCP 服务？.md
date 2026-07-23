---
id: Q074
source: mianshiya
category: MCP 与协议
title: 如何将已有的应⽤转换成 MCP 服务？
generated: 2026-07-23T15:41:19.805405
---

# 如何将已有的应⽤转换成 MCP 服务？

> 来源: 面试鸭题库 | 分类: MCP 与协议

MCP 本质上是⼀套⾯向云原⽣的模块化编程模型，核⼼是把传统应⽤拆解成可独⽴部署、按需加载的 微内核 + 插件 结
构。你不需要重写整个系统，关键是识别出哪些模块具备“可插拔”特征。
⼀般适合改造的模块是那些业务边界清晰、依赖收敛、有明确接⼝定义的部分。⽐如你在⽤ Spring Boot 做⽹关，⾥
⾯的鉴权、限流、⽇志收集这些功能就可以拆成 MCP 插件。它们共⽤⼀套上下⽂，但彼此不耦合。
改造第⼀步是引⼊ MCP 运⾏时容器，⽐如基于 Jigsaw 模块系统或⾃研 ClassLoader 隔离机制。然后把原有功能打成
jar 包，配上 module.json  或注解声明⼊⼝类和依赖关系。启动时容器会按拓扑顺序加载并激活。
代码上最简单的做法是在原项⽬加⼀个启动器：
@McpModule(name = "auth-plugin", version = "1.0")
public class AuthPlugin implements ModuleLifecycle {
public void onStart(Context ctx) {
ctx.registerFilter(new AuthFilter());
}
}
注意类加载器隔离，避免第三⽅库冲突。像 Apollo、Nacos 这类配置中⼼的客户端通常要下沉到宿主，插件通过统⼀
API 获取配置。
常⻅翻⻋点是静态变量共享和线程池滥⽤。不同插件如果都 new ⾃⼰的 ThreadPoolExecutor，很容易把机器打爆。
建议统⼀⽤宿主提供的执⾏器。
这种架构在阿⾥内部的 Sentinel 控制台、Ant Design Pro 后台都有落地，主要是为了⽀撑多租户定制化需求。⼩团队
⽤的话，得评估好复杂度收益⽐，别为了架构⽽架构。