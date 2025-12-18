# 依赖注入（如获取 DB 会话、SearchGateway 等）
from app.core.database import SessionLocal
from app.rag.search_gateway import SearchGateway
from app.rag.clients.milvus_client import VectorDBClient
from app.rag.clients.es_client import SearchEngineClient
from app.services.embedding_service import EmbeddingService
from app.services.tokenizer_service import TokenizerService
from app.rag.strategies import VectorRecallStrategy, KeywordRecallStrategy
from app.rag.fusion import RRFMergeImpl
from loguru import logger
from functools import lru_cache


# ========================================
# 数据库会话依赖注入
# ========================================
def get_db():
    """
    获取数据库会话

    这是一个生成器函数
    """
    db = SessionLocal()  # 1. 建立连接
    try:
        yield db  # 2. 把连接"借"给接口用（暂停在这里）
    finally:
        db.close()  # 3. 等接口用完了，自动回来执行这一行，关闭连接


# ========================================
# SearchGateway 依赖注入（单例模式）
# ========================================
@lru_cache()
def get_search_gateway() -> SearchGateway:
    """
    获取 SearchGateway 实例（单例）

    使用 lru_cache 确保整个应用生命周期内只创建一次实例

    Returns:
        SearchGateway 实例
    """
    try:
        logger.info("正在初始化 SearchGateway...")

        # 1. 创建基础设施客户端
        milvus_client = VectorDBClient(collection_name="documents")
        es_client = SearchEngineClient()
        logger.info("基础设施客户端创建完成")

        # 2. 创建工具服务
        embedding_service = EmbeddingService()
        tokenizer_service = TokenizerService()
        logger.info("工具服务创建完成")

        # 3. 创建召回策略
        vector_strategy = VectorRecallStrategy(milvus_client)
        keyword_strategy = KeywordRecallStrategy(es_client)
        recall_strategies = [vector_strategy, keyword_strategy]
        logger.info(f"召回策略创建完成: {len(recall_strategies)} 个策略")

        # 4. 创建融合服务
        fusion_service = RRFMergeImpl()
        logger.info("融合服务创建完成")

        # 5. 创建 SearchGateway
        gateway = SearchGateway(
            embedding_service=embedding_service,
            tokenizer_service=tokenizer_service,
            recall_strategies=recall_strategies,
            fusion_service=fusion_service,
            rerank_service=None,  # 重排服务暂不启用
        )

        logger.info("SearchGateway 初始化成功")
        return gateway

    except Exception as e:
        logger.error(f"初始化 SearchGateway 失败: {e}")
        raise
