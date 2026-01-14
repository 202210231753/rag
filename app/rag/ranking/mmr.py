"""
MMR (最大边际相关性) 算法实现

用于在保持相关性的同时，增加搜索结果的多样性。
"""

from typing import List
from loguru import logger


def calculate_similarity(item1, item2) -> float:
    """
    计算两个文档的相似度（基于元数据）
    
    Args:
        item1, item2: 搜索结果项（需要有 metadata 属性）
    
    Returns:
        相似度分数 (0-1)，越高表示越相似
    """
    score = 0.0

    # 获取元数据
    meta1 = getattr(item1, "metadata", {}) or {}
    meta2 = getattr(item2, "metadata", {}) or {}

    # 同类别 +0.6
    if meta1.get("category") == meta2.get("category"):
        score += 0.6

    # 同来源 +0.4
    if meta1.get("source") == meta2.get("source"):
        score += 0.4

    return min(score, 1.0)  # 归一化到 [0, 1]


def mmr_rerank(items: List, lambda_param: float = 0.5, top_n: int = 10) -> List:
    """
    使用 MMR 算法重新排序，增加多样性
    
    算法公式:
        MMR = argmax[λ * Sim(D, Q) - (1-λ) * max Sim(D, Di)]
              D∈R\S
    
    参数说明:
        - λ=1: 只看相关性（不考虑多样性）
        - λ=0: 只看多样性（不考虑相关性）
        - λ=0.5: 平衡相关性和多样性
    
    Args:
        items: 已排序的搜索结果列表（需要有 final_score 属性）
        lambda_param: 平衡参数 (0-1)
        top_n: 返回前N个结果
    
    Returns:
        重新排序后的结果列表
    """
    if not items:
        return []

    if lambda_param < 0 or lambda_param > 1:
        logger.warning(f"lambda_param={lambda_param} 超出范围 [0,1]，使用默认值 0.5")
        lambda_param = 0.5

    selected = []  # 已选文档
    remaining = items.copy()  # 候选文档

    logger.debug(f"开始 MMR 重排: 候选数={len(remaining)}, lambda={lambda_param}, top_n={top_n}")

    while len(selected) < top_n and remaining:
        best_score = -999999
        best_item = None
        best_idx = None

        for idx, item in enumerate(remaining):
            # 相关性分数（使用重排后的分数）
            relevance = getattr(item, "final_score", 0.0)

            # 多样性惩罚（与已选文档最相似的那个）
            max_similarity = 0.0
            if selected:
                for selected_item in selected:
                    sim = calculate_similarity(item, selected_item)
                    max_similarity = max(max_similarity, sim)

            # 计算 MMR 分数
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

            if mmr_score > best_score:
                best_score = mmr_score
                best_item = item
                best_idx = idx

        if best_item is None:
            break

        # 添加到结果，并从候选中移除
        selected.append(best_item)
        remaining.pop(best_idx)

    logger.debug(f"MMR 重排完成: 输出数={len(selected)}")
    return selected
