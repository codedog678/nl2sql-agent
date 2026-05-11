from pathlib import Path

from omegaconf import OmegaConf
#找到当前文件所在的目录
#__file__

#利用Path 处理路径问题 重写了除法/操作符 直接当做路径分隔符
#Path(__file__).parent.parent.parent/conf/app_config.yaml
#找到当前文件所在的目录的祖先目录（也就是项目根目录）parents里面传0就是当前目录，传1就是父目录，传2就是祖父目录
config_path=Path(__file__).parents[2]/conf/app_config_test.yaml

@dataclass
class AppConfig:
    name:str
    id:int
schema=OmegaConf.structured(AppConfig)   #类型结构
conf=OmegaConf.load(config_path)   #类型内容
OmegaConf.merge(schema,conf)   #合并类型结构和内容  又有类型检查又有内容了
app_conf:AppConfig=OmegaConf.to_object(conf)   #将 OmegaConf 对象转换为普通的 dataclass 对象

#print(conf['name'])    不如配置类对象 conf.name访问
# OmegaConf.structured() 可以将一个 dataclass 转换为 OmegaConf 对象，使其支持点访问和类型检查。
'''
from dataclasses import dataclass
@dataclass
class MyConfig:
    port: int = 80
    host: str = "localhost"
# For strict typing purposes, prefer OmegaConf.structured() when creating structured configs
conf = OmegaConf.structured(MyConfig)
print(OmegaConf.to_object(conf).port) 输出 80

'''
