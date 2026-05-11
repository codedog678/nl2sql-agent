
from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.entities.value_info import ValueInfo


class ValueEsRepository:
    index_name='value_index'
    index_mappings = {
        "dynamic": False,  # 不允许动态添加字段
        "properties": {
            "id": {"type": "keyword"},  #analyzer 分词器   search_analyzer 搜索分词器（对查询做分词）
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}   # 关联的字段id  keyword不会做分词  text会做分词
        }}
    
    def __init__(self, client:AsyncElasticsearch):
        self.client = client
    async def ensure_index(self):
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(index=self.index_name, mappings=self.index_mappings)

    async def index(self, value_infos: list[ValueInfo], batch_size=5):
    # 外层循环：按 batch_size 分段处理
        for i in range(0, len(value_infos), batch_size):
            batch = value_infos[i:i + batch_size]
            operations = []
            
            # 内层循环：仅负责构造当前 batch 的 operations 列表 
            for value_info in batch:
                operations.append({"index": {"_index": self.index_name, "_id": value_info.id}})
                operations.append(asdict(value_info))
            
            # await 应该与内层 for 对齐
            # 表示当整个 batch (比如 20 条) 准备好了，再一次性发送给数据库
            await self.client.bulk(operations=operations)

    async def search(self,keyword:str,score_threshold=0.5,limit=20)->list[ValueInfo]:
        result = await self.client.search(index=self.index_name,
                                            query={
                                                "match": {
                                                    "value": keyword
                                                }},
                                            min_score=score_threshold,
                                            size=limit
                                            )
        return [ValueInfo(**hit['_source']) for hit in result['hits']['hits']]
    #result['hits']['hits']是一个列表，每个元素是一个字典 包含__source字段，该字段是一个字典，包含value_info的属性值