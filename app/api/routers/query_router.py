#和查询相关的接口挂载在这里
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService

query_router = APIRouter()

@query_router.post('/api/query')  #前端请求路径 请求放在请求体
#依赖项的真实类型 
async def query_handler(query:QuerySchema,query_service:Annotated[QueryService, Depends(get_query_service)]):
    return StreamingResponse(query_service.query(query.query), media_type="text/event-stream")
# 这里的query_service是QueryService的实例化对象，它是依赖注入的对象
#query.query是前端请求体query:QuerySchema中的query参数
