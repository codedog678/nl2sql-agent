#怎么解决找不到包的问题：所执行脚本所在的目录一定会在sys.path中，但是app.core.log不在当前目录下，所以需要把app所在的目录添加到sys.path中
#把app所在的目录添加到sys.path中
import asyncio
import sys
sys.path.append(r'E:\5.study\5.project\selfone')  
from app.agent.nodes.error_handler import error_handler   #熔断处理
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.clients.es_client_manager  import es_client_manager
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.clients.mysql_client_manaager import mysql_client_manager
from app.clients.mysql_client_manaager import dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.embedding_client_manager import embedding_client_manager
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository

from app.agent.nodes.extract_keywords import extract_keywords
from langgraph.graph import END, START, StateGraph
from app.agent.context import DataAgentContext
from app.agent.nodes.add_extra_context import add_extra_context
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.execute_sql import execute_sql
from app.agent.nodes.filter_metric import filter_metric
from app.agent.nodes.filter_table import filter_table
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository


graph_builder = StateGraph(state_schema=DataAgentState,context_schema=DataAgentContext)

# 添加节点
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("recall_column", recall_column)
graph_builder.add_node("recall_value", recall_value)
graph_builder.add_node("recall_metric", recall_metric)
graph_builder.add_node("merge_retrieved_info", merge_retrieved_info)
graph_builder.add_node("filter_metric", filter_metric)
graph_builder.add_node("filter_table", filter_table)
graph_builder.add_node("add_extra_context", add_extra_context)
graph_builder.add_node("generate_sql", generate_sql)
graph_builder.add_node("validate_sql", validate_sql)
graph_builder.add_node("correct_sql", correct_sql)
graph_builder.add_node("execute_sql", execute_sql)
graph_builder.add_node("error_handler", error_handler)

# 添加关系   普通边
graph_builder.add_edge(START, "extract_keywords")
graph_builder.add_edge("extract_keywords", "recall_column")
graph_builder.add_edge("extract_keywords", "recall_value")
graph_builder.add_edge("extract_keywords", "recall_metric")
graph_builder.add_edge("recall_column", "merge_retrieved_info")
graph_builder.add_edge("recall_value", "merge_retrieved_info")
graph_builder.add_edge("recall_metric", "merge_retrieved_info")
graph_builder.add_edge("merge_retrieved_info", "filter_table")
graph_builder.add_edge("merge_retrieved_info", "filter_metric")
graph_builder.add_edge("filter_table", "add_extra_context")
graph_builder.add_edge("filter_metric", "add_extra_context")
graph_builder.add_edge("add_extra_context", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")

#添加条件边  参数：1.source 起始节点  2.path决定分支逻辑  3.path_map逻辑映射到哪个节点(可选)
#错误信息需要记录到state中 通过状态进行判断
# graph_builder.add_conditional_edges(source='validate_sql',
#                                  path=lambda state:"execute_sql" if state['error'] is None else 'correct_sql',
#                                  path_map={'execute_sql':'execute_sql','correct_sql':'correct_sql'})
# graph_builder.add_edge("correct_sql", "execute_sql")

#添加熔断机制
def decide_next_after_validate(state: DataAgentState):
    error = state.get("error")
    retry_count = state.get("sql_retry_count", 0)
    max_retries = state.get("max_retries", 2)
    
    if error is None:
        return "execute_sql"
    elif retry_count < max_retries:
        # 注意：retry_count 已经在 validate 中增加了，这里判断 <表示还可以重试
        return "correct_sql"
    else:
        return "error_handler"

graph_builder.add_conditional_edges(
    "validate_sql",
    decide_next_after_validate,
    {
        "execute_sql": "execute_sql",
        "correct_sql": "correct_sql",
        "error_handler": "error_handler"
    }
)
# 关键：correct_sql 之后必须回到 validate_sql，而不是直接 execute_sql
graph_builder.add_edge("correct_sql", "validate_sql")
# execute_sql 之后结束
graph_builder.add_edge("execute_sql", END)
# error_handler 之后结束
graph_builder.add_edge("error_handler", END)


# 编译图
graph = graph_builder.compile()
# print(graph.get_graph().draw_mermaid())

if __name__ == '__main__':
    async def test():
        # 1. 初始化外部环境：创建客户端，连接数据库，准备好 Repository
        qdrant_client_manager.init()
        embedding_client_manager.init()
        es_client_manager.init()
        mysql_client_manager.init()
        dw_mysql_client_manager.init()
        #session
        async with mysql_client_manager.session_factory() as meta_session,dw_mysql_client_manager.session_factory() as dw_session:
            meta_mysql_repository = MetaMySQLRepository(meta_session)
            dw_mysql_repository = DWMySQLRepository(dw_session)

            metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
            column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
            value_es_repository = ValueEsRepository(es_client_manager.client)
            # 2. 初始化 State (初始记忆)
            state = DataAgentState(query="有没有哪一天是一单都没有卖出去的",
            keywords=[],
            error=None,  # 必须初始化为 None
            retrieved_column_infos=[],
            sql_retry_count=0,
            max_retries=2)
            # 3. 初始化 Context (工具箱内容)
            context = DataAgentContext(column_qdrant_repository=column_qdrant_repository,
                                    embedding_client=embedding_client_manager.client,
                                    metric_qdrant_repository=metric_qdrant_repository,
                                    value_es_repository=value_es_repository,
                                    meta_mysql_repository=meta_mysql_repository,
                                    dw_mysql_repository=dw_mysql_repository)
            async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                print(chunk)

        await qdrant_client_manager.close()
        await es_client_manager.close()
        await mysql_client_manager.close()
        await dw_mysql_client_manager.close()
        
        
    asyncio.run(test())

