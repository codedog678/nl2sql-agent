#同步  之后写一个异步
from qdrant_client import QdrantClient
from app.conf.app_config import QdrantConfig, app_config

class QdrantClientManager:
    def __init__(self,config:QdrantConfig):
        self.client:QdrantClient  = None
        self.config:QdrantConfig = config

    def init(self):
        #self.client=QdrantClient(host="localhost", port=6333)
        self.client=QdrantClient(host=self.config.host, port=self.config.port)

    def close(self):
        self.client.close()
    
qdrant_client_manager=QdrantClientManager(app_config.qdrant)
#.init()就可以了，后续在需要使用client的地方直接使用qdrant_client_manager.client即可。