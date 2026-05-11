from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL


class TableInfoMapper:
    @staticmethod
    def to_model(table_info:TableInfo):   #转化成orm对象
        return TableInfoMySQL(
            id=table_info.id,
            name=table_info.name,
            role=table_info.role,
            description=table_info.description
        )
    
    @staticmethod
    def to_entity(table_info_mysql:TableInfoMySQL): #转化成实体对象
        return TableInfo(
            id=table_info_mysql.id,
            name=table_info_mysql.name,
            role=table_info_mysql.role,
            description=table_info_mysql.description
        )