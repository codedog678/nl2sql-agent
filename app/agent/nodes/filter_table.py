from langgraph.runtime import Runtime
import yaml
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from app.agent.llm import llm_text
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "过滤表格", "status": "running"})
    query = state["query"]
    table_infos = state["table_infos"]
    table_infos:list[TableInfoState] = state.get('table_infos')
    try:
    #要把table_infos中 内存中的每个对象都序列化 要转化成序列化数据给大模型  结构化->序列化
        prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=["query", "table_infos"])
        output_parser = JsonOutputParser()
        chain = prompt | llm_text | output_parser
        #allow_unicode允许输出中文字符，而不是 \u5317\u4eac 这种 Unicode 转义
        #sort_keys=False 保持字典的顺序不变
        result =await chain.ainvoke({'query':query, 
                                    'table_infos':yaml.dump(table_infos,allow_unicode=True,sort_keys=False)})
        # 利用模型输出过滤table_infos  table_infos: list[TableInfoState]现在 保留哪些表，以及每张表保留哪些字段
            # {
            #   'fact_order':['order_amount', 'region_id'],
            #   'dim_region':['region_id', 'region_name']
            # }
        #  python中遍历列表 不能直接删除元素 所以用了一个新的列表 table_infos[:] 会在内存中创建一个原列表的浅拷贝 原列表元素的引用（指针）不会改变
        # 迭代器是在这个“快照”列表上走，它的索引和内容是固定的  删除对象：table_infos.remove(...) 作用于原列表 。
    
        for table_info in table_infos[:]:
                if table_info["name"] not in result:
                    table_infos.remove(table_info)
                else:#如果当前表在 精简字段
                    selected_columns = result[table_info["name"]]#这个表下的字段
                    for column_info in table_info["columns"][:]:
                        if column_info["name"] not in selected_columns:
                            table_info["columns"].remove(column_info)
        writer({"type": "progress", "step": "过滤表格", "status": "success"})
        logger.info(f"过滤后的表信息：{[table_info['name'] for table_info in table_infos]}")
        return {'table_infos':table_infos}
    except Exception as e:
        writer({"type": "progress", "step": "过滤表格", "status": "error"})
        logger.error(f"过滤表失败:{str(e)}")
        raise