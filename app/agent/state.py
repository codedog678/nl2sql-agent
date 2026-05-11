from typing  import Any, TypedDict
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo

class ColumnInfoState(TypedDict):
    name:str
    type:str
    role:str
    examples:list[Any]
    description:str
    alias:list[str]

class TableInfoState(TypedDict):
    name:str
    role:str
    derscription:str
    columns:list[ColumnInfoState]

class MetricInfoState(TypedDict):
    name:str
    description:str
    relevant_columns:list[str]
    alias:list[str]

class DataInfoState(TypedDict):
    data:str
    weekday:str
    quarter:str

class DBInfoState(TypedDict):
    dilect:str
    version:str

class DataAgentState(TypedDict):
    error:str  #校验sql的错误信息
    keywords:list[str] #抽取的关键词
    query:str  #查询语句
    retrieved_column_infos:list[ColumnInfo] #检索到的字段信息
    retrieved_metric_infos:list[MetricInfo] #检索到的指标信息
    retrieved_value_infos:list[ValueInfo] #检索到的取值信息
    table_infos:list[TableInfoState]  #表信息 
    metric_infos:list[MetricInfoState]  #指标信息 
    #上下文 data_info and db_info
    date_info:DataInfoState  #日期信息
    db_info:DBInfoState    #数据库信息
    sql:str    #sql语句
    sql_retry_count: int   # 当前已重试次数
    max_retries: int       # 最大重试次数
 
