"""
中文分词模块：
- 支持两种分词器（jieba / hanlp）切换
- 支持专用词条（自定义词库）增删与持久化
"""

from .manager import TokenizerManager, get_tokenizer_manager

__all__ = ["TokenizerManager", "get_tokenizer_manager"]
