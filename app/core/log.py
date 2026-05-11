import sys
from pathlib import Path
from loguru import logger
from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var

log_format = (
    "<magenta>request_id - {extra[request_id]}</magenta> | " 
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)#id 时间 级别（字符个数不超过8） 模块名 函数名 行号 日志内容

# 注入request_id到日志记录中
def inject_request_id(record):
    request_id = request_id_ctx_var.get()
    record["extra"]["request_id"] = request_id

logger.remove()  #移除默认配置

# 给日志打补丁，使其支持注入request_id
logger = logger.patch(inject_request_id) 
if app_config.logging.console.enable:#控制台可以配置的话 sink是输出目的地，level是日志级别，format是日志格式
    logger.add(sink=sys.stdout, level=app_config.logging.console.level, format=log_format) #添加配置
if app_config.logging.file.enable:
    path = Path(app_config.logging.file.path)
    path.mkdir(parents=True, exist_ok=True)   #创建目录，parents=True表示如果父目录不存在也创建，exist_ok=True表示如果目录已经存在就不报错
    logger.add(
        sink=path / "app.log",
        level=app_config.logging.file.level,
        format=log_format,
        rotation=app_config.logging.file.rotation,
        retention=app_config.logging.file.retention,
        encoding="utf-8"
)
