from dataclasses import dataclass


@dataclass
class ValueInfo:
    id:str
    value:str   #维度值 --全文索引 text 类型
    column_id:str
    