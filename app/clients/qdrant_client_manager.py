from qdrant_client import AsyncQdrantClient
import asyncio
from app.conf.app_config import QdrantConfig, app_config

class QdrantClientManager:
    def __init__(self,qdrant_config:QdrantConfig):
        self.client:AsyncQdrantClient  = None
        self.qdrant_config:QdrantConfig = qdrant_config

    # def init(self):
    #     #self.client=AsyncQdrantClient(host="localhost", port=6333)
    #     self.client=AsyncQdrantClient(host=self.config.host, port=self.config.port)
    def _get_url(self):
        return f"http://{self.qdrant_config.host}:{self.qdrant_config.port}"

    def init(self):
        self.client = AsyncQdrantClient(url=self._get_url())

    async def close(self):
        await self.client.close()
    
qdrant_client_manager=QdrantClientManager(app_config.qdrant)
#.init()就可以了，后续在需要使用client的地方直接使用qdrant_client_manager.client即可。
