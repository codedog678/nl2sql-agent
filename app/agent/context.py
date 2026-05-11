# from typing import TypedDict

# from langchain_openai import OpenAIEmbeddings

# from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository

# class DataAgentContext(TypedDict):
#     column_qdrant_repository: ColumnQdrantRepository
#     embedding_client: OpenAIEmbeddings

# app/agent/context.py
from typing import TypedDict
from langchain_community.embeddings import DashScopeEmbeddings # 替换导入
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository

class DataAgentContext(TypedDict):
    column_qdrant_repository: ColumnQdrantRepository
    embedding_client: DashScopeEmbeddings # 修改这里
    metric_qdrant_repository: MetricQdrantRepository 
    value_es_repository: ValueEsRepository
    meta_mysql_repository: MetaMySQLRepository
    dw_mysql_repository: DWMySQLRepository