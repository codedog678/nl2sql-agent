from app.core.log import logger
from dataclasses import asdict
from pathlib import Path
import uuid
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf
from app.conf.meta_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledegeService:
    def __init__(self, 
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository:DWMySQLRepository,
                 column_qdrant_repository:ColumnQdrantRepository,
                 embedding_client:HuggingFaceEndpointEmbeddings,
                 metric_qdrant_repository:MetricQdrantRepository,
                 value_es_repository:ValueEsRepository
                 ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository:ColumnQdrantRepository=column_qdrant_repository
        self.embedding_client:HuggingFaceEndpointEmbeddings=embedding_client
        self.value_es_repository:ValueEsRepository=value_es_repository
        self.metric_qdrant_repository:MetricQdrantRepository=metric_qdrant_repository

    async def _save_tables_to_meta_db(self,meta_config:MetaConfig)->list[ColumnInfo]:
        #配置文件中有表信息 表信息的同步
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []
        #2.1 将表信息和字段信息保存到meta数据库中（mysql)--column_info 和 table_info表
        for table in meta_config.tables:
            #table->table_info表  
            table_info=TableInfo(id=table.name,
                                        name=table.name,
                                        role=table.role,
                                        description=table.description,)
            table_infos.append(table_info)
            #查询字段的类型 一表一查  查询字段类型：
            column_types = await self.dw_mysql_repository.get_column_types(table.name)

            for column in table.columns:
                #column->column_info表
                #查询字段的取值示例 一个字段一查
                column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name)
                column_info=ColumnInfo(id=f'{table.name}.{column.name}',#由表名和列名组成 唯一
                                            name=column.name,
                                            type=column_types[column.name],#本身就是字段名作为key 类型作为值构造的字典 
                                            role=column.role,
                                            examples=column_values,
                                            description=column.description,
                                            alias=column.alias,
                                            table_id=table.name)
                column_infos.append(column_info)
        async with self.meta_mysql_repository.session.begin():#开启事务 开启一个事务 事务生命周期自动管理
            #上面一行代码的意思是 开启一个事务 这个事务的生命周期由这个上下文管理器自动管理 也就是在这个代码块中执行的操作都在这个事务中 
            # 如果代码块中的操作没有异常 那么这个事务就会提交 如果代码块中的操作有异常 那么这个事务就会回滚 这样就保证了数据的一致性 和完整性
            # 这样就不需要显式的调用commit或者rollback了 也不需要担心忘记调用了 这样就更安全了
        #把表信息和字段信息保存到meta数据库中,也就是meta_mysql_repository中，需要有数据库读取写入逻辑
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)
        #await self.meta_mysql_repository.session.commit()#提交事务 只有commit的时候才会真正写入数据库 之前只是添加到session中 还没有写入数据库 所以需要commit
        return column_infos

    async def _save_columns_to_qdrant(self,column_infos:list[ColumnInfo]):
        #2.2 对字段信息建立向量索引（qdrant） 需要把字段信息转成向量 需要用到模型（embedding_model） 这个模型的选择可以在配置文件中指定
            #字段名 描述信息  每个别名都是检索目标  每一个检索目标在向量空间都是一个点
            #读写操作都放在 repository层
            #qdrant 的collection->Table  Points->row（行） Payload->Metadata（元数据） 或 JSON 字段  每一个点三个信息：id 向量 元数据
        await self.column_qdrant_repository.ensure_collection()
        points:list[dict]=[]
        for column_info in column_infos:
            points.append({'id':uuid.uuid4(),
                            'embedding_text':column_info.name,#本来应该是vector 但是要经过模型转换 所以这里用了要转成向量的文本 等之后批量处理
                            'payload':asdict(column_info) #payload接受字典类型数据 这里把column_info转成字典类型数据
                            })
            points.append({'id':uuid.uuid4(),
                            'embedding_text':column_info.description,#后面的点
                            'payload':asdict(column_info) #payload接受字典类型数据 这里把column_info转成字典类型数据
                            })
            for alias in column_info.alias:
                points.append({'id':uuid.uuid4(),
                                'embedding_text':alias,#后面的点
                                'payload':asdict(column_info) #payload接受字典类型数据 这里把column_info转成字典类型数据
                                })
        #批量插入向量索引
        embeddings:list[list[float]]=[]
        embedding_texts=[point['embedding_text'] for point in points]  #拿到全部需要向量化的文档
        embedding_batch_size=20
        for i in range(0,len(embedding_texts),embedding_batch_size):
            batch_embedding_texts=embedding_texts[i:i+embedding_batch_size]
            batch_embeddings=await self.embedding_client.aembed_documents(batch_embedding_texts) #用模型转换成向量
            embeddings.extend(batch_embeddings)  #extend和append的区别是append 是“整体打包”，extend 是“拆解合并”
        #把向量索引保存到qdrant中
        ids=[point['id'] for point in points]
        payloads=[point['payload'] for point in points]
        await self.column_qdrant_repository.upsert(ids,embeddings,payloads)

    async def _save_values_to_es(self,meta_config:MetaConfig):
    #2.3 对指定的维度字段建立全文索引（elasticsearch）  实际上做的是全文检索 后续可以考虑加上混合索引
        #es的几个概念：index-table  document-row  field-column  mapping(索引的字段元数据配置规则)-schema
        #读写操作都放在 repository层  es的   时刻记住对 值 做索引
        await self.value_es_repository.ensure_index()
        value_infos:list[ValueInfo]=[]
        for table in meta_config.tables:
            for column in table.columns:#查询每个字段
                if column.sync:#如果是要建立全文索引的维度字段
                    #查询这个字段的取值
                    current_column_values=await self.dw_mysql_repository.get_column_values(table.name, column.name,limit=100000)
                    current_values_infos=[ValueInfo(id=f'{table.name}.{column.name}.{current_column_value}',
                                                    value=current_column_value,
                                                    column_id=f'{table.name}.{column.name}') for 
                                                    current_column_value in current_column_values]
                    
                    value_infos.extend(current_values_infos)
        #把值信息保存到es中
        await self.value_es_repository.index(value_infos)
    
    async def _save_metrics_to_meta_db(self,meta_config:MetaConfig)->list[MetricInfo]:
    
        #3.1 将指标信息保存到meta数据库中（mysql)--metric_info 和 metric_column_info表
        metric_infos:list[MetricInfo]=[]
        column_metrics:list[ColumnMetric]=[]

        for metric in meta_config.metrics:
            #metric->metric_info表 MetricInfo
            metric_info=MetricInfo(id=metric.name,
                                    name=metric.name,
                                    description=metric.description,
                                    relevant_columns=metric.relevant_columns,
                                    alias=metric.alias)
            metric_infos.append(metric_info)
            for column in metric.relevant_columns:
                #column->metric_column_info表 ColumnMetric
                column_metric=ColumnMetric(column_id=column,metric_id=metric.name)
                column_metrics.append(column_metric)

        async with self.meta_mysql_repository.session.begin():#开启事务 开启一个事务 事务生命周期自动管理
            self.meta_mysql_repository.save_metric_infos(metric_infos)
            self.meta_mysql_repository.save_column_metric(column_metrics)
        return metric_infos
    
    async def _save_metrics_to_qdrant(self,metric_infos:list[MetricInfo]):
        #3.2 对指标信息建立向量索引
        await self.metric_qdrant_repository.ensure_collection()
        points:list[dict]=[]
        for metric_info in metric_infos:
            points.append({'id':uuid.uuid4(),
                            'embedding_text':metric_info.name,#本来应该是vector 但是要经过模型转换 所以这里用了要转成向量的文本 等之后批量处理
                            'payload':asdict(metric_info) #payload接受字典类型数据 这里把column_info转成字典类型数据
                            })
            points.append({'id':uuid.uuid4(),
                            'embedding_text':metric_info.description,#后面的点
                            'payload':asdict(metric_info) #payload接受字典类型数据 这里把column_info转成字典类型数据
                            })
            for alias in metric_info.alias:
                points.append({'id':uuid.uuid4(),
                                'embedding_text':alias,#后面的点
                                'payload':asdict(metric_info) #payload接受字典类型数据 这里把column_info转成字典类型数据
                                })
        #批量插入向量索引
        embeddings:list[list[float]]=[]
        embedding_texts=[point['embedding_text'] for point in points]  #拿到全部需要向量化的文档
        embedding_batch_size=20
        for i in range(0,len(embedding_texts),embedding_batch_size):
            batch_embedding_texts=embedding_texts[i:i+embedding_batch_size]
            batch_embeddings=await self.embedding_client.aembed_documents(batch_embedding_texts) #用模型转换成向量
            embeddings.extend(batch_embeddings)  #extend和append的区别是append 是“整体打包”，extend 是“拆解合并”
        #把向量索引保存到qdrant中
        ids=[point['id'] for point in points]
        payloads=[point['payload'] for point in points]
        await self.metric_qdrant_repository.upsert(ids,embeddings,payloads)
    
    
    async def build(self,config_path=None):
        #1.读取配置文件  要看配置文件是什么样子
        # 配置文件加载逻辑
        context = OmegaConf.load(config_path)  # 加载 YAML 文件 读文件内容
        schema = OmegaConf.structured(MetaConfig)   #读对应的结构 是表还是字段
        # 合并配置并转换为对象 
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("加载配置文件成功")

        #2.根据配置文件 去同步指定的表、指标信息
        # print(meta_config.metrics)  测试
        if meta_config.tables:#是否存在  
            #2.1写成私有方法了  _save_tables_to_meta_db(self,meta_config:MetaConfig)
            column_infos=await self._save_tables_to_meta_db(meta_config)
            logger.info("保存表信息和字段信息到数据库成功")
            #2.2 写成私有方法了 _save_columns_to_qdrant(self,column_infos:list[ColumnInfo])
            await self._save_columns_to_qdrant(column_infos)
            logger.info("为字段信息建立向量索引成功")
            
            #2.3 写成私有方法了 _save_values_to_es(self,meta_config:MetaConfig)
            await self._save_values_to_es(meta_config)
            logger.info("为指定维度字段建立全文索引成功")
        
        #3.根据配置文件 去同步指定的指标信息
        if meta_config.metrics:#是否存在
            #3.1 写成私有方法了 _save_metrics_to_meta_db
            metric_infos=await self._save_metrics_to_meta_db(meta_config)
            logger.info("保存指标信息到数据库成功")

            #3.2 写成私有方法了 _save_metrics_to_qdrant
            await self._save_metrics_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引成功")