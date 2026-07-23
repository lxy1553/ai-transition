**FastAPI** 是一个现代、高性能的 Python Web 框架，专门用于构建 API 服务。
它最大的特点是**异步支持、自动交互式文档、以及基于 Python 类型提示的数据校验**，
让你可以用极少的代码写出健壮、快速、且易于维护的接口。
在之前讨论的生产级 AI 应用中，FastAPI 扮演的角色是**推理网关**——将模型、特征、规则引擎等串联成业务可用的 HTTP/gRPC 服务。

---

## 一、FastAPI 的核心特性

### 1. 极致的性能
FastAPI 底层基于 **Starlette**（Web 框架）和 **Pydantic**（数据校验）。
它的异步能力（async/await）使其性能与 Node.js 和 Go 相当，远超传统 Flask/Django。
在信贷风控这种需要 50ms 级低延迟推理的场景中，异步特性可以保证在等待 Redis 特征查询或远程模型调用时，不阻塞其他请求。

### 2. 自动生成交互式文档
只要定义了 Pydantic 模型和路由，FastAPI 就会自动生成 **Swagger UI** 和 **ReDoc** 两份交互式 API 文档。
开发人员、测试人员、甚至业务方都可以直接在网页上测试接口，极大降低沟通成本。

### 3. 基于类型提示的数据校验
通过 Python 的类型注解（Type Hints），FastAPI 可以在请求进来时自动校验参数类型、范围、格式，并将请求体自动解析为 Pydantic 对象。
这不仅减少了手动写校验代码的繁琐，还提供了编辑器自动补全和静态检查。

### 4. 依赖注入系统
FastAPI 内置了强大的依赖注入机制，可以将数据库连接、模型加载、特征服务客户端等公共依赖，以声明式的方式注入到路由函数中，代码解耦且易于测试。

### 5. 原生支持 WebSocket、后台任务、中间件
这使得它可以胜任实时数据推送、异步日志上报等需求。

---

## 二、在 AI/ML 系统中的具体作用

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

## 三、为什么选 FastAPI 而不是 Flask？

| 维度 | FastAPI | Flask |
|------|---------|-------|
| 异步支持 | 原生 async/await，性能高 | 需额外扩展（gevent/asyncio） |
| 数据校验 | 自动基于 Pydantic，类型安全 | 需手动写校验逻辑或插件 |
| API 文档 | 自动生成 Swagger/ReDoc | 需额外安装 flasgger 等 |
| 性能 | 接近 NodeJS/Go | 同步模型下并发能力受限 |
| 生态 | 完美兼容 Starlette 生态，与 Pydantic、SQLAlchemy 无缝集成 | 庞大但逐渐老旧 |

生产级 AI 应用对**低延迟、高并发、严格的输入输出定义**要求很高，FastAPI 在这些方面是当前 Python 生态的最优解。

---

**一句话总结：FastAPI 是现代 Python 构建高性能、类型安全 API 的事实标准，
它在 AI 系统中充当推理网关，通过异步能力、自动校验和文档生成，将模型服务化过程变得极其高效和可靠。**