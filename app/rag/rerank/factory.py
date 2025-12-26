"""
重排服务配置工厂

提供便捷的重排服务初始化方法
"""

from typing import Optional
from loguru import logger

from app.rag.rerank import (
    RerankService,
    BaseRerankModel,
    TEIRerankModel,
    LocalRerankModel,
    MockRerankModel,
    PersonalizationPolicy,
    PolicyEngine,
)


class RerankConfig:
    """
    重排服务配置

    支持通过环境变量或代码配置重排服务
    """

    # 重排模型类型
    RERANK_MODEL_TYPE = "mock"  # 可选: "tei", "local", "mock"

    # TEI 配置
    TEI_ENDPOINT = "http://localhost:8081"
    TEI_MODEL_NAME = "bge-reranker-base"

    # 本地模型配置
    LOCAL_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # 个性化策略配置
    ENABLE_PERSONALIZATION = True
    INTEREST_BOOST = 0.3
    HISTORY_BOOST = 0.2
    RECENCY_BOOST = 0.1

    # 验证配置
    ENABLE_VALIDATION = True


def create_rerank_model(
    model_type: Optional[str] = None,
) -> BaseRerankModel:
    """
    创建重排模型实例

    Args:
        model_type: 模型类型 ("tei", "local", "mock")

    Returns:
        重排模型实例
    """
    model_type = model_type or RerankConfig.RERANK_MODEL_TYPE

    if model_type == "tei":
        logger.info(
            f"[RerankFactory] 创建 TEI 模型: endpoint={RerankConfig.TEI_ENDPOINT}"
        )
        return TEIRerankModel(
            model_name=RerankConfig.TEI_MODEL_NAME,
            endpoint=RerankConfig.TEI_ENDPOINT,
        )

    elif model_type == "local":
        logger.info(
            f"[RerankFactory] 创建本地模型: model={RerankConfig.LOCAL_MODEL_NAME}"
        )
        return LocalRerankModel(model_name=RerankConfig.LOCAL_MODEL_NAME)

    elif model_type == "mock":
        logger.info("[RerankFactory] 创建 Mock 模型（测试模式）")
        return MockRerankModel()

    else:
        raise ValueError(f"不支持的模型类型: {model_type}")


def create_policy_engine() -> PolicyEngine:
    """
    创建策略引擎

    Returns:
        策略引擎实例
    """
    if RerankConfig.ENABLE_PERSONALIZATION:
        policy = PersonalizationPolicy(
            interest_boost=RerankConfig.INTEREST_BOOST,
            history_boost=RerankConfig.HISTORY_BOOST,
            recency_boost=RerankConfig.RECENCY_BOOST,
        )
        logger.info("[RerankFactory] 创建个性化策略引擎")
    else:
        policy = PersonalizationPolicy(
            interest_boost=0.0, history_boost=0.0, recency_boost=0.0
        )
        logger.info("[RerankFactory] 创建默认策略引擎（无个性化）")

    return PolicyEngine(personalization_policy=policy)


def create_rerank_service(
    model_type: Optional[str] = None,
    enable_personalization: Optional[bool] = None,
) -> RerankService:
    """
    创建重排服务实例

    这是推荐的初始化方式，会自动根据配置创建合适的组件

    Args:
        model_type: 模型类型（可选，默认使用配置）
        enable_personalization: 是否启用个性化（可选）

    Returns:
        重排服务实例

    Example:
        ```python
        # 使用默认配置
        rerank_service = create_rerank_service()

        # 使用 TEI 模型
        rerank_service = create_rerank_service(model_type="tei")

        # 禁用个性化
        rerank_service = create_rerank_service(enable_personalization=False)
        ```
    """
    # 创建重排模型
    rerank_model = create_rerank_model(model_type)

    # 创建策略引擎
    if enable_personalization is False:
        policy_engine = PolicyEngine(
            personalization_policy=PersonalizationPolicy(
                interest_boost=0.0, history_boost=0.0, recency_boost=0.0
            )
        )
    else:
        policy_engine = create_policy_engine()

    # 创建重排服务
    service = RerankService(
        rerank_model=rerank_model,
        policy_engine=policy_engine,
        enable_validation=RerankConfig.ENABLE_VALIDATION,
    )

    logger.info("[RerankFactory] 重排服务创建完成")
    return service


# 便捷函数
def get_rerank_service() -> Optional[RerankService]:
    """
    获取重排服务实例（单例模式）

    Returns:
        重排服务实例，如果配置为禁用则返回 None
    """
    try:
        return create_rerank_service()
    except Exception as e:
        logger.error(f"[RerankFactory] 创建重排服务失败: {e}")
        return None
