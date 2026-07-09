# Day 05：生产级降级 + 容错设计

> 目标：掌握多层降级路径设计，理解"每层为什么这么设计"——超时时间、默认值、兜底策略。

---

## 一、为什么需要降级？（15min）

```
正常路径: 实时特征(Feast) → XGBoost → 决策

生产中的异常:
  09:00  特征服务 Redis 挂了 → 所有请求 500 → 业务全挂 ❌

有降级:
  09:00  特征服务超时 → 降级到缓存 → 缓存也没有 → 用默认值
  → 决策可能偏保守，但服务没挂 ✓
```

**核心原则：宁可降级不可挂掉。**

---

## 二、三层降级代码精读（1h）

打开 `src/decision_engine/inference_pipeline.py` 第 310-350 行：

```python
async def _fetch_features_with_fallback(self, request):
    t0 = time.perf_counter()

    # ═══════════════════════════════════════════
    # 路径1: 在线特征 — 50ms 超时
    #
    # 为什么是 50ms？
    # 整个推理 P99 < 300ms。特征获取只是其中一环。
    # 50ms = 1/6 预算，留给规则(5ms)+模型(10ms)+序列化(10ms)
    #         +网络(20ms)+余量(205ms)。
    # 设太大(100ms)→ 挤压模型推理时间
    # 设太小(20ms)→ 正常请求也超时 → 频繁降级
    # ═══════════════════════════════════════════
    try:
        snapshot = await asyncio.wait_for(
            self.feature_service.get_online_features(request.user_id),
            timeout=0.050
        )
        return snapshot
    except asyncio.TimeoutError:
        pass  # → 降级

    # ═══════════════════════════════════════════
    # 路径2: 缓存特征 — TTL 5分钟
    #
    # 为什么缓存不是默认路径？
    # 默认走在线（最新数据），在线挂了走缓存（可用但可能过时）。
    # 缓存是"安全网"，不是"主路"。
    # ═══════════════════════════════════════════
    cached = self.feature_service.get_cached_features(request.user_id)
    if cached:
        snapshot = FeatureSnapshot(user_id=request.user_id)
        snapshot.features = cached
        snapshot.degraded_features = list(cached.keys())  # ← 标记降级
        return snapshot

    # ═══════════════════════════════════════════
    # 路径3: 默认值 — 最保守策略
    #
    # 为什么默认值偏保守（偏高风险）？
    # 不知道用户什么样 → 宁可误杀，不可放过
    #
    # night_ops_ratio 默认 0.5: 偏高（正常 0.1-0.3）
    # on_time_rate 默认 0.5: 偏低（正常 0.8-1.0）
    # monthly_income 默认 5000: 中等偏低
    #
    # 为什么不是 0？填 0 意味着"无风险"→ 会放行实际高风险用户
    # 为什么不是极端值？全拒绝会影响业务量
    # ═══════════════════════════════════════════
    snapshot = FeatureSnapshot(user_id=request.user_id)
    snapshot.features = DegradationPolicy.get_all_defaults()
    snapshot.degraded_features = list(snapshot.features.keys())
    return snapshot
```

### 2.1 降级默认值的选择——这是 AI 工程师的决策

打开 `src/decision_engine/degradation.py`：

```python
class DegradationPolicy:
    DEFAULTS = {
        # "越高越危险"的特征 → 默认偏高（保守）
        'night_ops_ratio_30d': 0.5,    # 正常 0.1-0.3
        'overdue_cnt_hist':    1.0,    # 正常 0
        'apply_cnt_7d':        2.0,    # 正常 0-1

        # "越低越危险"的特征 → 默认偏低（保守）
        'on_time_rate':        0.5,    # 正常 0.8-1.0
        'monthly_income':      5000,   # 正常 5000-20000
    }
```

**为什么 `on_time_rate` 默认 0.5 而不是 0 或 1？**

```
0.0 → "绝对坏" → 所有降级请求都被拒 → 业务量骤降
1.0 → "绝对好" → 所有降级请求都被通过 → 放行了高风险用户
0.5 → 中间值 → 评分大约 500 分 → MANUAL_REVIEW → 人工兜底
```

---

## 三、动手练习（1.5h）

### 练习 1：实现三层降级（45min）

```python
import asyncio
import random

# 模拟的特征服务：有时正常、有时慢、有时直接抛异常
class MockFeatureService:
    async def get_online_features(self, user_id):
        delay = random.choice([0.01, 0.02, 0.06, 0.2])  # 最后一个超时
        await asyncio.sleep(delay)
        if random.random() < 0.1:  # 10% 概率直接崩溃
            raise ConnectionError("Redis 挂了")
        return {"f1": 1.0, "f2": 2.0}

    def get_cached_features(self, user_id):
        if random.random() > 0.3:  # 70% 概率命中缓存
            return {"f1": 0.9, "f2": 1.8}
        return None  # 缓存过期

DEFAULTS = {"f1": 0.5, "f2": 0.5}

async def fetch_features_with_fallback(user_id):
    """
    要求实现三层降级，和项目中的代码结构一致:
    1. 在线查询(50ms超时) → 2. 缓存 → 3. 默认值

    关键: 每层降级都要记录 degraded_features
    """
    # TODO: 实现
    pass

# 测试
async def test():
    for i in range(10):
        result = await fetch_features_with_fallback(f"user_{i}")
        print(f"user_{i}: features={result['features']}, "
              f"degraded={result.get('degraded', False)}")

asyncio.run(test())
```

### 练习 2：设计搜索系统的降级路径（30min）

```
搜索系统的四层降级:
  路径1: 语义搜索(深度学习) — 80ms 超时
  路径2: 关键词匹配(ES) — 50ms 超时
  路径3: 热门结果缓存 — 不超时
  路径4: 空结果 + "请优化搜索词"

要求:
  1. 写出每层超时时间的理由
  2. 路径4 返回空结果 → 用户体验很差 → 如何缓解？
```

---

## 四、跨业务思考（30min）

```
语音助手:
  路径1: GPT-4o (2s超时) → 最智能
  路径2: 本地小模型 Whisper+LLaMA (500ms) → 还行
  路径3: 预设回复列表 → "请稍后再试"

自动驾驶:
  路径1: 多传感器融合 → 最优
  路径2: 纯视觉 → 降级
  路径3: 安全停车 → 绝对兜底
  ★ 注意: 自动驾驶不能"降级到默认值继续开"
          降级=停车，不是"保守策略"
```

---

## 五、今天要点

```
降级设计的铁律:
  1. 每层有明确的触发条件（超时/异常）
  2. 默认值的选择直接影响风控/推荐效果 — 这是 AI 工程师的决策
  3. 永远有最后一道防线（纯规则/热门/安全停车）
```

---

## 六、检查清单

- [ ] 完成了三层降级代码（含 degraded_features 标记）
- [ ] 能解释每层超时时间的设定理由
- [ ] 能说清 DegradationPolicy 中每个默认值为什么选这个数
- [ ] 完成了搜索系统降级设计
