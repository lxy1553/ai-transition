"""
Schema Registry — 数据仓库表结构注册中心

职责:
  1. 从 config/schemas/*.yaml 加载表结构定义
  2. 在数据写入时将 _TABLE_SCHEMA.json 写入数据目录
  3. 在数据读取时校验 schema 兼容性
  4. 提供表结构的查询接口（供文档生成、数据探索）

使用方式:
    registry = SchemaRegistry()
    schema = registry.get_table("ods", "ods_application")
    # schema.columns → 列定义列表
    # schema.ddl → 对应的 SQL DDL 文本
    registry.write_schema_to_data_dir("data/warehouse/ods/dt=2026-07-01", "ods_application")
"""

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ColumnDef:
    """列定义"""
    name: str
    type: str
    nullable: bool = True
    description: str = ""
    pii: bool = False
    sensitivity: Optional[str] = None
    aggregation: Optional[str] = None
    risk_direction: Optional[str] = None


@dataclass
class TableSchema:
    """表结构定义"""
    table_name: str
    layer: str           # ods / dwd / dws / ads
    description: str = ""
    columns: list[ColumnDef] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    partition_key: str = "dt"
    source_table: Optional[str] = None
    grain: Optional[str] = None
    ddl: str = ""        # 对应的 SQL DDL

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def pii_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.pii]

    def to_dict(self) -> dict:
        return {
            "table_name": self.table_name,
            "layer": self.layer,
            "description": self.description,
            "primary_key": self.primary_key,
            "partition_key": self.partition_key,
            "source_table": self.source_table,
            "grain": self.grain,
            "columns": [
                {
                    "name": c.name,
                    "type": c.type,
                    "nullable": c.nullable,
                    "description": c.description,
                    "pii": c.pii,
                    "sensitivity": c.sensitivity,
                    "aggregation": c.aggregation,
                }
                for c in self.columns
            ],
        }

    def print_ddl(self) -> str:
        """格式化打印 DDL"""
        if self.ddl:
            return self.ddl
        return self._generate_ddl()

    def _generate_ddl(self) -> str:
        """从列定义生成 DDL"""
        lines = [f"-- Table: {self.layer}.{self.table_name}",
                 f"-- Description: {self.description}",
                 f"-- Grain: {self.grain or 'N/A'}",
                 f"CREATE TABLE IF NOT EXISTS {self.layer}.{self.table_name} ("]
        for c in self.columns:
            nullable = "" if c.nullable else " NOT NULL"
            desc = f" -- {c.description}" if c.description else ""
            lines.append(f"    {c.name:25s} {c.type}{nullable},{desc}")
        lines.append(f")")
        if self.partition_key:
            lines.append(f"PARTITIONED BY ({self.partition_key})")
        lines.append("STORED AS parquet;")
        return "\n".join(lines)


