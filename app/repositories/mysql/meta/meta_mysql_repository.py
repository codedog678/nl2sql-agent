from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper

class MetaMySQLRepository:
    def __init__(self, session:AsyncSession):
        self.session = session

    # def save_table_infos(self,table_infos:list):
    #     self.session.add_all(table_infos) #列表内容批量写入
    # #不能加await 因为add_all只是把对象添加到session中 还没有真正写入数据库 
    # #只有commit的时候才会真正写入数据库 而commit是由外部调用的 所以在这里不能加await
    # #现在只是把数据写在本地的session对象中 并没有实际的网络io 这里是同步的 不需要异步
    # #在service层调用repository的方法时 调用session.commit() 那个地方异步了 
    # # 但是在repository层不需要异步 因为repository层只是把数据添加到session中 并没有实际的网络io 只有commit的时候才会真正写入数据库 那个时候才需要异步

    # def save_column_infos(self,column_infos:list):
    #     self.session.add_all(column_infos) #列表内容批量写入

    #因为业务类与orm类对象分离 所以在repository层需要把业务类对象转换成orm类对象 然后再添加到session中 
    #这样就需要在repository层写一个转换的方法 这个方法的作用就是把业务类对象转换成orm类对象
    #这样就可以在service层调用repository的方法时 直接传入业务类对象 就可以了 不需要在service层进行转换了
    #因为session接受的对象必须是orm类对象 但是业务不能过于依赖orm类对象 这样就违背了分层的原则 业务层应该只依赖于实体类对象
    def save_table_infos(self,table_infos:list[TableInfo]):
        self.session.add_all([TableInfoMapper.to_model(table_info) for table_info in table_infos] ) #列表内容批量写入
   

    def save_column_infos(self,column_infos:list[ColumnInfo]):
        self.session.add_all([ColumnInfoMapper.to_model(column_info) for column_info in column_infos]) #列表内容批量写入

    def save_metric_infos(self,metric_infos:list[MetricInfo]):
        self.session.add_all([MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos]) #列表内容批量写入  类型转换

    def save_column_metric(self,column_metrics:list[ColumnMetric]):
        self.session.add_all([ColumnMetricMapper.to_model(cm) for cm in column_metrics])
    
    async def get_column_info_by_id(self,column_id:str)->ColumnInfo|None:
        column_info:ColumnInfoMySQL| None = await self.session.get(ColumnInfoMySQL,column_id)   #不是传入业务实体，而是和session 绑定的orm实体类对象
        if column_info :
            return ColumnInfoMapper.to_entity(column_info)
        else:
            return None

    async def get_table_info_by_id(self,id:str)->TableInfo|None:
        table_info:TableInfoMySQL| None = await self.session.get(TableInfoMySQL,id)   #不是传入业务实体，而是和session 绑定的orm实体类对象
        if table_info :
            return TableInfoMapper.to_entity(table_info)
        else:
            return None    
    async def get_key_columns_by_table_id(self,table_id:str)->list[ColumnInfo]:
        sql="SELECT * FROM column_info WHERE table_id = :table_id AND role in ('primary_key','foreign_key')"
        # :table_id 占位符

        result = await self.session.execute(text(sql),{"table_id":table_id})
        #第一个table_id是占位符 第二个table_id是实际值
        return [ColumnInfo(**dict(row)) for row in result.mappings().fetchall()] #把查询结果转换成业务实体对象列表
        #元组--字典列表--强制字典--业务实体对象列表
        #返回的是一个包含特定表内所有“主键”和“外键”信息的业务实体对象列表