from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
class DWMySQLRepository:
    def __init__(self, session:AsyncSession):
        self.session = session

    async def get_column_types(self,table_name:str)->dict[str,str]:
        #这里是查询字段类型的逻辑 
        sql=f'show columns from {table_name}'
        result=await self.session.execute(text(sql))  #不能直接执行sql 需要用text包装一下
        result_dict=result.mappings().fetchall()
        #fetchall()获得row对象的 列表 访问需要通过下标不方便 用mappings()把结果转换成字典 访问就方便了
        #想要结果{order_id:varchar(30),......}  {字段名：字段类型}
        #但现在结构是一行的所有数据  通过字典推导式把它转换成想要的结构
        return {row['Field']:row['Type'] for row in result_dict}
    
    
    async def get_column_values(self,table_name:str,column_name:str,limit:int=10):
        #这里是查询字段取值的逻辑 
        sql=f'select distinct {column_name} from {table_name} limit {limit}' #取前10个不同的值作为示例
        result=await self.session.execute(text(sql))
        #row 对象根据索引访问 现在只有一列 就是column_name 通过row[0]访问 
        #想要结果本身就是一个列表  [value1,value2,...] 通过列表推导式把结果转换成想要的结构
        return [row[0] for row in result.fetchall()]
    async def get_db_info(self):
        sql='select version()'
        result=await self.session.execute(text(sql))
        #result.fetchall()[0][0]  #Sequence[Row[_TP]]  这里返回的是一个列表 里面是Row对象  Row对象是字典的子类 所以可以用字典的语法访问
        #如果只有一个值 只用scalar()方法即可
        version=result.scalar()
        dialect=self.session.bind.dialect.name  #获取数据库类型
        return {'version':version,'dialect':dialect}

    async def validate(self,sql:str):
        sql=f"explain {sql}"
        await self.session.execute(text(sql))  #如果报错会抛出异常 
    
    async def execute(self,sql:str)->list[dict]:#因为后端要给前端表格数据 所以这里返回的是列表 列表里面的元素是字典
        result=await self.session.execute(text(sql))  #如果报错会抛出异常 
        return [dict(row) for row in result.mappings().fetchall()]
#result.mappings().fetchall()“看起来”是字典，但它其实是一种特殊的、只读的映射对象，并不是 Python 中最标准的那种 dict
