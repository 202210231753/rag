"""
重排模型实现

提供多种重排模型的具体实现，支持策略模式切换
"""

from abc import ABC, abstractmethod
from typing import List
from loguru import logger


class BaseRerankModel(ABC):
    """
    重排模型基类

    定义统一的重排模型接口
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        logger.info(f"[{self.__class__.__name__}] 初始化: model={model_name}")

    @abstractmethod
    async def predict_scores(
        self, query: str, documents: List[str]
    ) -> List[float]:
        """
        预测查询与文档的相关性分数

        Args:
            query: 用户查询
            documents: 文档文本列表

        Returns:
            分数列表（与 documents 顺序一致）
        """
        pass


class TEIRerankModel(BaseRerankModel):
    """
    基于 TEI (Text Embeddings Inference) 的重排模型

    通过 HTTP 接口调用 TEI 部署的 Cross-Encoder 模型
    """

    def __init__(self, model_name: str, endpoint: str):
        """
        初始化 TEI 重排模型

        Args:
            model_name: 模型名称（如 "bge-reranker-base"）
            endpoint: TEI 服务端点（如 "http://reranker-bge:8080"）
        """
        super().__init__(model_name)
        self.endpoint = endpoint.rstrip("/")
        logger.info(f"[TEIRerankModel] endpoint={self.endpoint}")

    async def predict_scores(
        self, query: str, documents: List[str]
    ) -> List[float]:
        """
        调用 TEI 接口进行重排

        Args:
            query: 用户查询
            documents: 文档列表

        Returns:
            分数列表
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.endpoint}/rerank",
                    json={"query": query, "texts": documents},
                )
                response.raise_for_status()
                result = response.json()

                # TEI 返回格式: [{"index": 0, "score": 0.95}, ...]
                # 按 index 排序后提取分数
                sorted_result = sorted(result, key=lambda x: x["index"])
                scores = [item["score"] for item in sorted_result]

                logger.debug(
                    f"[TEIRerankModel] 预测完成: query='{query[:30]}...', "
                    f"docs={len(documents)}, scores={scores[:3]}..."
                )
                return scores

        except httpx.HTTPError as e:
            logger.error(f"[TEIRerankModel] 调用 TEI 失败: {e}")
            # 降级：返回均匀分数
            return [0.5] * len(documents)
        except Exception as e:
            logger.error(f"[TEIRerankModel] 预测失败: {e}")
            return [0.5] * len(documents)


class LocalRerankModel(BaseRerankModel):
    """
    本地加载的重排模型

    使用 sentence-transformers 直接在进程内运行 Cross-Encoder
    适合小规模或没有 GPU 资源的场景
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        初始化本地重排模型

        Args:
            model_name: Hugging Face 模型名称
        """
        super().__init__(model_name)
        try:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(model_name, device="cpu")
            logger.info(f"[LocalRerankModel] 模型加载成功: {model_name}")
        except ImportError:
            logger.error(
                "[LocalRerankModel] 缺少 sentence-transformers 库，请安装: "
                "pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"[LocalRerankModel] 模型加载失败: {e}")
            raise

    async def predict_scores(
        self, query: str, documents: List[str]
    ) -> List[float]:
        """
        本地模型预测

        Args:
            query: 用户查询
            documents: 文档列表

        Returns:
            分数列表
        """
        try:
            # Cross-Encoder 需要 (query, doc) 对
            pairs = [(query, doc) for doc in documents]
            scores = self.model.predict(pairs).tolist()

            logger.debug(
                f"[LocalRerankModel] 预测完成: query='{query[:30]}...', "
                f"docs={len(documents)}, scores={scores[:3]}..."
            )
            return scores

        except Exception as e:
            logger.error(f"[LocalRerankModel] 预测失败: {e}")
            return [0.5] * len(documents)


class MockRerankModel(BaseRerankModel):
    """
    Mock 重排模型

    用于测试和开发，返回模拟分数
    """

    def __init__(self):
        super().__init__("mock-reranker")

    async def predict_scores(
        self, query: str, documents: List[str]
    ) -> List[float]:
        """
        返回模拟分数

        规则：根据文档长度和查询词是否在文档中计算模拟分数
        """
        import random

        scores = []
        for doc in documents:
            base_score = 0.5
            # 如果查询词在文档中，加分
            if query.lower() in doc.lower():
                base_score += 0.3
            # 添加随机扰动
            score = min(1.0, max(0.0, base_score + random.uniform(-0.1, 0.1)))
            scores.append(score)

        logger.debug(
            f"[MockRerankModel] 返回模拟分数: docs={len(documents)}, scores={scores[:3]}..."
        )
        return scores
