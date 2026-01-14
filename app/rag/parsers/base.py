from abc import ABC, abstractmethod
from typing import Any, List, Dict

class BaseParser(ABC):
    """解析器基类"""
    
    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        解析文件
        :param file_path: 文件绝对路径
        :return: {
            "content": "Markdown格式的文本内容",
            "images": ["图片路径1", "图片路径2"],
            "meta": {"title": "...", "author": "..."}
        }
        """
        pass
