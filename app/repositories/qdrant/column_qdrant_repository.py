from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.entities.column_info import ColumnInfo


class ColumnQdrantRepository:
    collection_name='column_info_collenction' #向量索引召回字段 所以名字就是 字段信息表
    def __init__(self,client:AsyncQdrantClient):
        self.client=client
    
    #创建
    async def ensure_collection(self):
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name, 
                vectors_config=VectorParams(size=1536,distance=Distance.COSINE)) #设置向量维度取决于选的向量模型，距离计算方式为余弦距离
    #size也可以读取config文件获取 app_config.qdrant.embedding_size

    #写
    async def upsert(self,ids,embeddings,payloads,batch_size=10):
        #zip()会得到一个迭代器  可以写推导式
        points=[{"id":id,"vector":embedding,"payload":payload} for id,embedding,payload in zip(ids,embeddings,payloads)]
        for i in range(0,len(points),batch_size):
            await self.client.upsert(collection_name=self.collection_name, points=points[i:i+batch_size])   
    async def search(self,embedding,limit=20,score_threshold=0.5)->list[ColumnInfo]:
        #查询向量相似度最高的limit个字段
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        #不能直接返回result 因为要转换成ColumnInfo对象 query_points现在返回的是dict 还需要转换
        return [ColumnInfo(**point.payload) for point in result.points]




