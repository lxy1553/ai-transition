"""
数据仓库分层模块 — ODS → DWD → DWS → ADS

生产环境技术栈:
  实时链路: Kafka → Flink SQL → ClickHouse/Doris
  离线链路: Spark SQL → Iceberg/Hive (Parquet on S3)

每层的职责和时效:
  ODS (原始数据层) : 1:1 镜像业务系统数据，不做清洗，保留原始粒度
  DWD (明细数据层) : 清洗/标准化/脱敏，仍保留明细粒度
  DWS (汇总数据层) : 按主题聚合，构建用户风险特征宽表 (★核心)
  ADS (应用数据层) : 直接服务上层应用（模型训练样本、BI报表、监控指标）

本模块用 Python 类模拟每层的 ETL 逻辑，数据存储在本地 Parquet。
生产环境替换为 Spark SQL + Iceberg，逻辑完全一致。
"""

from src.data.warehouse.ods_layer import ODSLayer
from src.data.warehouse.dwd_layer import DWDLayer
from src.data.warehouse.dws_layer import DWSLayer
from src.data.warehouse.ads_layer import ADSLayer

__all__ = ["ODSLayer", "DWDLayer", "DWSLayer", "ADSLayer"]
