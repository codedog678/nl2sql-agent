import json

from langchain_community.embeddings import DashScopeEmbeddings

from app.agent.graph import graph
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.repositories.mysql.meta import meta_mysql_repository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository


class QueryService: 
    def __init__(self,
                 meta_mysql_repository: meta_mysql_repository.MetaMySQLRepository,
                 dw_mysql_repository : DWMySQLRepository,
                 metric_qdrant_repository: MetricQdrantRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 value_es_repository: ValueEsRepository,
                 embedding_client:DashScopeEmbeddings
                 ):# 存储所有 repository 和 client
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.metric_qdrant_repository =metric_qdrant_repository 
        self.column_qdrant_repository = column_qdrant_repository
        self.value_es_repository = value_es_repository
        self.embedding_client = embedding_client

    async def query(self, query: str):
    #得到前端用户的问题 交给graph 进行处理 得到答案 然后返回给前端
    #把用户查询封装成图的state
        state = DataAgentState(query=query,
                        keywords=[],
                        error=None,  # 必须初始化为 None
                        retrieved_column_infos=[])
                # context 里面包含了所有需要的依赖 现在要用fastapi的依赖注入来实现
        context = DataAgentContext(column_qdrant_repository=self.column_qdrant_repository,
                                embedding_client=self.embedding_client,
                                metric_qdrant_repository=self.metric_qdrant_repository,
                                value_es_repository=self.value_es_repository,
                                meta_mysql_repository=self.meta_mysql_repository,
                                dw_mysql_repository=self.dw_mysql_repository)
        try:
            async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                #转成json 序列化 ensure_ascii=False 防止中文乱码
                yield f"data: {json.dumps(chunk,ensure_ascii=False,default=str)}\n\n"  #sse协议格式
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False, default=str)}\n\n" 