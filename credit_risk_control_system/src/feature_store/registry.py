"""
特征注册中心 — 管理所有特征的定义、元数据和血缘

PRODUCTION 对比:
- 本实现: YAML + 内存加载（适合学习/小团队）
- 生产环境: Feast Feature Registry（支持版本管理、Schema演进、多团队协作）
- 大规模: 可加 DataHub/Amundsen 做特征发现和血缘可视化

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

import yaml


@dataclass
class FeatureDefinition:
    """单条特征的定义"""
    name: str
    type: str                    # int, float, category, bool
    category: str                # basic_profile, behavior, credit_derived, multi_head, device, fraud
    source: str                  # 数据来源: user_application, flink_realtime, credit_report_service...
    description: str = ""
    owner: str = ""
    derivation: str = ""         # 衍生逻辑（如 pd.cut 分箱）
    values: list = field(default_factory=list)    # 离散特征的取值列表
    range: list[float] = field(default_factory=list)  # 连续特征的值域
    null_fill_strategy: str = ""  # 空值填充策略
    online_store_key: str = ""    # Redis key 模板
    ttl_seconds: int = 604800     # 在线特征有效期
    psi_threshold: float = 0.1    # PSI 告警阈值
    tags: list[str] = field(default_factory=list)
    lineage: dict = field(default_factory=dict)   # 血缘: 上游表/字段 → 下游模型


class FeatureRegistry:
    """
    特征注册中心。

    职责:
    1. 加载和管理所有特征定义
    2. 提供特征查询（按名称、按分类、按数据源）
    3. 特征血缘追踪
    4. 为在线/离线存储提供特征列表

    使用方式:
        registry = FeatureRegistry("config/features/feature_defs.yaml")
        feat = registry.get("debt_to_income_ratio")
        risk_features = registry.get_by_category("credit_derived")
    """

    def __init__(self, config_path: Union[str, Path, None] = None):
        self._features: dict[str, FeatureDefinition] = {}
        self._by_category: dict[str, list[FeatureDefinition]] = {}
        self._by_source: dict[str, list[FeatureDefinition]] = {}

        if config_path:
            self._load(Path(config_path))

    def _load(self, config_path: Path) -> None:
        """从 YAML 加载特征定义"""
        config = yaml.safe_load(config_path.read_text(encoding='utf-8'))

        for feat_dict in config.get('features', []):
            feat = FeatureDefinition(
                name=feat_dict['name'],
                type=feat_dict.get('type', 'float'),
                category=feat_dict.get('category', 'unknown'),
                source=feat_dict.get('source', 'unknown'),
                description=feat_dict.get('description', ''),
                owner=feat_dict.get('owner', ''),
                derivation=feat_dict.get('derivation', ''),
                values=feat_dict.get('values', []),
                range=feat_dict.get('range', []),
                null_fill_strategy=feat_dict.get('null_fill_strategy', ''),
                online_store_key=feat_dict.get('online_store_key', ''),
                ttl_seconds=feat_dict.get('ttl_seconds', 604800),
                psi_threshold=feat_dict.get('psi_threshold', 0.1),
                tags=feat_dict.get('tags', []),
            )

            self._features[feat.name] = feat

            # 建立索引
            cat = feat.category
            self._by_category.setdefault(cat, []).append(feat)
            src = feat.source
            self._by_source.setdefault(src, []).append(feat)

    def get(self, name: str) -> Optional[FeatureDefinition]:
        """按名称查询特征定义"""
        return self._features.get(name)

    def get_all(self) -> dict[str, FeatureDefinition]:
        """获取全部特征定义"""
        return self._features

    def get_by_category(self, category: str) -> list[FeatureDefinition]:
        """按分类查询特征"""
        return self._by_category.get(category, [])

    def get_by_source(self, source: str) -> list[FeatureDefinition]:
        """按数据源查询特征"""
        return self._by_source.get(source, [])

    @property
    def feature_names(self) -> list[str]:
        """所有特征名称列表（供模型推理使用）"""
        return list(self._features.keys())

    @property
    def feature_count(self) -> int:
        return len(self._features)

    def get_categories(self) -> dict[str, int]:
        """各分类的特征数量统计"""
        return {k: len(v) for k, v in self._by_category.items()}

    def add_lineage(self, feature_name: str, upstream: dict) -> None:
        """添加特征血缘信息"""
        if feature_name in self._features:
            self._features[feature_name].lineage = upstream

    def get_lineage(self, feature_name: str) -> dict:
        """查询特征血缘（上游表 → 该特征 → 下游模型）"""
        feat = self._features.get(feature_name)
        if feat:
            return feat.lineage
        return {}

    def to_dataframe(self):
        """导出为 Pandas DataFrame（用于分析和文档）"""
        import pandas as pd
        return pd.DataFrame([
            {
                'name': f.name,
                'type': f.type,
                'category': f.category,
                'source': f.source,
                'owner': f.owner,
                'null_strategy': f.null_fill_strategy,
                'psi_threshold': f.psi_threshold,
            }
            for f in self._features.values()
        ])