class SchemaRegistry:
    """
    表结构注册中心。

    加载 config/schemas/*.yaml 和 config/ddl/*.sql，
    提供统一的表结构查询和写入接口。
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.schemas_dir = self.config_dir / "schemas"
        self.ddl_dir = self.config_dir / "ddl"
        self._tables: dict[str, TableSchema] = {}  # key: "layer.table_name"
        self._load_all()

    # ── 加载 ──────────────────────────────────────────

    def _load_all(self):
        """加载所有 schema 定义和 DDL"""
        self._load_ods()
        self._load_dwd()
        self._load_dws()
        self._load_ads()
        self._load_ddls()
        print(f"[SchemaRegistry] 已加载 {len(self._tables)} 张表结构")

    def _load_ods(self):
        """加载 ODS 层 schema"""
        path = self.schemas_dir / "ods_tables.yaml"
        if not path.exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for table_name, table_def in data.get('tables', {}).items():
            columns = []
            for col in table_def.get('columns', []):
                columns.append(ColumnDef(**{
                    k: v for k, v in col.items()
                    if k in ('name', 'type', 'nullable', 'description', 'pii', 'sensitivity')
                }))
            self._register(TableSchema(
                table_name=table_name,
                layer="ods",
                description=table_def.get('description', ''),
                columns=columns,
                partition_key=table_def.get('partition_key', 'dt'),
                source_table=table_def.get('source_system', ''),
            ))

    def _load_dwd(self):
        """加载 DWD 层 schema"""
        path = self.schemas_dir / "dwd_tables.yaml"
        if not path.exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for table_name, table_def in data.get('tables', {}).items():
            columns = []
            for col in table_def.get('columns', []):
                columns.append(ColumnDef(**{
                    k: v for k, v in col.items()
                    if k in ('name', 'type', 'nullable', 'description')
                }))
            self._register(TableSchema(
                table_name=table_name,
                layer="dwd",
                description=table_def.get('description', ''),
                columns=columns,
                partition_key='dt',
                source_table=table_def.get('source_table', ''),
            ))

    def _load_dws(self):
        """加载 DWS 层 schema（宽表）"""
        path = self.schemas_dir / "dws_wide_table.yaml"
        if not path.exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        wt = data.get('wide_table', {})

        columns = []
        for cat_key in ['category_profile', 'category_behavior', 'category_repayment']:
            cat = wt.get(cat_key, {})
            for feat in cat.get('features', []):
                columns.append(ColumnDef(
                    name=feat['name'],
                    type=feat.get('type', 'STRING'),
                    nullable=feat.get('nullable', True),
                    description=feat.get('description', ''),
                    aggregation=feat.get('aggregation', ''),
                    risk_direction=feat.get('risk_direction', ''),
                ))

        # 分区列
        for p in wt.get('partition', []):
            columns.append(ColumnDef(
                name=p['name'], type=p['type'],
                nullable=p.get('nullable', False),
                description=p.get('description', ''),
            ))

        self._register(TableSchema(
            table_name=wt.get('table_name', 'user_risk_feature_wide'),
            layer="dws",
            description=wt.get('description', ''),
            columns=columns,
            primary_key=wt.get('primary_key', []),
            partition_key=wt.get('partition_key', 'dt'),
            grain=wt.get('grain', ''),
        ))

    def _load_ads(self):
        """加载 ADS 层 schema"""
        path = self.schemas_dir / "ads_tables.yaml"
        if not path.exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for table_name, table_def in data.get('tables', {}).items():
            columns = []
            for col in table_def.get('columns', []):
                columns.append(ColumnDef(**{
                    k: v for k, v in col.items()
                    if k in ('name', 'type', 'nullable', 'description')
                }))
            self._register(TableSchema(
                table_name=table_name,
                layer="ads",
                description=table_def.get('description', ''),
                columns=columns,
                partition_key='dt',
            ))

    def _load_ddls(self):
        """加载 SQL DDL 文件，关联到对应表"""
        ddl_files = sorted(self.ddl_dir.glob("*.sql")) if self.ddl_dir.exists() else []
        for ddl_path in ddl_files:
            ddl_text = ddl_path.read_text(encoding='utf-8')
            # 从 DDL 中提取表名，关联到已注册的 table
            for line in ddl_text.split('\n'):
                if 'CREATE TABLE' in line.upper():
                    # 解析 "ods.ods_application" 格式
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p.upper() == 'TABLE' and i + 2 < len(parts):
                            full_name = parts[i + 2]  # ods.ods_application
                            if '.' in full_name:
                                layer, name = full_name.split('.', 1)
                                key = f"{layer}.{name}"
                                if key in self._tables:
                                    self._tables[key].ddl = ddl_text
                            break

    def _register(self, schema: TableSchema):
        """注册一张表"""
        key = f"{schema.layer}.{schema.table_name}"
        self._tables[key] = schema

    # ── 查询 ──────────────────────────────────────────

    def get_table(self, layer: str, table_name: str) -> Optional[TableSchema]:
        """按层和表名查询"""
        return self._tables.get(f"{layer}.{table_name}")

    def list_tables(self, layer: Optional[str] = None) -> list[TableSchema]:
        """列出所有表，可按层筛选"""
        tables = list(self._tables.values())
        if layer:
            tables = [t for t in tables if t.layer == layer]
        return tables

    def get_wide_table(self) -> Optional[TableSchema]:
        """获取宽表结构"""
        return self._tables.get("dws.user_risk_feature_wide")

    # ── 写入数据目录 ──────────────────────────────────

    def write_schema_to_data_dir(self, data_dir: str, table_name: str,
                                  layer: str = "ods") -> Path:
        """
        将表结构写入数据目录的 _TABLE_SCHEMA.json 文件。
        这样每个数据目录下都自带表结构定义，可以独立被外部工具读取。

        Args:
            data_dir: 数据分区目录，如 "data/warehouse/ods/dt=2026-07-01"
            table_name: 表名

        Returns:
            写入的文件路径
        """
        key = f"{layer}.{table_name}"
        schema = self._tables.get(key)
        if schema is None:
            raise ValueError(f"未找到表结构: {key}。已注册: {list(self._tables.keys())}")

        out_dir = Path(data_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        schema_file = out_dir / f"_TABLE_SCHEMA_{table_name}.json"

        schema_dict = schema.to_dict()
        schema_dict["_generated_by"] = "SchemaRegistry"
        schema_dict["_schema_version"] = "1.0"

        with open(schema_file, 'w', encoding='utf-8') as f:
            json.dump(schema_dict, f, indent=2, ensure_ascii=False)

        return schema_file

    def write_layer_schemas(self, warehouse_dir: str = "data/warehouse") -> dict[str, Path]:
        """
        为每层数据目录写入 _TABLE_SCHEMA.json。
        每个表一个文件，写入该层根目录（schema 对所有分区相同）。

        Args:
            warehouse_dir: 数据仓库根目录

        Returns:
            {表名: schema文件路径}
        """
        written = {}
        base = Path(warehouse_dir)

        layer_tables = {
            "ods": ["ods_application", "ods_user_behavior", "ods_repayment"],
            "dwd": ["dwd_application", "dwd_user_behavior", "dwd_repayment"],
            "dws": ["user_risk_feature_wide"],
            "ads": ["ads_training_samples", "ads_model_monitor_daily", "ads_portfolio_analysis"],
        }

        for layer, tables in layer_tables.items():
            layer_dir = base / layer
            if not layer_dir.exists():
                continue

            for table in tables:
                try:
                    path = self.write_schema_to_data_dir(
                        str(layer_dir), table, layer
                    )
                    written[f"{layer}.{table}"] = path
                except ValueError:
                    continue

        return written

    # ── 汇总 ─────────────────────────────────────────

    def print_summary(self) -> str:
        """打印所有表结构概览"""
        lines = ["\n" + "=" * 70,
                 "  数据仓库表结构注册中心",
                 "=" * 70]
        for layer in ["ods", "dwd", "dws", "ads"]:
            tables = self.list_tables(layer)
            if not tables:
                continue
            lines.append(f"\n  [{layer.upper()} 层] {len(tables)} 张表")
            for t in tables:
                lines.append(f"    {t.table_name:35s} "
                           f"{len(t.columns):2d}列  "
                           f"PK={t.primary_key or '(无)'}")
        lines.append(f"\n  总计: {len(self._tables)} 张表")
        lines.append("=" * 70)
        return "\n".join(lines)
