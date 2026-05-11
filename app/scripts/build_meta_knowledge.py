# import sys
# print(sys.path)  #打印出一系列路径，告诉Python解释器在哪里寻找模块和包
# #怎么解决找不到包的问题：所执行脚本所在的目录一定会在sys.path中，但是app.core.log不在当前目录下，所以需要把app所在的目录添加到sys.path中
# #把app所在的目录添加到sys.path中
# sys.path.append(r'E:\5.study\5.project\selfone')  #替换为你的app所在的目录
# print(sys.path)
#另外一种解决方法 在命令行中用模块的方式执行脚本：python -m app.scripts.build_meta_knowledge 即可
import sys
import asyncio,argparse
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueEsRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledegeService
from app.clients.mysql_client_manaager import mysql_client_manager,dw_mysql_client_manager

async def build(config_path=None):#异步 访问mysql qdrant es 得异步
    '''这里在实际项目中实际调用service 业务主服务'''
    mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    async with mysql_client_manager.session_factory() as meta_session,dw_mysql_client_manager.session_factory() as dw_session:
        #这里需要传入一个session 但是session的创建需要用到mysql_client_manager 这个组件，所以这里
     # 需要先初始化mysql_client_manager 然后再创建session 最后把session传入MetaMySQLRepository中
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)#不需要传入session qdrant客户端不需要session
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)#和column_qdrant_repository公用同一个client对象
        valuse_es_repository = ValueEsRepository(es_client_manager.client)
        meta_knowledge_service = MetaKnowledegeService(meta_mysql_repository=meta_mysql_repository,
                                                       dw_mysql_repository=dw_mysql_repository,
                                                       column_qdrant_repository=column_qdrant_repository,
                                                       embedding_client=embedding_client_manager.client,
                                                       value_es_repository=valuse_es_repository,
                                                       metric_qdrant_repository=metric_qdrant_repository
            
                                                       )
         #把repository传入service中 因为service需要调用repository的方法来访问数据库
         #最后调用service的build方法来构建元知识库 这个方法是异步的 所以需要await
         #两个数据库 所以是两个repository 
        await meta_knowledge_service.build(config_path)

    #填充业务逻辑
    #使用自己定义好的logger组件
    # print(config_path)
    # logger.info('building meta knowledge...')#日志记录
    await dw_mysql_client_manager.close()#关闭dw mysql连接
    await mysql_client_manager.close()#关闭meta mysql连接
    await qdrant_client_manager.close()#关闭qdrant连接
    await es_client_manager.close()#关闭es连接

if __name__ == "__main__":
    #sys.argv[0] 是当前脚本的路径，sys.argv[1:] 是传递给脚本的参数列表 sys.argv是全部参数列表
    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--config')
    args = parser.parse_args()
    config_path = args.config 

    asyncio.run(build(config_path)) 