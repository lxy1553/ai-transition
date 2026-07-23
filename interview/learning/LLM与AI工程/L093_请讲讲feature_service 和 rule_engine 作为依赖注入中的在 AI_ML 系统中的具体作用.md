---
id: L093
source: learning
category: LLM与AI工程
title: 请讲讲feature_service 和 rule_engine 作为依赖注入中的在 AI/ML 系统中的具体作用
generated: 2026-07-23T15:41:19.871645
---

# 请讲讲feature_service 和 rule_engine 作为依赖注入中的在 AI/ML 系统中的具体作用

> 来源: 学习复习计划 | 分类: LLM与AI工程

结合我们之前的信贷风控架构，FastAPI 被用来构建**模型推理服务**和**决策网关**：

### 1. 模型推理 API
它将训练好的模型（评分卡、XGBoost、PyTorch）封装为 RESTful 接口：

```python
from fastapi import FastAPI
from pydantic import BaseModel
import joblib

app = FastAPI()
model = joblib.load("scorecard.pkl")

class LoanRequest(BaseModel):
    age: int
    income: float
    credit_score: int
    # ... 其它特征字段

@app.post("/predict")
async def predict(request: LoanRequest):
    features = [[request.age, request.income, request.credit_score]]
    score = model.predict(features)[0]
    return {"score": float(score), "decision": "PASS" if score > 600 else "REJECT"}

```
当上游业务系统发起 HTTP 请求时，FastAPI 自动校验字段类型、缺失值，省去大量手工判断。

### 2. 集成特征获取与规则引擎
实际生产推理往往需要先获取在线特征，再过黑名单，然后调用模型。这些逻辑可以通过 FastAPI 的依赖注入优雅组织：

```python
from fastapi import Depends
# feature_service 和 rule_engine 作为依赖注入
@app.post("/credit/apply")
async def apply(
    req: ApplyRequest,
    features = Depends(feature_service),
    rules = Depends(rule_engine)
):
    # 1. 黑名单检查
    if rules.check_blacklist(req.user_id):
        return {"decision": "REJECT", "reason": "命中黑名单"}
    # 2. 获取特征并打分
    feats = await features.get_online(req.user_id)
    score = model.predict(feats)
    # 3. 返回决策
    ...

```

### 3. 高性能异步处理
在线推理时，服务往往要并发请求多个服务（如 Redis 查用户画像、HTTP 调三方征信），
使用 `async/await` 可以让这些 I/O 操作并发执行，大幅降低单次请求的总耗时。

### 4. 接口文档与团队协作
信贷风控涉及数据、算法、后端、产品等多个角色。
FastAPI 自动生成的文档就是一份“活的接口规范”，所有人都能直观看到需要传哪些参数、参数含义、返回格式，且可以在文档页直接调试。

---