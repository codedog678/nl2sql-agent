import asyncio
import json
from pathlib import Path
from app.core.log import logger
from app.core.context import request_id_ctx_var
request_id_ctx_var.set("eval-test")

# 引入项目已有的组件
from app.agent.state import DataAgentState
from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manaager import mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

DATASET_FILE = Path(__file__).parents[2] / "evaluation_cases.json"

async def evaluate():
    # 1. 加载数据集（保持与原 DATASET 相同的列表格式）
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        DATASET = json.load(f)
    # 确保每条记录都有 expected_tables 和 expected_columns 字段（与原逻辑兼容）
    for item in DATASET:
        item.setdefault("expected_tables", [])
        item.setdefault("expected_columns", [])

    # 2. 初始化各类客户端环境 
    logger.info("正在初始化基础服务环境...")
    embedding_client_manager.init()
    qdrant_client_manager.init()
    es_client_manager.init()
    mysql_client_manager.init()
    dw_mysql_client_manager.init()

    # 准备统计数据
    total_queries = len(DATASET)
    table_recall_sum = 0.0
    column_recall_sum = 0.0


    async with mysql_client_manager.session_factory() as meta_session, dw_mysql_client_manager.session_factory() as dw_session:
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueEsRepository(es_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)

        context = DataAgentContext(
            embedding_client=embedding_client_manager.client,
            column_qdrant_repository=column_qdrant_repository,
            value_es_repository=value_es_repository,
            metric_qdrant_repository=metric_qdrant_repository,
            meta_mysql_repository=meta_mysql_repository,
            dw_mysql_repository=dw_mysql_repository
        )

        logger.info(f"开始评估，共 {total_queries} 条测试用例...")
        
        for idx, item in enumerate(DATASET, 1):
            query = item["query"]
            expected_tables = set(item.get("expected_tables", []))
            expected_columns = set(item.get("expected_columns", []))

            # 初始化State
            state = DataAgentState(
                query=query, 
                keywords=[], 
                error=None, 
                retrieved_column_infos=[]
            )

            actual_tables = set()
            actual_columns = set()

            # 关键点：使用 stream_mode="updates"，并且在 filter_table 完成后拦截，终止运行
            async for chunk in graph.astream(input=state, context=context, stream_mode="updates"):
                # chunk 是字典格式，key是执行完毕的节点名称
                if "filter_table" in chunk:
                    # 此时已经拿到了经过召回并被大模型过滤后的最终表和字段信息
                    table_infos = chunk["filter_table"].get("table_infos", [])
                    
                    # 提取实际召回的表和字段名称
                    for t_info in table_infos:
                        actual_tables.add(t_info["name"])
                        for c_info in t_info["columns"]:
                            actual_columns.add(c_info["name"])
                    
                    # 拦截，不继续往下跑 generate_sql
                    break 
            
            # 计算单条的Recall (TP / (TP + FN))
            t_recall = len(expected_tables & actual_tables) / len(expected_tables) if expected_tables else 1.0
            c_recall = len(expected_columns & actual_columns) / len(expected_columns) if expected_columns else 1.0
            
            table_recall_sum += t_recall
            column_recall_sum += c_recall

            # 打印当前进度明细
            logger.info(f"[{idx}/{total_queries}] Query: {query}")
            logger.info(f" ┣ 表召回: {t_recall:.2%} (预期: {expected_tables}, 实际: {actual_tables})")
            logger.info(f" ┗ 字段召回: {c_recall:.2%} (预期: {expected_columns}, 实际: {actual_columns})\n")

    # 2. 计算宏平均 (Macro-average) 召回率
    final_table_recall = table_recall_sum / total_queries
    final_column_recall = column_recall_sum / total_queries

    print("=" * 50)
    print("📈 检索能力量化评估报告")
    print("=" * 50)
    print(f"总测试用例数: {total_queries}")
    print(f"表级召回率 (Table Recall) : {final_table_recall:.2%}")
    print(f"字段召回率 (Column Recall): {final_column_recall:.2%}")
    print("=" * 50)

    # 3. 关闭所有资源
    await qdrant_client_manager.close()
    await es_client_manager.close()
    await mysql_client_manager.close()
    await dw_mysql_client_manager.close()


if __name__ == '__main__':
    asyncio.run(evaluate())