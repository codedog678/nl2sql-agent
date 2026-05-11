from dataclasses import dataclass
from typing import Optional

@dataclass
class ColumnConfig:
    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool

@dataclass
class TableConfig:
    name: str
    role: str
    description: str
    columns: list[ColumnConfig]

@dataclass
class MetricConfig:
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]

@dataclass
class MetaConfig: #将来可能只用其中一个 所以使用optional可选的 可能有可能没有
    tables: Optional[list[TableConfig]] = None
    metrics: Optional[list[MetricConfig]] = None