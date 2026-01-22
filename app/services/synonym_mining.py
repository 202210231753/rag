"""同义词自动挖掘服务。"""
from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple, Dict
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.synonym import SynonymCandidate
from app.models.stats import SearchLog
from app.services.synonym_service import SynonymService

logger = logging.getLogger(__name__)


class SearchLogMiner:
    """基于搜索点击日志的挖掘策略。
    
    挖掘原理：
    1. 找出用户搜索后点击了相同文档的不同查询词
    2. 如果多个查询词都指向同一个文档，这些查询词可能是同义词
    3. 根据点击频率和文档匹配度计算同义词置信度
    """

    def __init__(self, db: Session):
        """
        Args:
            db: 数据库会话
        """
        self.db = db

    def mine_synonyms(
        self,
        domain: str = "default",
        days_back: int = 30,
        min_clicks: int = 2,
        min_co_click_ratio: float = 0.3,
    ) -> List[Tuple[str, str, float]]:
        """
        从搜索点击日志中挖掘同义词。
        
        挖掘逻辑：
        1. 统计每个文档被哪些查询词点击过
        2. 找出共同点击同一文档的查询词对
        3. 计算同义词置信度（基于共同点击的文档数量和比例）
        
        Args:
            domain: 领域（当前未使用，预留）
            days_back: 回溯天数（默认30天）
            min_clicks: 最小点击次数（查询词至少被点击多少次才考虑）
            min_co_click_ratio: 最小共同点击比例（两个查询词共同点击的文档数 / 总文档数）
        
        Returns:
            List[(canonical, synonym, score)]
            score 范围：0-1，表示同义词置信度
        """
        # 1. 获取时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        logger.info(
            f"开始从搜索日志挖掘同义词: days_back={days_back}, "
            f"min_clicks={min_clicks}, min_co_click_ratio={min_co_click_ratio}"
        )

        # 2. 查询搜索日志（有查询词和点击文档的记录）
        search_logs = (
            self.db.query(SearchLog)
            .filter(
                SearchLog.timestamp.between(start_time, end_time),
                SearchLog.query.isnot(None),
                SearchLog.clicked_doc_id.isnot(None),
            )
            .all()
        )

        if not search_logs:
            logger.info("没有搜索点击日志数据，跳过挖掘")
            return []

        logger.info(f"找到 {len(search_logs)} 条搜索点击日志")

        # 3. 统计：每个查询词点击了哪些文档
        # query -> {doc_id: click_count}
        query_docs: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for log in search_logs:
            query = log.query.strip() if log.query else ""
            doc_id = log.clicked_doc_id.strip() if log.clicked_doc_id else ""

            if not query or not doc_id:
                continue

            query_docs[query][doc_id] += 1

        # 4. 过滤：只保留点击次数足够的查询词
        filtered_queries = {
            q: docs
            for q, docs in query_docs.items()
            if sum(docs.values()) >= min_clicks
        }

        if not filtered_queries:
            logger.info(f"没有查询词满足最小点击次数要求（{min_clicks}）")
            return []

        logger.info(f"过滤后剩余 {len(filtered_queries)} 个有效查询词")

        # 5. 找出共同点击同一文档的查询词对
        query_list = list(filtered_queries.keys())
        synonym_pairs: List[Tuple[str, str, float]] = []

        for i, query1 in enumerate(query_list):
            docs1 = set(filtered_queries[query1].keys())
            if not docs1:
                continue

            for query2 in query_list[i + 1 :]:
                docs2 = set(filtered_queries[query2].keys())
                if not docs2:
                    continue

                # 计算共同点击的文档
                common_docs = docs1 & docs2
                if not common_docs:
                    continue

                # 计算共同点击比例
                total_docs = docs1 | docs2
                co_click_ratio = len(common_docs) / len(total_docs) if total_docs else 0.0

                if co_click_ratio < min_co_click_ratio:
                    continue

                # 计算置信度分数
                # 综合考虑：共同文档数、共同比例、总点击次数
                common_click_count = sum(
                    min(filtered_queries[query1].get(doc, 0), filtered_queries[query2].get(doc, 0))
                    for doc in common_docs
                )
                total_click1 = sum(filtered_queries[query1].values())
                total_click2 = sum(filtered_queries[query2].values())

                # 分数计算：共同点击比例 * 归一化的共同点击次数
                normalized_common_clicks = min(common_click_count / max(total_click1, total_click2, 1), 1.0)
                score = co_click_ratio * 0.7 + normalized_common_clicks * 0.3

                # 确保分数在合理范围内
                score = min(score, 1.0)

                # 选择较短的词作为 canonical（如果长度相同，选择字典序较小的）
                if len(query1) <= len(query2):
                    canonical, synonym = query1, query2
                else:
                    canonical, synonym = query2, query1

                # 避免重复（相同词对）
                if canonical != synonym:
                    synonym_pairs.append((canonical, synonym, score))

        logger.info(f"挖掘到 {len(synonym_pairs)} 个同义词对")

        # 6. 去重和排序
        # 使用字典去重（保留分数最高的）
        unique_pairs: dict[Tuple[str, str], float] = {}
        for canonical, synonym, score in synonym_pairs:
            key = (canonical, synonym)
            if key not in unique_pairs or score > unique_pairs[key]:
                unique_pairs[key] = score

        # 转换为列表并按分数排序
        result = [(canonical, synonym, score) for (canonical, synonym), score in unique_pairs.items()]
        result.sort(key=lambda x: x[2], reverse=True)

        logger.info(f"去重后剩余 {len(result)} 个同义词对")
        return result

    def mine_synonyms_by_document_similarity(
        self,
        domain: str = "default",
        days_back: int = 30,
        min_clicks: int = 2,
        similarity_threshold: float = 0.5,
    ) -> List[Tuple[str, str, float]]:
        """
        基于文档相似度的挖掘（扩展方法）。
        
        如果两个查询词点击的文档集合高度相似，则可能是同义词。
        
        Args:
            domain: 领域
            days_back: 回溯天数
            min_clicks: 最小点击次数
            similarity_threshold: 文档集合相似度阈值（Jaccard 相似度）
        
        Returns:
            List[(canonical, synonym, score)]
        """
        # 1. 获取时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        # 2. 查询搜索日志
        search_logs = (
            self.db.query(SearchLog)
            .filter(
                SearchLog.timestamp.between(start_time, end_time),
                SearchLog.query.isnot(None),
                SearchLog.clicked_doc_id.isnot(None),
            )
            .all()
        )

        if not search_logs:
            return []

        # 3. 统计每个查询词点击的文档集合
        query_docs: dict[str, set[str]] = defaultdict(set)

        for log in search_logs:
            query = log.query.strip() if log.query else ""
            doc_id = log.clicked_doc_id.strip() if log.clicked_doc_id else ""

            if not query or not doc_id:
                continue

            query_docs[query].add(doc_id)

        # 4. 计算查询词对的文档集合相似度（Jaccard）
        query_list = list(query_docs.keys())
        synonym_pairs: List[Tuple[str, str, float]] = []

        for i, query1 in enumerate(query_list):
            docs1 = query_docs[query1]
            if len(docs1) < min_clicks:
                continue

            for query2 in query_list[i + 1 :]:
                docs2 = query_docs[query2]
                if len(docs2) < min_clicks:
                    continue

                # 计算 Jaccard 相似度
                intersection = len(docs1 & docs2)
                union = len(docs1 | docs2)
                jaccard = intersection / union if union > 0 else 0.0

                if jaccard >= similarity_threshold:
                    # 选择较短的词作为 canonical
                    if len(query1) <= len(query2):
                        canonical, synonym = query1, query2
                    else:
                        canonical, synonym = query2, query1

                    if canonical != synonym:
                        synonym_pairs.append((canonical, synonym, jaccard))

        # 5. 去重
        unique_pairs: dict[Tuple[str, str], float] = {}
        for canonical, synonym, score in synonym_pairs:
            key = (canonical, synonym)
            if key not in unique_pairs or score > unique_pairs[key]:
                unique_pairs[key] = score

        result = [(canonical, synonym, score) for (canonical, synonym), score in unique_pairs.items()]
        result.sort(key=lambda x: x[2], reverse=True)

        return result


