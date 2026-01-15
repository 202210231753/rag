from typing import List, Dict
from app.data.models import ExperimentParams

class ConfigCenter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigCenter, cls).__new__(cls)
            # 模拟配置数据
            cls._instance.hot_searches = ["DeepSeek", "RAG Optimization", "Python AsyncIO"]
            cls._instance.diversity_lambda = 0.5
            cls._instance.curated_queries = ["Official Tutorial", "Best Practices"]
            cls._instance.experiments = {
                "group_A": ExperimentParams(diversity_lambda=0.5, enable_curated=True),
                "group_B": ExperimentParams(diversity_lambda=0.8, enable_curated=False)
            }
        return cls._instance

    def get_hot_search_config(self) -> List[str]:
        return self.hot_searches

    def get_diversity_lambda(self) -> float:
        return self.diversity_lambda

    def get_curated_queries(self) -> List[str]:
        return self.curated_queries

    def get_experiment_config(self, user_id: str) -> ExperimentParams:
        # 简单的哈希一致性模拟用于 AB 测试
        if hash(user_id) % 2 == 0:
            return self.experiments["group_A"]
        return self.experiments["group_B"]
