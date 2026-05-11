# app/conf/app_config.py
import os

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from omegaconf import OmegaConf

# 日志配置
@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str

@dataclass
class Console:
    enable: bool
    level: str

@dataclass
class LoggingConfig:
    file: File
    console: Console

# 数据库配置
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int

@dataclass
class EmbeddingConfig:
    base_url: str  # 替换 host
    api_key: str   # 替换 port
    model: str

@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str

@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str

@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm_coder: LLMConfig
    llm_text: LLMConfig

# 配置文件加载逻辑
# 注意：__file__ 所在的目录是 app/conf/，parents[2] 会定位到项目根目录 [cite: 203]
config_file = Path(__file__).parents[2] / 'conf' / 'app_config.yaml'
context = OmegaConf.load(config_file)
schema = OmegaConf.structured(AppConfig)
merged = OmegaConf.merge(schema, context)

_env_mappings = {
    "db_meta.password": "DB_META_PASSWORD",
    "db_dw.password": "DB_DW_PASSWORD",
    "embedding.api_key": "EMBEDDING_API_KEY",
    "llm_coder.api_key": "LLM_CODER_API_KEY",
    "llm_text.api_key": "LLM_TEXT_API_KEY",
}

for dotpath, env_var in _env_mappings.items():
    env_val = os.environ.get(env_var)
    if env_val:
        OmegaConf.update(merged, dotpath, env_val)

app_config: AppConfig = OmegaConf.to_object(merged)
