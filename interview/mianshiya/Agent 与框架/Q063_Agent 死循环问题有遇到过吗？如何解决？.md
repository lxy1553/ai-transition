---
id: Q063
source: mianshiya
category: Agent 与框架
title: Agent 死循环问题有遇到过吗？如何解决？
generated: 2026-07-23T15:41:19.803991
---

# Agent 死循环问题有遇到过吗？如何解决？

> 来源: 面试鸭题库 | 分类: Agent 与框架

Agent 死循环通常发⽣在字节码增强逻辑⾥，⽐如⽤ Java Agent 做监控或 APM 时，不⼩⼼把⾃⼰ instrument 的类⼜
触发了新的 transform，结果⽆限加载 class，CPU 直接打满。
最常⻅的场景是，你在 ClassFileTransformer  ⾥处理某个类的时候，执⾏了某些代码，这些代码⼜动态⽣成类
或者触发类加载，⽽你的 transformer 没做过滤，就会重新进⼊ transform ⽅法，形成递归调⽤。特别是⽤到 ASM、
CGLIB、Javassist 这些框架时很容易中招。
解决办法其实就两条：
1）加 类名过滤，直接排除不必要的类，尤其是你 agent ⾃⾝的包路径，⽐如 com.mycompany.agent.**  全部
return null 不做处理。
2）⽤ 本地线程标记（ThreadLocal）标记当前是否已经在 transform 流程中，如果是，直接跳过。这个特别关键，因
为很多间接类加载是你控制不了的。
static final ThreadLocal<Boolean> transforming = new ThreadLocal<>();
public byte[] transform(ClassLoader loader, String className, Class<?>
classBeingRedefined,
ProtectionDomain protectionDomain, byte[] classfileBuffer) {
if (transforming.get() != null) return null;
try {
transforming.set(true);
// 执⾏实际的字节码修改逻辑
return doTransform(loader, className, classfileBuffer);
} finally {
transforming.remove();
}
}
另外，像 SkyWalking、Pinpoint 这些 APM ⼯具都遇到过这类问题，它们的源码⾥都有对应的 guard 机制防⽌重⼊。
参考它们的实现能少踩很多坑。

> 注：原 PDF 此处混入了 Java Agent 与 LLM Agent 两种答案；LLM Agent 死循环应强调 max_steps、循环检测、工具失败回退与人机介入。

---