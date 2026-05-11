import uuid

from fastapi import FastAPI, Request
from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_ctx_var

app = FastAPI(lifespan=lifespan)  #生命周期
app.include_router(query_router)  #APIrouter

# 添加中间件，在每个请求中生成唯一的request_id
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # 调用路径函数之前  
    request_id=uuid.uuid4()
    request_id_ctx_var.set(str(request_id))
    # 调用路径函数  业务逻辑
    response = await call_next(request)
    # 调用路径函数之后
    return response
