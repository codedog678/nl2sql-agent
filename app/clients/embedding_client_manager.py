# # data-agent/app/clients/embedding_client_manager.py
# from typing import Optional
# from langchain_openai import OpenAIEmbeddings # 需要执行 uv add langchain-openai
# from app.conf.app_config import EmbeddingConfig, app_config

# class EmbeddingClientManager:
#     def __init__(self, config: EmbeddingConfig):
#         self.client: Optional[OpenAIEmbeddings] = None
#         self.config = config

#     def init(self):
#         # 使用兼容 OpenAI 接口的方式调用外部云端 API
#         self.client = OpenAIEmbeddings(
#             model=self.config.model,        # 必须确保是 "text-embedding-v2" 等阿里模型名
#             api_key=self.config.api_key,    # 现代参数名，建议替换 openai_api_key
#             base_url=self.config.base_url,  # 现代参数名，建议替换 openai_api_base
#             # 【关键修改】解决阿里百炼 400 错误的终极手段
#         # 阿里部分接口不认 LangChain 默认发送的 "encoding_format" 参数
#         # 【核心修改】不要设为 None，要显式设为 "float"
#         model_kwargs={"encoding_format": "float"}
#         )
       

# embedding_client_manager = EmbeddingClientManager(app_config.embedding)
# app/clients/embedding_client_manager.py
from typing import Optional
from langchain_community.embeddings import DashScopeEmbeddings # 替换导入
from app.conf.app_config import EmbeddingConfig, app_config

class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: Optional[DashScopeEmbeddings] = None
        self.config = config

    def init(self):
        # 阿里专用的类会自动处理字符串传输，不会强制转成数字
        self.client = DashScopeEmbeddings(
            model=self.config.model,        # 确保 YAML 里是 "text-embedding-v2"
            dashscope_api_key=self.config.api_key
        )

embedding_client_manager = EmbeddingClientManager(app_config.embedding)
