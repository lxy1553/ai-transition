---
id: 附-05
source: mianshiya
category: 未分类
title: 假设需要让大模型生成一个React表单组件代码，请设计一个包含上下文约束的Prompt（需包含数据验证、错误提示等要求）
generated: 2026-07-23T15:41:19.807541
---

# 假设需要让大模型生成一个React表单组件代码，请设计一个包含上下文约束的Prompt（需包含数据验证、错误提示等要求）

> 来源: 面试鸭题库 | 分类: 未分类

据验证、错误提⽰等要求）
你让⼤模型写 React 表单，光说“写个表单”它肯定给你个最简单的 input 加按钮。要拿到能落地的代码，得把约束
条件⼀次性给全。
关键是在 Prompt ⾥明确结构、⾏为和边界。⽐如你要⼀个⽤户注册表单，就得指定字段、验证规则、错误提⽰⽅
式、提交逻辑。
可以这样组织上下⽂：
1）表单包含⽤户名、邮箱、密码、确认密码四个字段
2）所有字段必填，⽤户名⾄少 3 字符，邮箱格式校验，密码需 8 位以上且含⼤⼩写和数字
3）实时校验：输⼊时显⽰错误信息，不满⾜规则时禁⽤提交按钮
4）错误提⽰使⽤ React Hook Form  的 errors  对象驱动，配合 Zod  做 schema 校验
5）样式⽤ className  预留，不依赖具体 UI 库
代码⽰例核⼼结构：
const schema = z.object({
username: z.string().min(3),
email: z.string().email(),
password: z.string().min(8).regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/),
confirmPassword: z.string()
}).refine(data => data.password === data.confirmPassword, {
message: "Passwords don't match",
path: ["confirmPassword"]
});
搭配 useForm  和 zodResolver ，把 register  绑到输⼊框，errors  渲染提⽰，按钮根据
formState.isValid  控制是否可点。
这种 Prompt 能让模型输出接近⽣产环境的代码，⽽不是玩具⽰例。你给的约束越贴近实际项⽬，⽣成结果越能直接
⽤。