from langchain.chat_models import init_chat_model
from app.conf.app_config import app_config

# 初始化 Coder 模型
llm_coder = init_chat_model(
    model=app_config.llm_coder.model_name,
    model_provider='openai', 
    base_url=app_config.llm_coder.base_url,
    api_key=app_config.llm_coder.api_key,
    temperature=0
)

# 初始化 Text 模型
llm_text = init_chat_model(
    model=app_config.llm_text.model_name,
    model_provider='openai',
    base_url=app_config.llm_text.base_url,
    api_key=app_config.llm_text.api_key,
    temperature=0
)

if __name__ == '__main__':
    #print(llm_coder.invoke("你编码能力怎么样").content)  #测试成功
    pass