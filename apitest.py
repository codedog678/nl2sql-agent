# # 1. 导入 FastAPI 类
# from fastapi import FastAPI

# # 2. 创建一个“应用实例”。这就像是你的 Agent 的大脑，所有的路由都注册在这里。
# app = FastAPI()

# # 3. 定义一个“路径操作装饰器”。
# # @app 代表这个实例，.get 代表 HTTP 的 GET 请求（用于获取数据）
# # "/" 代表网站的根目录，比如 http://127.0.0.1:8000/
# @app.get("/")
# def read_root():
#     # 4. 函数返回的内容会自动被转化为 JSON 格式。
#     return {"message": "你好，这是我的第一个 FastAPI 接口！"}
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


async def fake_video_streamer():
    for i in range(10):
        yield b"some fake video bytes"


@app.get("/")
async def main():
    return StreamingResponse(fake_video_streamer())