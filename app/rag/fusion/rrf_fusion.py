"""
RRF 融合算法实现

实现 Reciprocal Rank Fusion (RRF) 融合算法
"""

from typing import List, Dict
from collections import defaultdict
from loguru import logger

from app.rag.fusion.base import IFusionService
from app.rag.models.candidate import CandidateItem


class RRFMergeImpl(IFusionService):
    """
    RRF 融合算法实现

    使用 Reciprocal Rank Fusion 公式合并多路召回结果
    """

    def rrf_merge(
        self,
        candidate_lists: List[List[CandidateItem]],
        top_n: int = 50,
        k: int = 60,
    ) -> List[CandidateItem]:
        """
        RRF 融合算法

        公式: score(d) = Σ 1/(k + rank(d))
        其中 rank(d) 是文档 d 在某一召回列表中的排名（从 0 开始）

        Args:
            candidate_lists: 多路召回结果列表
            top_n: 返回最终结果数量
            k: RRF 参数（默认 60，根据设计图）

        Returns:
            融合后的候选列表，按 RRF 分数降序排列
        """
        try:
            logger.info(
                f"[RRF] 开始融合: lists_count={len(candidate_lists)}, k={k}, top_n={top_n}"
            )

            # 统计每路召回的数量
            list_sizes = [len(lst) for lst in candidate_lists]
            logger.debug(f"[RRF] 各路召回数量: {list_sizes}")

            # 存储每个文档的 RRF 分数和元数据
            # doc_id -> {"rrf_score": float, "candidate": CandidateItem}
            doc_scores: Dict[str, Dict] = defaultdict(
                lambda: {"rrf_score": 0.0, "candidate": None}
            )

            # 遍历每一路召回结果
            for list_idx, candidate_list in enumerate(candidate_lists):
                logger.debug(
                    f"[RRF] 处理第 {list_idx + 1} 路召回: size={len(candidate_list)}"
                )

                # 遍历该路召回中的每个文档
                for rank, candidate in enumerate(candidate_list):
                    # 计算 RRF 分数增量: 1 / (k + rank)
                    rrf_increment = 1.0 / (k + rank)

                    # 累加 RRF 分数
                    doc_scores[candidate.doc_id]["rrf_score"] += rrf_increment

                    # 保存候选项（如果该文档还没有保存）
                    if doc_scores[candidate.doc_id]["candidate"] is None:
                        doc_scores[candidate.doc_id]["candidate"] = candidate

            # 转换为列表并按 RRF 分数降序排序
            merged_candidates = []
            for doc_id, data in doc_scores.items():
                candidate = data["candidate"]
                # 更新候选项的分数为 RRF 分数
                candidate.score = data["rrf_score"]
                merged_candidates.append(candidate)

            # 排序
            merged_candidates.sort(key=lambda x: x.score, reverse=True)

            # 截断到 top_n
            final_results = merged_candidates[:top_n]

            logger.info(
                f"[RRF] 融合完成: 合并前总数={len(doc_scores)}, 返回 top_n={len(final_results)}"
            )
            logger.debug(
                f"[RRF] Top 3 分数: {[(c.doc_id, round(c.score, 4)) for c in final_results[:3]]}"
            )

            return final_results

        except Exception as e:
            logger.error(f"[RRF] 融合失败: {e}")
            raise
