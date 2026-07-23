# 金融信贷风控 AI 应用系统

> 生产级互联网小贷/消费金融自动化信贷审批与贷后监控系统

## 项目概述

本项目是一个完整的信贷风控系统参考实现，涵盖：
- **贷前审批**：实时授信决策（规则引擎 + XGBoost/评分卡）
- **贷中管理**：额度调整策略
- **贷后监控**：逾期预警与模型闭环迭代

## 系统架构

```
数据源 → Kafka/Flink → 特征平台(Feast) → 推理引擎(FastAPI) → 决策输出
                                ↑
 MLflow模型注册 ← 离线训练(Spark/XGBoost) ← 贷后标签回传
```

## 项目结构

```
credit_risk_control_system/
├── config/
│   ├── rules/credit_policy.yaml      # 规则引擎决策表
│   ├── features/feature_defs.yaml    # 特征定义
│   └── settings.yaml                 # 系统配置
├── src/
│   ├── decision_engine/              # 推理引擎核心
│   │   ├── rule_engine.py            # 规则引擎（AST安全求值）
│   │   ├── inference_pipeline.py     # 推理流水线
│   │   ├── ab_router.py             # A/B测试流量路由
│   │   └── degradation.py           # 降级策略
│   ├── feature_store/                # 特征平台
│   │   ├── registry.py              # 特征注册中心
│   │   ├── online_store.py          # 在线特征存储(Redis模拟)
│   │   ├── offline_store.py         # 离线特征存储(Iceberg模拟)
│   │   └── pit_join.py             # Point-in-Time Join
│   ├── models/                       # 模型训练与评估
│   │   ├── trainer.py               # XGBoost/LightGBM训练器
│   │   ├── evaluator.py             # KS/AUC/Gini/PSI/Lift评估
│   │   ├── woe_iv.py                # WOE/IV特征筛选
│   │   ├── scorecard.py             # 评分卡映射
│   │   └── shap_explainer.py        # SHAP可解释性
│   ├── monitoring/                   # 监控告警
│   │   ├── psi_monitor.py           # 特征PSI漂移监控
│   │   ├── circuit_breaker.py       # 模型熔断器
│   │   └── metrics.py               # Prometheus指标
│   ├── services/                     # 外部服务适配
│   │   ├── api_gateway.py           # FastAPI推理网关
│   │   ├── credit_report_service.py # 征信报告服务(模拟)
│   │   ├── device_fingerprint.py    # 设备指纹服务(模拟)
│   │   └── multi_head_service.py    # 多头借贷服务(模拟)
│   └── data/                         # 数据层
│       ├── kafka_client.py          # Kafka客户端(模拟)
│       ├── mock_data_generator.py   # 模拟数据生成
│       └── sample_builder.py        # 训练样本构建
├── tests/                            # 测试用例
├── scripts/                          # 运行脚本
│   ├── train_model.py               # 模型训练脚本
│   ├── run_inference.py             # 推理演示
│   └── run_monitoring.py            # 监控演示
└── docker/
    └── docker-compose.yml           # 本地开发环境
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成模拟数据
python scripts/generate_mock_data.py

# 3. 训练模型
python scripts/train_model.py

# 4. 启动推理服务
python scripts/run_inference.py

# 5. 运行监控
python scripts/run_monitoring.py

# 6. 运行测试
pytest tests/ -v
```

## 核心技术栈

| 组件    | 技术             | 说明                           |
|--------|-----------------|------------------------------|
| 规则引擎  | 自研(AST求值)      | YAML决策表 + Python安全表达式        |
| 模型    | XGBoost / 评分卡  | 传统ML，满足监管可解释性                |
| 特征平台  | Feast-like     | Point-in-Time Join，在线/离线一致   |
| 推理网关  | FastAPI        | 异步高性能，P99 < 300ms            |
| 监控    | Prometheus     | 系统+业务双维度监控                   |
| 消息队列  | Kafka (模拟)     | 异步日志 + 事件驱动                  |
