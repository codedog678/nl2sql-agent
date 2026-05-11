# SelfOne — 基于 LangGraph 的智能数据查询 Agent

## 项目简介

SelfOne 是一个基于 LangGraph 构建的智能数据查询 Agent 系统。用户以自然语言提问，系统自动完成关键词抽取、元数据召回（字段/指标/取值）、信息过滤与合并、SQL 生成与校验、SQL 执行等全流程，最终将查询结果流式返回给前端。

## 系统架构

```
用户自然语言查询
       │
       ▼
  ┌─────────────┐
  │ FastAPI 接口  │  POST /api/query  (SSE 流式响应)
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────┐
  │           LangGraph Agent 工作流          │
  │                                          │
  │  extract_keywords ──┬─► recall_column    │
  │                     ├─► recall_value     │
  │                     └─► recall_metric    │
  │                            │             │
  │              merge_retrieved_info        │
  │                   ┌────┴────┐            │
  │           filter_table  filter_metric    │
  │                   └────┬────┘            │
  │              add_extra_context           │
  │                      │                   │
  │              generate_sql                │
  │                      │                   │
  │              validate_sql ◄─────────┐    │
  │              ┌───┴───┐             │    │
  │         成功 │       │ 失败(≤2次)   │    │
  │              ▼       ▼              │    │
  │       execute_sql  correct_sql ─────┘    │
  │              │       │                   │
  │              │   失败(>2次)              │
  │              │       ▼                   │
  │              │  error_handler            │
  └──────────────┼──────┼───────────────────┘
                 │      │
                 ▼      ▼
           查询结果 (SSE 流式返回)
```

## 核心工作流节点说明

| 节点                     | 功能                                           |
| ------------------------ | ---------------------------------------------- |
| `extract_keywords`     | 使用 Jieba 分词从用户查询中抽取关键词          |
| `recall_column`        | 基于关键词向量检索 Qdrant，召回相关字段信息    |
| `recall_value`         | 基于关键词全文检索 Elasticsearch，召回字段取值 |
| `recall_metric`        | 基于关键词向量检索 Qdrant，召回相关指标信息    |
| `merge_retrieved_info` | 合并三类召回信息，按表分组字段，强制补充主外键 |
| `filter_table`         | LLM 过滤无关表和字段，精简上下文               |
| `filter_metric`        | LLM 过滤无关指标，精简上下文                   |
| `add_extra_context`    | 补充日期信息和数据库方言信息                   |
| `generate_sql`         | LLM 生成 SQL                                   |
| `validate_sql`         | 在数据仓库中预执行 SQL 验证语法正确性          |
| `correct_sql`          | SQL 校验失败时 LLM 修正 SQL（最多重试 2 次）   |
| `execute_sql`          | 执行验证通过的 SQL，返回查询结果               |
| `error_handler`        | 超过最大重试次数后的熔断处理                   |

## 技术栈

| 类别       | 技术                                           |
| ---------- | ---------------------------------------------- |
| Web 框架   | FastAPI + Uvicorn                              |
| Agent 框架 | LangGraph                                      |
| LLM        | 阿里百炼（qwen-coder-plus-latest / qwen3-max） |
| Embedding  | 阿里百炼 DashScope（text-embedding-v2）        |
| 向量数据库 | Qdrant                                         |
| 搜索引擎   | Elasticsearch（含 IK 中文分词插件）            |
| 关系数据库 | MySQL 8.0（元数据库 + 数据仓库）               |
| 分词       | Jieba                                          |
| 配置管理   | OmegaConf + YAML                               |
| 日志       | Loguru                                         |
| 容器化     | Docker Compose                                 |

## 项目结构

