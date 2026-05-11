from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DBInfoState, DataAgentState, DataInfoState
from datetime import date, datetime
from app.core.log import logger


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "添加额外上下文信息", "status": "running"})
    dw_mysql_repository = runtime.context['dw_mysql_repository']
    try:
        # 当前的时间信息
        today = datetime.today()
        # 日期
        date = today.strftime("%Y-%m-%d")
        # 星期
        weekday = today.strftime("%A")
        # 季度 需要计算 
        quarter = f"Q{(today.month - 1) // 3 + 1}"

        date_info = DataInfoState(date=date, weekday=weekday, quarter=quarter)
        # 数据仓库环境信息
        db = await dw_mysql_repository.get_db_info()
        db_info=DBInfoState(**db)
        writer({"type": "progress", "step": "添加额外上下文信息", "status": "success"})
        logger.info(f"获取数据仓库环境信息：{db_info}")
        logger.info(f"获取日期信息：{date_info}")
        return {'date_info': date_info, 'db_info': db_info}
    except Exception as e:
        writer({"type": "progress", "step": "添加额外上下文信息", "status": "error"})
        logger.error(f"添加上下文失败:{str(e)}")
        raise





    