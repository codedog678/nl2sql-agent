from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from langchain_core.prompts import PromptTemplate
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt
from langchain_core.output_parsers import JsonOutputParser
from app.agent.llm import llm_text
from app.core.log import logger

async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})
    query = state['query']
    keywords = state['keywords']
    embedding_client = runtime.context['embedding_client']
    metric_qdrant_repository = runtime.context['metric_qdrant_repository']
    try:
        prompt= PromptTemplate(template=load_prompt('extend_keywords_for_metric_recall'),
                            input_variables=['query'])
        output_parser=JsonOutputParser()  #JSON数据(对象/数组）→字典/列表
        chain=prompt|llm_text|output_parser
        result=await chain.ainvoke({'query':query})
        keywords=list(set(keywords+result))
        
        metric_info_map: dict[str, MetricInfo] = {}

        # 6. 从qdrant中拿到召回的字段信息
        for keyword in keywords:
            # 6.1 对keyword进行向量化
            #logger.info(f"keyword type: {type(keyword)}, value: {keyword}")
            embedding = await embedding_client.aembed_query(keyword)
            # 6.2 向qdrant中查询  补充repository的search方法
            current_column_infos:list[MetricInfo]=await metric_qdrant_repository.search(embedding)
            # 6.3 本来用下面合并结果 但是直接extend可能会导致 column_infos 里有重复的元素 
            # 因为A,B两个关键字可能会召回同样的字段；
            # 同时想一行数据多个点存储在多行 但是对应的是同一个字段的payload（比如name 和alias召回同一个）
            #column_infos.extend(current_column_infos)
            # 6.3 去重合并
            for metric_info in current_column_infos:
                if metric_info.id not in metric_info_map:
                    metric_info_map[metric_info.id]=metric_info
        retrieved_metric_infos=list(metric_info_map.values())#values()返回的是一个MetricInfo的迭代器，需要转成list
        # 验证 获取key 也就是id
        writer({"type": "progress", "step": "召回指标", "status": "success"})
        logger.info(f"检索到的指标信息:{list(metric_info_map.keys())}")
        return {"retrieved_metric_infos":retrieved_metric_infos}
    except Exception as e:
        writer({"type": "progress", "step": "召回指标", "status": "error"})
        logger.error(f"召回指标信息失败: {str(e)}")
        raise