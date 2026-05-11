from app.conf.app_config import DBConfig,app_config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine,AsyncEngine  
import asyncio
from typing import Optional

from sqlalchemy import text

class MySQLClientManager:
    def __init__(self,config:DBConfig):
        self.engine: AsyncEngine = None
        self.config = config
        self.session_factory = None
    def _get_url(self):
        return f'mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4'
    def init(self):
        self.engine=create_async_engine(url=self._get_url(),
                                        pool_size=10,
                                        pool_pre_ping=True)#创建异步引擎
        self.session_factory=async_sessionmaker(self.engine, expire_on_commit=False,autoflush=True)#创建异步会话工厂
    async def close(self):
        await self.engine.dispose()

mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)