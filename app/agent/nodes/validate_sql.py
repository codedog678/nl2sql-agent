from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "验证SQL", "status": "running"})
    dw_mysql_repository = runtime.context["dw_mysql_repository"]
    sql = state["sql"]
    retry_count = state.get("sql_retry_count", 0)
    max_retries = state.get("max_retries", 2)
    try:
        try:
            await dw_mysql_repository.validate(sql)
            logger.info(f"SQL验证成功: {sql}")
            writer({"type": "progress", "step": "验证SQL成功", "status": "success"})
            # 验证成功，清除错误，重置计数器
            return {"error": None,"sql_retry_count": 0}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"SQL 验证失败: {sql}, 错误: {error_msg}")
        
            if retry_count < max_retries:
            # 还可以重试
                writer({"type": "progress", "step": "验证 SQL", "status": "error", "retryable": True})
                return {"error": error_msg, "sql_retry_count": retry_count + 1}
            else:
            # 超过最大重试次数，熔断
                writer({"type": "progress", "step": "验证 SQL", "status": "error", "retryable": False})
                logger.error(f"SQL 验证失败且已达最大重试次数 {max_retries}")
                return {"error": error_msg}   # 仍然保留错误，但后续会走向 error_handler
    except Exception as e:
        writer({"type": "progress", "step": "验证SQL", "status": "error"})
        raise
    