class IMiningStrategy(ABC):
    """挖掘策略接口。"""

    @abstractmethod
    def mine_synonyms(
        self, domain: str, seed_terms: List[str], threshold: float = 0.82
    ) -> List[tuple[str, str, float]]:
        """
        挖掘同义词。
        
        Args:
            domain: 领域
            seed_terms: 种子词列表
            threshold: 相似度阈值
        
        Returns:
            List[(canonical, synonym, score)]
        """
        pass


class LocalEmbeddingMiner(IMiningStrategy):
    """基于本地 Embedding 的挖掘器。"""

    def __init__(self, embedding_model_path: Optional[str] = None):
        """
        Args:
            embedding_model_path: Embedding 模型路径（如 Qwen3-Embedding-0.6B）
        """
        self.embedding_model_path = embedding_model_path or os.getenv(
            "EMBEDDING_MODEL_PATH", "/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B"
        )
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """延迟加载模型。"""
        if self._model is not None:
            return

        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            logger.info(f"加载 Embedding 模型: {self.embedding_model_path}")
            self._tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_path)
            self._model = AutoModel.from_pretrained(self.embedding_model_path)
            self._model.eval()

            if torch.cuda.is_available():
                self._model = self._model.cuda()
                logger.info("使用 GPU 加速")
            else:
                logger.info("使用 CPU")

        except ImportError:
            logger.warning("transformers 未安装，使用 OpenAI Embedding 作为备选")
            self._model = "openai"  # 标记使用 OpenAI
        except Exception as e:
            logger.error(f"加载模型失败: {e}", exc_info=True)
            raise

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的 embedding。"""
        self._load_model()

        if self._model == "openai":
            # 使用 OpenAI Embedding
            return self._get_openai_embedding(text)

        # 使用本地模型
        from transformers import AutoModel, AutoTokenizer
        import torch

        inputs = self._tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            # 使用 [CLS] token 的 embedding 或 mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

        return embeddings.tolist()

    def _get_openai_embedding(self, text: str) -> List[float]:
        """使用 OpenAI Embedding API。"""
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
            import os

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 未设置")

            embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
            embedding = embed_model.get_text_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"OpenAI Embedding 失败: {e}", exc_info=True)
            raise

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度。"""
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def mine_synonyms(
        self, domain: str, seed_terms: List[str], threshold: float = 0.82
    ) -> List[tuple[str, str, float]]:
        """
        挖掘同义词（简化版：从种子词出发，找相似词）。
        
        从文档库或词表中挖掘同义词。
        """
        if not seed_terms:
            return []

        self._load_model()

        # 获取种子词的 embedding
        seed_embeddings = {}
        for term in seed_terms:
            try:
                seed_embeddings[term] = self._get_embedding(term)
            except Exception as e:
                logger.warning(f"获取 {term} 的 embedding 失败: {e}")
                continue

        if not seed_embeddings:
            return []

        # 简化实现：这里应该从文档库或词表中查找相似词
        # 实际场景中，可以从：
        # 1. 现有 canonical 列表
        # 2. 文档库中的高频词
        # 3. 外部词表
        # 这里仅做示例，返回空列表
        # 实际实现需要根据项目的数据源来设计
        
        # TODO: 实现实际的挖掘逻辑
        # 示例：从文档库中提取候选词，计算相似度，返回超过阈值的同义词
        logger.warning(
            "LocalEmbeddingMiner.mine_synonyms 需要根据实际数据源实现。"
            "当前返回空列表，请参考文档实现实际的挖掘逻辑。"
        )
        return []


