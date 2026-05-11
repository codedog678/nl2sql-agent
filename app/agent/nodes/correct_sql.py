from langgraph.runtime import Runtime
import yaml
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from app.prompt.prompt_loader import load_prompt
from app.agent.llm import llm_coder


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "校正SQL", "status": "running"})

    sql = state["sql"]
    error = state["error"]
    query = state["query"]
    table_infos = state["table_infos"]
    metric_infos = state["metric_infos"]
    date_info = state["date_info"]
    db_info = state["db_info"]
    retry_count = state.get("sql_retry_count", 0)
    max_retries = state.get("max_retries", 2)
    try:
        prompt = PromptTemplate(template=load_prompt("correct_sql"), input_variables=["query", "metric_infos"])
        output_parser = StrOutputParser()

        chain = prompt | llm_coder | output_parser

        result = await chain.ainvoke(
            {"query": query,
                "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
                "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                "sql": sql,
                "error": error,
                "retry_count": retry_count,
                "max_retries": max_retries
                })
        writer({"type": "progress", "step": "校正SQL", "status": "success"})
        logger.info(f"校正后的SQL: {result}")
        return {'sql':result}
    except Exception as e:
        writer({"type": "progress", "step": "校正SQL", "status": "error"})
        logger.error(f"校正SQL失败:{str(e)}")
        raise