from contextvars import ContextVar
# 定义一个变量，默认值为 "1"
request_id_ctx_var = ContextVar("request_id", default="recall_test")