class MiningJobScheduler:
    """挖掘任务调度器。"""

    def __init__(self, db: Session, strategy: IMiningStrategy = None):
        """
        Args:
            db: 数据库会话
            strategy: 挖掘策略（可选，如果不提供则使用默认策略）
        """
        self.db = db
        self.strategy = strategy
        self.synonym_service = SynonymService(db)
        self.search_log_miner = SearchLogMiner(db)

    def run_mining(
        self,
        domain: str = "default",
        threshold: float = 0.82,
        use_embedding: bool = True,
        use_search_log: bool = True,
        search_log_days: int = 30,
        search_log_min_clicks: int = 2,
        search_log_min_ratio: float = 0.3,
    ) -> int:
        """
        执行挖掘任务（支持多种挖掘策略）。
        
        Args:
            domain: 领域
            threshold: 相似度阈值（用于 Embedding 挖掘）
            use_embedding: 是否使用 Embedding 挖掘
            use_search_log: 是否使用搜索日志挖掘
            search_log_days: 搜索日志回溯天数
            search_log_min_clicks: 搜索日志最小点击次数
            search_log_min_ratio: 搜索日志最小共同点击比例
        
        Returns:
            生成的候选数量
        """
        all_candidates = []

        # 1. Embedding 挖掘（如果启用）
        if use_embedding and self.strategy:
            # 直接查询数据库获取模型对象
            from app.models.synonym import SynonymGroup
            groups = (
                self.db.query(SynonymGroup)
                .filter(SynonymGroup.domain == domain)
                .order_by(SynonymGroup.created_at.desc())
                .all()
            )
            seed_terms = [g.canonical for g in groups if g.enabled == 1]

            if seed_terms:
                logger.info(f"开始 Embedding 挖掘: domain={domain}, seed_count={len(seed_terms)}")
                embedding_results = self.strategy.mine_synonyms(domain, seed_terms, threshold)
                for canonical, synonym, score in embedding_results:
                    all_candidates.append(
                        (canonical, synonym, score, "embedding")
                    )
                logger.info(f"Embedding 挖掘完成: {len(embedding_results)} 个候选")
            else:
                logger.info(f"领域 {domain} 没有种子词，跳过 Embedding 挖掘")

        # 2. 搜索日志挖掘（如果启用）
        if use_search_log:
            logger.info(f"开始搜索日志挖掘: domain={domain}, days_back={search_log_days}")
            search_log_results = self.search_log_miner.mine_synonyms(
                domain=domain,
                days_back=search_log_days,
                min_clicks=search_log_min_clicks,
                min_co_click_ratio=search_log_min_ratio,
            )
            for canonical, synonym, score in search_log_results:
                all_candidates.append(
                    (canonical, synonym, score, "search_log")
                )
            logger.info(f"搜索日志挖掘完成: {len(search_log_results)} 个候选")

        if not all_candidates:
            logger.info("未挖掘到任何同义词候选")
            return 0

        # 3. 去重并保存候选
        candidates = []
        seen_pairs = set()

        for canonical, synonym, score, source in all_candidates:
            # 检查是否已存在（同 domain/canonical/synonym）
            existing = (
                self.db.query(SynonymCandidate)
                .filter(
                    and_(
                        SynonymCandidate.domain == domain,
                        SynonymCandidate.canonical == canonical,
                        SynonymCandidate.synonym == synonym,
                    )
                )
                .first()
            )
            if existing:
                continue

            # 检查是否已在同义词组中存在（直接查询数据库）
            from app.models.synonym import SynonymGroup, SynonymTerm
            group = (
                self.db.query(SynonymGroup)
                .filter(
                    and_(
                        SynonymGroup.domain == domain,
                        SynonymGroup.enabled == 1,
                        SynonymGroup.canonical == synonym,
                    )
                )
                .first()
            )
            if not group:
                term_obj = (
                    self.db.query(SynonymTerm)
                    .join(SynonymGroup)
                    .filter(
                        and_(
                            SynonymGroup.domain == domain,
                            SynonymGroup.enabled == 1,
                            SynonymTerm.term == synonym,
                        )
                    )
                    .first()
                )
                if term_obj:
                    continue  # 已存在，跳过
            else:
                continue  # 已存在，跳过

            # 去重：相同词对只保留一次（保留分数最高的）
            pair_key = (canonical, synonym)
            if pair_key in seen_pairs:
                # 如果已存在，检查是否需要更新分数
                existing_candidate = next(
                    (c for c in candidates if (c.canonical, c.synonym) == pair_key),
                    None
                )
                if existing_candidate and score > existing_candidate.score:
                    existing_candidate.score = score
                    existing_candidate.source = source
                continue

            seen_pairs.add(pair_key)

            candidate = SynonymCandidate(
                domain=domain,
                canonical=canonical,
                synonym=synonym,
                score=score,
                status="pending",
                source=source,
            )
            candidates.append(candidate)

        # 4. 批量保存
        if candidates:
            for candidate in candidates:
                self.db.add(candidate)
            self.db.commit()
            count = len(candidates)
            logger.info(
                f"挖掘完成: domain={domain}, generated={count} "
                f"(embedding={sum(1 for c in candidates if c.source == 'embedding')}, "
                f"search_log={sum(1 for c in candidates if c.source == 'search_log')})"
            )
            return count
        else:
            logger.info("所有候选都已存在，跳过保存")
            return 0

