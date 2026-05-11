from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
import jieba.analyse
from app.core.log import logger

async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "抽取关键字", "status": "running"})
    
    query=state['query']
    # 调用语言模型抽取关键词 用Jieba分词 
    # 对查询进行分词，只提取指定词性的词
    allow_pos = (
        "n",  # 名词: 数据、服务器、表格
        "nr",  # 人名: 张三、李四
        "ns",  # 地名: 北京、上海
        "nt",  # 机构团体名: 政府、学校、某公司
        "nz",  # 其他专有名词: Unicode、哈希算法、诺贝尔奖
        "v",  # 动词: 运行、开发
        "vn",  # 名动词: 工作、研究
        "a",  # 形容词: 美丽、快速
        "an",  # 名形词: 难度、合法性、复杂度
        "eng",  # 英文
        "i",  # 成语
        "l",  # 常用固定短语
    )

    keywords = jieba.analyse.extract_tags(query, topK=10, allowPOS=allow_pos)  #keywords为列表形式
    #为了防止分词丢失语义 将原始句子不做分词append到keywords列表中
    #keywords.append(query)  #这样写有风险，万一query分词后和原来一样，会导致重复 所以进行去重写法
    keywords = list(set(keywords + [query]))#列表相加 转为set去重在转为列表
    writer({"type": "progress", "step": "抽取关键字", "status": "success"})
    logger.info(f"抽取关键词{keywords}")
    return {'keywords':keywords}

     

