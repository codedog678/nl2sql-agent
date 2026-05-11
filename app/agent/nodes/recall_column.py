from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from app.agent.llm import llm_text
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt

async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    # 1. 实时反馈：通过 stream_writer 给前端发消息，告诉用户“我正在找字段”
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段", "status": "running"})


    # 2. 读取记忆：从 State 中提取之前节点找出的“关键词” 读取问题
    keywords = state['keywords'] 
    query=state['query']
    
    # 3. 提取工具：从 Context 中拿到已经初始化好的 Qdrant 仓库对象
    # 注意：这里 runtime.context 实际上就是从 DataAgentContext 映射过来的
    column_qdrant_repository = runtime.context['column_qdrant_repository']
    embedding_client = runtime.context['embedding_client']
    try:
        # 4. 借助LLM扩展关键词 期望结构化输出
        #input_variables是key value形式的变量，这里只有一个变量query
        prompt= PromptTemplate(template=load_prompt('extend_keywords_for_column_recall'),
                            input_variables=['query'])
        output_parser=JsonOutputParser()  #JSON数据(对象/数组）→字典/列表
        chain=prompt|llm_text|output_parser
        result=await chain.ainvoke({'query':query})

        # 5.合并去重关键词
        # 使用扩展后的关键词召回字段信息
        column_info_map: dict[str, ColumnInfo] = {}
        keywords=list(set(keywords+result))

        # 6. 从qdrant中拿到召回的字段信息
        for keyword in keywords:
            # 6.1 对keyword进行向量化
            #logger.info(f"keyword type: {type(keyword)}, value: {keyword}")
            embedding = await embedding_client.aembed_query(keyword)
            # 6.2 向qdrant中查询  补充repository的search方法
            current_column_infos:list[ColumnInfo]=await column_qdrant_repository.search(embedding)
            # 6.3 本来用下面合并结果 但是直接extend可能会导致 column_infos 里有重复的元素 
            # 因为A,B两个关键字可能会召回同样的字段；
            # 同时想一行数据多个点存储在多行 但是对应的是同一个字段的payload（比如name 和alias召回同一个）
            #column_infos.extend(current_column_infos)
            # 6.3 去重合并
            for column_info in current_column_infos:
                if column_info.id not in column_info_map:
                    column_info_map[column_info.id]=column_info
        retrieved_column_infos=list(column_info_map.values())#values()返回的是一个ColumnInfo的迭代器，需要转成list
        # 验证 获取key 也就是id
        writer({"type": "progress", "step": "召回字段", "status": "success"})
        logger.info(f"检索到的字段信息:{list(column_info_map.keys())}")
        return {"retrieved_column_infos":retrieved_column_infos}
            
    except Exception as e:
        writer({"type": "progress", "step": "召回字段", "status": "error"})
        logger.error(f"召回字段信息失败: {str(e)}")
        raise
        
