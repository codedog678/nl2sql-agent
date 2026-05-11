from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger

async def error_handler(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    error_msg = state.get("error", "未知错误")
    logger.error(f"达到最大重试次数，放弃处理。最终错误: {error_msg}")
    
    writer({
        "type": "error",
        "message": f"SQL 生成多次失败，请稍后重试或简化问题。详情: {error_msg}"
    })

    