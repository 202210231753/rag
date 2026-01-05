from typing import List, Set
import math
from chatbot.rag.app.data.models import Item, UserProfile, ExplanationItem

class RankingEngine:
    def apply_hard_filters(self, candidates: List[Item], profile: UserProfile) -> List[Item]:
        """
        执行硬规则，如剔除不匹配的地理位置、不感兴趣的类别。
        """
        filtered = []
        for item in candidates:
            # 检查负面标签
            is_negative = False
            for tag in item.tags:
                if tag in profile.negative_tags:
                    is_negative = True
                    break
            
            if is_negative:
                continue

            # 检查位置（模拟逻辑：如果项目内容提到了不在画像中的位置，排除？）
            # 简化：假设项目标签可能包含位置信息，或者如果不适用则跳过位置逻辑
            # 在此演示中，我们假设如果画像有位置且项目标签明确与其冲突，则过滤
            # (为简洁起见省略复杂的位置逻辑，专注于标签)
            
            filtered.append(item)
        return filtered

    def apply_soft_boosting(self, candidates: List[Item], hot_list: List[str]) -> List[Item]:
        """
        执行软规则，对热门内容进行加权。
        """
        for item in candidates:
            for hot_term in hot_list:
                if hot_term.lower() in item.content.lower():
                    item.score *= 1.2  # 分数提升 20%
                    item.strategy_source = "hot_boosted"
                    break
        
        # 重新排序
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def calculate_mmr(self, candidates: List[Item], lambda_val: float) -> List[Item]:
        """
        执行 MMR 算法平衡相关性与多样性。
        简化的 MMR 实现。
        """
        if not candidates:
            return []

        selected = []
        pool = candidates[:]
        
        while pool:
            best_item = None
            best_mmr_score = -float('inf')
            
            for item in pool:
                # 模拟与查询的相似度（使用 item.score 作为代理）
                relevance = item.score
                
                # 模拟与已选项目的最大相似度
                # 在真实的 MMR 中，这需要向量相似度。
                # 这里我们模拟它：具有相同标签的项目是“相似的”
                max_sim_to_selected = 0.0
                for sel in selected:
                    intersection = len(set(item.tags) & set(sel.tags))
                    if intersection > 0:
                        max_sim_to_selected = max(max_sim_to_selected, 0.5) # 模拟相似度
                
                mmr_score = (lambda_val * relevance) - ((1 - lambda_val) * max_sim_to_selected)
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_item = item
            
            if best_item:
                selected.append(best_item)
                pool.remove(best_item)
            else:
                break
                
        return selected

    def predict_with_strategy_info(self, items: List[Item]) -> List[ExplanationItem]:
        """
        返回带有“策略来源”的结果。
        """
        result = []
        for item in items:
            explanation = "Relevance"
            if item.strategy_source == "hot_boosted":
                explanation = "Hot Content Boost"
            elif item.strategy_source == "curated":
                explanation = "Curated Selection"
            
            result.append(ExplanationItem(item=item, explanation=explanation))
        return result
