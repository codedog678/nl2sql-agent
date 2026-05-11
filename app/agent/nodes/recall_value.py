from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from app.agent.llm import llm_text
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):#全文检索
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段取值", "status": "running"})
    query = state['query']
    keywords = state['keywords']
    value_es_repository=runtime.context['value_es_repository']
    #扩展关键词
    try:
        prompt= PromptTemplate(template=load_prompt('extend_keywords_for_value_recall'),
                            input_variables=['query'])
        output_parser=JsonOutputParser()  #JSON数据(对象/数组）→字典/列表
        chain=prompt|llm_text|output_parser
        result=await chain.ainvoke({'query':query})
        keywords=list(set(keywords+result))
        #根据关键词召回字段取值
        value_infos_map:dict[str,ValueInfo]={}
        for keyword in keywords:
            current_value_infos:list[ValueInfo]=await value_es_repository.search(keyword)
            #去重
            for current_value_info in current_value_infos:
                if current_value_info.id not in value_infos_map:
                    value_infos_map[current_value_info.id]=current_value_info
        retrieved_value_infos:list[ValueInfo]=list(value_infos_map.values())
        writer({"type": "progress", "step": "召回字段取值", "status": "success"})
        logger.info(f"检索到字段取值：{list(value_infos_map.keys())}")
        return {'retrieved_value_infos':retrieved_value_infos}
    except Exception as e:
        writer({"type": "progress", "step": "召回字段取值", "status": "error"})
        logger.error(f"召回字段取值失败: {str(e)}")
        raise