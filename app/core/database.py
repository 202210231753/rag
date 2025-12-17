# 数据库连接池生成器
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 1. 加载环境变量 (.env)
load_dotenv()

# 2. 从环境变量读取配置 (如果没有读取到，后面是默认值)
# 注意：如果你是在 Docker 里跑，DB_SERVER 应该是 'mysql_db' (取决于 docker-compose 服务名)
# 如果是在本地跑 uvicorn，DB_SERVER 应该是 'localhost'
USER = os.getenv("DB_USER", "rag_user")
PASSWORD = os.getenv("DB_PASSWORD", "rag_password")
SERVER = os.getenv("DB_SERVER", "localhost")
PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "rag_data")

# 3. 组装 MySQL 连接字符串
# 格式: mysql+pymysql://用户名:密码@地址:端口/数据库名
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{SERVER}:{PORT}/{DB_NAME}"

# 4. 创建数据库引擎 (Engine)
# pool_recycle=3600: MySQL 默认会断开空闲 8 小时的连接，这里设置每 1 小时回收重连，防止报错
# pool_pre_ping=True: 每次从池子里拿连接前，先 ping 一下数据库，确保连接是活的
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600,
    pool_pre_ping=True
)

# 5. ✅ 定义 SessionLocal (这就是你报错缺少的那个对象)
# 这是一个“工厂类”，每次有新请求进来，deps.py 就会调用它产生一个新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 6. 定义 Base 类
# 所有的 Model (比如 Document) 都要继承这个类
Base = declarative_base()