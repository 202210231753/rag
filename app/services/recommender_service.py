from typing import List
from app.data.models import Item, ExplanationItem
from app.core.user_profile_manager import UserProfileManager
from app.core.ranking_engine import RankingEngine
from app.infra.config import ConfigCenter
from app.infra.ai_client import AIModelClient
from app.infra.vector_db import VectorDBClient

class ContentRecommenderService:
    def __init__(self, 
                 profile_manager: UserProfileManager,
                 ranking_engine: RankingEngine,
                 config_center: ConfigCenter,
                 ai_client: AIModelClient,
                 vector_db: VectorDBClient):
        self.profile_manager = profile_manager
        self.ranking_engine = ranking_engine
        self.config_center = config_center
        self.ai_client = ai_client
        self.vector_db = vector_db

    def recommend(self, user_id: str, trace_id: str) -> List[ExplanationItem]:
        """
        主入口。新增 traceId 参数，串联全过程。
        """
        # 1. 获取用户画像
        profile = self.profile_manager.store.load(user_id)
        
        # 2. 混合检索
        # 基于兴趣构建用户向量（模拟：使用最新的兴趣）
        user_vector_text = " ".join(profile.static_tags + profile.dynamic_interests)
        if not user_vector_text:
            user_vector_text = "general"
        
        user_vector = self.ai_client.get_embedding(user_vector_text)
        candidates = self.hybrid_retrieval(user_vector)
        
        # 3. 硬过滤（人工干预：地理位置，负面分类）
        filtered_candidates = self.ranking_engine.apply_hard_filters(candidates, profile)
        
        # 4. 软提升（人工干预：热搜）
        hot_list = self.config_center.get_hot_search_config()
        boosted_candidates = self.ranking_engine.apply_soft_boosting(filtered_candidates, hot_list)
        
        # 5. MMR 多样性（可配置策略）
        experiment_config = self.config_center.get_experiment_config(user_id)
        final_list = self.ranking_engine.calculate_mmr(
            boosted_candidates, 
            lambda_val=experiment_config.diversity_lambda
        )
        
        # 6. 解释和追踪
        results = self.ranking_engine.predict_with_strategy_info(final_list)
        
        print(f"[ContentRecommender] TraceID: {trace_id}, User: {user_id}, Returned: {len(results)} items")
        return results

    def hybrid_retrieval(self, user_vector: List[float]) -> List[Item]:
        """
        维持原有逻辑，结合用户静态标签和动态兴趣向量进行召回。
        """
        # 1. 向量搜索 (只搜内容，不搜查询词)
        items = self.vector_db.search_ann(user_vector, topk=50, filter_type="content")
        return items


class QueryRecommenderService:
    def __init__(self, 
                 config_center: ConfigCenter,
                 ai_client: AIModelClient,
                 vector_db: VectorDBClient):
        self.config_center = config_center
        self.ai_client = ai_client
        self.vector_db = vector_db

    def recommend_next_queries(self, current_query: str, trace_id: str) -> List[str]:
        """
        主入口。新增 traceId 用于验证。
        """
        # 1. 算法检索（语义相似度）
        vector = self.ai_client.get_embedding(current_query)
        
        # 2. 从向量数据库获取相似查询 (只搜查询词)
        algo_items = self.vector_db.search_ann(vector, topk=5, filter_type="query")
        algo_results = [item.content for item in algo_items] # 使用项目内容作为建议查询
        
        # 3. 获取配置的来源
        hot_results = self.config_center.get_hot_search_config()
        curated_results = self.config_center.get_curated_queries()
        
        # 4. 填充槽位
        final_queries = self.fill_slots(algo_results, hot_results, curated_results)
        
        print(f"[QueryRecommender] TraceID: {trace_id}, Query: {current_query}, Recommended: {final_queries}")
        return final_queries

    def fill_slots(self, algo_results: List[str], hot_results: List[str], curated_results: List[str]) -> List[str]:
        """
        槽位填充逻辑。新增 curatedResults 支持精选优质内容。
        策略:
        槽位 0: 精选（如果有）
        槽位 1: 算法最佳匹配
        槽位 2: 热门
        槽位 3+: 混合剩余算法结果
        """
        slots = []
        
        # 1. 精选优先
        if curated_results:
            slots.append(curated_results[0]) # 获取第一个精选
            
        # 2. 算法最佳匹配
        if algo_results:
            # 避免重复
            for q in algo_results:
                if q not in slots:
                    slots.append(q)
                    break
        
        # 3. 热门查询
        if hot_results:
            for q in hot_results:
                if q not in slots:
                    slots.append(q)
                    break
                    
        # 4. 从算法填充剩余部分
        for q in algo_results:
            if len(slots) >= 5:
                break
            if q not in slots:
                slots.append(q)
                
        return slots
