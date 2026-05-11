from langgraph.runtime import Runtime
from app.agent.context import DataAgentContext
from app.agent.state import ColumnInfoState, DataAgentState, MetricInfoState, TableInfoState
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.core.log import logger
async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "合并召回信息", "status": "running"})

    # 已召回信息
    retrieved_column_infos:list[ColumnInfo] = state['retrieved_column_infos']
    retrieved_metric_infos:list[MetricInfo] = state['retrieved_metric_infos']
    retrieved_value_infos:list[ValueInfo] = state['retrieved_value_infos']

    # 获取所需依赖 元数据知识库  
    meta_mysql_repository = runtime.context['meta_mysql_repository']
    try:
        # 一、处理表信息
        #id作为key 值是字段本身信息  自己可以获得Id 转成一个字典
        retrieved_columns_map: dict[str, ColumnInfo] = {retrieved_column_info.id: retrieved_column_info for retrieved_column_info in retrieved_column_infos}
        #1.将指标信息的相关字段信息添加到字段信息中 就是加入到retrieved_column_infos中
        for metric_info in retrieved_metric_infos:
            for column_id in metric_info.relevant_columns:  #指标的相关字段
                #要根据字段id找到完整的列信息 去meta中获取完整的字段信息
                #为了防止数据重复 要判断是否已经存在
                if column_id not in retrieved_columns_map:
                    colunmn_info:ColumnInfo=await meta_mysql_repository.get_column_info_by_id(column_id)
                    retrieved_columns_map[column_id] = colunmn_info
        
        #2.将字段取值添加到其所属字段的examples中
        for value_info in retrieved_value_infos:
            value=value_info.value
            column_id=value_info.column_id
            #1.字段是否在  2.example是否已经有这个值
            if not column_id in retrieved_columns_map:
                colunmn_info:ColumnInfo=await meta_mysql_repository.get_column_info_by_id(column_id)
                retrieved_columns_map[column_id] = colunmn_info
            #确保字段存在完成
            if value not in retrieved_columns_map[column_id].examples:
                retrieved_columns_map[column_id].examples.append(value)
        
        #3.按照表对字段信息进行分组，整理成目标格式 当前是没有添加强制加主外键的内容  下面进行补充
        #key是table_id  value是字段信息列表 把属于同一张表的字段信息放到一起
        table_to_columns_map: dict[str, list[ColumnInfo]] = {}
        #ColumnInfo里有一个字段是table_id 所以可以根据这个字段进行分组
        for column_info in retrieved_columns_map.values():
            table_id = column_info.table_id
            if column_info.table_id not in table_to_columns_map:
                table_to_columns_map[table_id] = []
            table_to_columns_map[table_id].append(column_info)#把不同字段分到对应的表中
        #--------------------强制为每个表添加主外键字段--------------------
        for table_id in table_to_columns_map.keys():
        # 1. 直接去元数据库查这个表定义的所有主键和外键字段
            key_columns: list[ColumnInfo] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)
            
            # 2. 主外键字段可能召回 得检查是否已经存在到columns中 先取出当前已经有的current_column_ids
            current_column_ids = [col.id for col in table_to_columns_map[table_id]]
            
            for key_column in key_columns:
                if key_column.id not in current_column_ids:
                    # 3. 只要没在里面，不管搜没搜到，强行塞进去
                    table_to_columns_map[table_id].append(key_column)
    # ----------------------------------------------
        
        
        #整理成目标格式  
        table_infos : list[TableInfoState] = []
        for table_id, columns in table_to_columns_map.items():
            # 1. 根据表ID从 meta 数据库查询该表的完整信息（名称、角色、描述）
            table_info:TableInfo=await meta_mysql_repository.get_table_info_by_id(table_id)
             # 2. 将当前表下的每个 ColumnInfo 对象转换为 ColumnInfoState
             #  ColumnInfoState 只保留大模型需要的字段（去掉一些内部字段如 id, table_id）
            columns=[ColumnInfoState(
                name=column_info.name,
                type=column_info.type,
                role=column_info.role,
                examples=column_info.examples,
                description=column_info.description,
                alias=column_info.alias) 
                for column_info in columns]
            table_info_state=TableInfoState(
                name = table_info.name,
                role=table_info.role,
                description= table_info.description,
                columns=columns)
            table_infos.append(table_info_state)

        

            # 二、处理指标信息
        #metric_infos:list[MetricInfoState] = []  全部传入就可以
        metric_infos: list[MetricInfoState] = [
                MetricInfoState(name=metric_info.name, description=metric_info.description,
                                relevant_columns=metric_info.relevant_columns, alias=metric_info.alias)
                for metric_info in retrieved_metric_infos]
        writer({"type": "progress", "step": "合并召回信息", "status": "success"})
        logger.info(
            f"合并召回信息: 表信息-{[table_info['name'] for table_info in table_infos]},指标信息-{[metric_info['name'] for metric_info in metric_infos]}")
        return {
            'table_infos': table_infos,
            'metric_infos': metric_infos
        }
    except Exception as e:
        writer({"type": "progress", "step": "合并召回信息", "status": "error"})
        logger.error(f"合并召回信息失败: {str(e)}")
        raise