"""
Tokenizer 分词服务

封装 jieba 中文分词
"""

from typing import List
import jieba
from loguru import logger


class TokenizerService:
    """
    中文分词服务

    使用 jieba 进行中文分词
    """

    def __init__(self):
        """初始化分词器"""
        # jieba 首次使用时会自动加载词典
        logger.info("Tokenizer 服务初始化完成")

    async def analyze(self, text: str) -> List[str]:
        """
        文本分词

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        try:
            logger.debug(f"执行文本分词: text_length={len(text)}")

            # jieba 分词（精确模式）
            tokens = list(jieba.cut(text, cut_all=False))

            # 过滤空白 token
            tokens = [t.strip() for t in tokens if t.strip()]

            logger.info(f"分词完成: token_count={len(tokens)}")
            return tokens

        except Exception as e:
            logger.error(f"分词失败: {e}")
            raise

    async def analyze_for_search(self, text: str) -> List[str]:
        """
        搜索模式分词

        使用 jieba 搜索引擎模式，会对长词进行额外切分

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        try:
            logger.debug(f"执行搜索模式分词: text_length={len(text)}")

            # jieba 搜索引擎模式
            tokens = list(jieba.cut_for_search(text))

            # 过滤空白 token
            tokens = [t.strip() for t in tokens if t.strip()]

            logger.info(f"搜索模式分词完成: token_count={len(tokens)}")
            return tokens

        except Exception as e:
            logger.error(f"搜索模式分词失败: {e}")
            raise
