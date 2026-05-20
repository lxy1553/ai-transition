# Day 25 - RAG 权限与敏感信息控制

这个项目用于练习 RAG 系统里的权限过滤和敏感信息控制。

它模拟三个安全决策：

- `allow`：用户有权限，内容可以进入上下文和答案；
- `deny`：用户无权限或问题有高风险意图，必须拒绝；
- `mask`：用户有权限，但内容包含手机号、邮箱、密钥等，需要脱敏。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day25_security_controls/main.py
```

## 输入文件

```text
projects/day25_security_controls/policy.json
projects/day25_security_controls/cases.json
```

`policy.json` 保存角色、敏感信息正则和高风险关键词。
`cases.json` 保存固定测试样本，用来检查策略是否误放行或误拒。

## 输出文件

```text
projects/day25_security_controls/output/security_eval_results.json
projects/day25_security_controls/output/security_eval_report.md
```

## 生产映射

真实生产系统里，这个脚本对应 RAG API 调用 LLM 前后的安全检查层。
它通常会接入用户身份、角色权限、数据分级、metadata filter、输出脱敏和审计日志。

安全控制的目标不是让系统少回答，而是确保只有被授权、可追溯、脱敏后的内容才能进入答案。