```
selfone/
├── app/
│   ├── agent/                  # LangGraph Agent 核心
│   │   ├── nodes/              # 工作流节点
│   │   ├── context.py          # Agent 上下文定义
│   │   ├── graph.py            # LangGraph 图构建与编译
│   │   ├── llm.py              # LLM 初始化
│   │   └── state.py            # Agent 状态定义
│   ├── api/                    # FastAPI 接口层
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── dependencies.py     # 依赖注入
│   │   └── lifespan.py         # 应用生命周期管理
│   ├── clients/                # 外部服务客户端管理
│   ├── conf/                   # 配置加载
│   ├── core/                   # 核心工具（日志、请求上下文）
│   ├── entities/               # 数据实体
│   ├── models/                 # ORM 模型
│   ├── prompt/                 # Prompt 模板加载
│   ├── repositories/           # 数据访问层
│   │   ├── es/                 # Elasticsearch 仓库
│   │   ├── mysql/              # MySQL 仓库（meta + dw）
│   │   └── qdrant/             # Qdrant 仓库
│   ├── scripts/                # 脚本工具
│   └── services/               # 业务服务层
├── conf/                       # 配置文件
│   ├── app_config.yaml         # 应用配置（需本地创建，含敏感信息）
│   └── meta_config.yaml        # 元数据配置（表/指标定义）
├── docker/                     # Docker 部署
│   ├── docker-compose.yaml
│   ├── mysql/                  # MySQL 初始化 SQL
│   ├── elasticsearch/          # ES + IK 分词插件
│   └── embedding/              # 本地 Embedding 模型
├── prompts/                    # Prompt 模板文件
├── main.py                     # 应用入口
└── pyproject.toml              # 项目依赖
```

## 数据模型

项目采用经典的星型模型（Star Schema）：

- **维度表**：`dim_region`（地区）、`dim_customer`（客户）、`dim_product`（商品）、`dim_date`（时间）
- **事实表**：`fact_order`（订单）
- **指标定义**：GMV（成交总额）、AOV（平均订单金额）等

## 快速开始

### 环境要求

- Python >= 3.13
- Docker & Docker Compose

### 1. 启动基础设施

```bash
cd docker
docker-compose up -d
```

| 服务          | 端口        | 说明                |
| ------------- | ----------- | ------------------- |
| MySQL         | 3306        | 元数据库 + 数据仓库 |
| Elasticsearch | 9200        | 全文检索引擎        |
| Kibana        | 7000        | ES 可视化面板       |
| Qdrant        | 6333 / 6334 | 向量数据库          |

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置

在 `conf/` 目录下创建 `app_config.yaml`，参考以下模板填入实际值：

```yaml
logging:
  file:
    enable: true
    level: INFO
    path: logs
    rotation: "10 MB"
    retention: "7 days"
  console:
    enable: true
    level: INFO

db_meta:
  host: localhost
  port: 3306
  user: <your_user>
  password: <your_password>
  database: meta

db_dw:
  host: localhost
  port: 3306
  user: <your_user>
  password: <your_password>
  database: dw

qdrant:
  host: localhost
  port: 6333
  embedding_size: 1024

embedding:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: <your_dashscope_api_key>
  model: "text-embedding-v2"

es:
  host: localhost
  port: 9200
  index_name: data_agent

llm_coder:
  model_name: qwen-coder-plus-latest
  api_key: <your_dashscope_api_key>
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1

llm_text:
  model_name: qwen3-max
  api_key: <your_dashscope_api_key>
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
```

同时设置环境变量以覆盖敏感配置：

```powershell
$env:DB_META_PASSWORD = "<your_password>"
$env:DB_DW_PASSWORD = "<your_password>"
$env:EMBEDDING_API_KEY = "<your_api_key>"
$env:LLM_CODER_API_KEY = "<your_api_key>"
$env:LLM_TEXT_API_KEY = "<your_api_key>"
```

### 4. 构建元数据知识库

```bash
python -m app.scripts.build_meta_knowledge
```

### 5. 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 6. 调用接口

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "华东地区各省份的销售额是多少"}'
```

## API 接口

### POST /api/query

**请求体：**

```json
{
  "query": "自然语言查询问题"
}
```

**响应格式（SSE）：**

```
data: {"type": "progress", "step": "抽取关键字", "status": "running"}
data: {"type": "progress", "step": "抽取关键字", "status": "success"}
data: {"type": "progress", "step": "召回字段", "status": "running"}
...
data: {"type": "result", "data": [...]}
```

## 关键设计

### 多路召回

系统采用三路并行召回策略：

1. **字段召回**（Qdrant 向量检索）— 基于语义相似度匹配字段
2. **取值召回**（Elasticsearch 全文检索）— 基于关键词匹配字段取值
3. **指标召回**（Qdrant 向量检索）— 基于语义相似度匹配指标

### SQL 校验与熔断

- 生成的 SQL 先在数据仓库中预执行验证
- 验证失败时 LLM 根据错误信息修正 SQL，修正后重新验证（循环）
- 最多修正 2 次，均失败后触发熔断

### 实时进度反馈

每个工作流节点通过 LangGraph 的 `stream_writer` 向前端推送当前处理进度，用户可实时感知每一步状态。
