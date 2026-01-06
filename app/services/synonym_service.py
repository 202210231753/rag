"""同义词业务逻辑层。"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Set
from datetime import datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.synonym import SynonymGroup, SynonymTerm, SynonymCandidate
from app.schemas.synonym_schema import SynonymGroupSchema, SynonymTermSchema, RewritePlan

logger = logging.getLogger(__name__)


class SynonymService:
    """同义词服务（包含数据访问和查询改写）。"""

    def __init__(self, db: Session, max_expansions: int = 8, max_per_group: int = 3):
        """
        Args:
            db: 数据库会话
            max_expansions: 查询改写最大扩展词数
            max_per_group: 每个组最多取几个词
        """
        self.db = db
        self.max_expansions = max_expansions
        self.max_per_group = max_per_group
        # 查询改写缓存
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_max_size = 100

    # ========== 数据访问方法 ==========

    def _upsert_group(
        self, domain: str, canonical: str, terms: List[Tuple[str, float]], enabled: int = 1
    ) -> SynonymGroup:
        """创建或更新同义词组（幂等，带事务回滚）。"""
        try:
            group = (
                self.db.query(SynonymGroup)
                .filter(and_(SynonymGroup.domain == domain, SynonymGroup.canonical == canonical))
                .first()
            )

            if group:
                group.enabled = enabled
                # 删除旧的 terms（级联删除更高效）
                self.db.query(SynonymTerm).filter(SynonymTerm.group_id == group.group_id).delete(synchronize_session=False)
            else:
                group = SynonymGroup(domain=domain, canonical=canonical, enabled=enabled)
                self.db.add(group)
                self.db.flush()

            # 批量添加新的 terms
            for term, weight in terms:
                synonym_term = SynonymTerm(group_id=group.group_id, term=term, weight=weight)
                self.db.add(synonym_term)

            self.db.commit()
            self.db.refresh(group)
            return group
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新同义词组失败: domain={domain}, canonical={canonical}, error={e}", exc_info=True)
            raise

    def _remove_groups(self, group_ids: List[int]) -> int:
        """删除同义词组（级联删除同义词项，带事务回滚）。"""
        try:
            # 由于外键设置了 ON DELETE CASCADE，只需删除 group 即可
            count = self.db.query(SynonymGroup).filter(SynonymGroup.group_id.in_(group_ids)).delete(
                synchronize_session=False
            )
            self.db.commit()
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除同义词组失败: group_ids={group_ids}, error={e}", exc_info=True)
            raise

    def _find_by_term(self, domain: str, term: str) -> Optional[Tuple[SynonymGroup, List[SynonymTerm]]]:
        """根据词查找同义词组（优化查询，使用一次 JOIN 查询）。"""
        # 使用一次查询同时查找 canonical 和 term 匹配
        # 先尝试通过 canonical 匹配
        group = (
            self.db.query(SynonymGroup)
            .filter(
                and_(
                    SynonymGroup.domain == domain,
                    SynonymGroup.enabled == 1,
                    SynonymGroup.canonical == term,
                )
            )
            .first()
        )

        if group:
            # 使用 relationship 预加载 terms，避免额外查询
            terms = group.terms
            return (group, list(terms))

        # 通过 term 匹配（使用 JOIN 优化）
        term_obj = (
            self.db.query(SynonymTerm)
            .join(SynonymGroup)
            .filter(
                and_(
                    SynonymGroup.domain == domain,
                    SynonymGroup.enabled == 1,
                    SynonymTerm.term == term,
                )
            )
            .first()
        )

        if term_obj:
            group = term_obj.group
            # 使用 relationship 避免额外查询
            return (group, list(group.terms))

        return None

    def _list_all_groups(self, domain: str) -> List[SynonymGroup]:
        """列出指定领域的所有同义词组（已废弃，使用 list_groups 代替）。"""
        return (
            self.db.query(SynonymGroup)
            .filter(SynonymGroup.domain == domain)
            .order_by(SynonymGroup.created_at.desc())
            .all()
        )

    # ========== 业务逻辑方法 ==========

    def manual_upsert(self, domain: str, canonical: str, synonyms: List[str]) -> SynonymGroupSchema:
        """手动添加同义词（幂等/去重）。"""
        unique_synonyms = list(set(synonyms))
        terms = [(term, 1.0) for term in unique_synonyms]

        group = self._upsert_group(domain, canonical, terms, enabled=1)
        logger.info(f"手动添加同义词组: domain={domain}, canonical={canonical}, synonyms={unique_synonyms}")

        return self._group_to_schema(group)

    def batch_import(self, domain: str, groups: List[dict]) -> int:
        """批量导入同义词组（带事务回滚）。"""
        count = 0
        skipped = 0
        errors = 0

        for idx, group_data in enumerate(groups, 1):
            try:
                canonical = group_data.get("canonical", "").strip()
                synonyms = group_data.get("synonyms", [])

                if not canonical or not synonyms:
                    skipped += 1
                    continue

                unique_synonyms = list(set([s.strip() for s in synonyms if s.strip()]))
                if not unique_synonyms:
                    skipped += 1
                    continue

                terms = [(term, 1.0) for term in unique_synonyms]
                self._upsert_group(domain, canonical, terms, enabled=1)
                count += 1

            except Exception as e:
                errors += 1
                logger.warning(f"导入第 {idx} 组时出错: {e}", exc_info=logger.isEnabledFor(logging.DEBUG))
                # 继续处理下一组，不中断整个导入流程

        logger.info(f"批量导入完成: domain={domain}, 成功={count}, 跳过={skipped}, 错误={errors}")
        return count

    def remove_groups(self, group_ids: List[int]) -> int:
        """删除同义词组。"""
        count = self._remove_groups(group_ids)
        logger.info(f"删除同义词组: group_ids={group_ids}, count={count}")
        return count

    def _group_to_schema(self, group: SynonymGroup) -> SynonymGroupSchema:
        """将 SynonymGroup 转换为 Schema（提取重复代码）。"""
        term_schemas = [SynonymTermSchema(term=t.term, weight=t.weight) for t in group.terms]
        return SynonymGroupSchema(
            group_id=group.group_id,
            domain=group.domain,
            canonical=group.canonical,
            enabled=group.enabled,
            terms=term_schemas,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )

    def list_groups(self, domain: str, limit: int = 100, offset: int = 0) -> Tuple[List[SynonymGroupSchema], int]:
        """查询同义词组列表（分页，优化查询）。"""
        # 使用数据库分页，而不是在内存中分页
        total = (
            self.db.query(SynonymGroup)
            .filter(SynonymGroup.domain == domain)
            .count()
        )
        
        groups = (
            self.db.query(SynonymGroup)
            .filter(SynonymGroup.domain == domain)
            .order_by(SynonymGroup.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        group_schemas = [self._group_to_schema(group) for group in groups]
        return (group_schemas, total)

    # ========== 查询改写方法 ==========

    def rewrite(self, domain: str, query: str) -> RewritePlan:
        """改写查询（one-hop 扩展）。"""
        if not domain:
            domain = "default"

        original_query = query.strip()
        if not original_query:
            logger.debug(f"空查询，跳过改写: domain={domain}")
            return RewritePlan(original_query=original_query, expanded_terms=[], debug={})

        # 检查缓存
        cache_key = f"{domain}:{original_query}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        debug_info = {
            "domain": domain,
            "matched_groups": [],
            "expansion_count": 0,
        }

        # 分词
        query_terms = self._tokenize(original_query)
        if not query_terms:
            return RewritePlan(original_query=original_query, expanded_terms=[], debug=debug_info)

        # 最长匹配优先
        matched_groups = []
        expanded_terms_set: Set[str] = set()

        # 完整查询匹配
        full_match = self._find_by_term(domain, original_query)
        if full_match:
            group, terms = full_match
            matched_groups.append({"canonical": group.canonical, "matched_term": original_query})
            for term in terms:
                if term.term != original_query:
                    expanded_terms_set.add(term.term)
                    if len(expanded_terms_set) >= self.max_expansions:
                        break
            if len(expanded_terms_set) >= self.max_expansions:
                expanded_terms = list(expanded_terms_set)[: self.max_expansions]
                result = RewritePlan(
                    original_query=original_query,
                    expanded_terms=expanded_terms,
                    debug={**debug_info, "matched_groups": matched_groups, "expansion_count": len(expanded_terms)},
                )
                self._save_to_cache(cache_key, result)
                return result

        # 按词匹配（从长到短）
        query_terms_sorted = sorted(query_terms, key=len, reverse=True)
        for term in query_terms_sorted:
            if len(expanded_terms_set) >= self.max_expansions:
                break

            match_result = self._find_by_term(domain, term)
            if match_result:
                group, terms = match_result
                matched_groups.append({"canonical": group.canonical, "matched_term": term})

                sorted_terms = sorted(terms, key=lambda t: t.weight, reverse=True)
                for synonym_term in sorted_terms[: self.max_per_group]:
                    if synonym_term.term != term and synonym_term.term != original_query:
                        expanded_terms_set.add(synonym_term.term)
                        if len(expanded_terms_set) >= self.max_expansions:
                            break

        # 去重：排除原查询
        expanded_terms = [t for t in expanded_terms_set if t != original_query][: self.max_expansions]

        debug_info["matched_groups"] = matched_groups
        debug_info["expansion_count"] = len(expanded_terms)

        result = RewritePlan(
            original_query=original_query,
            expanded_terms=expanded_terms,
            debug=debug_info,
        )

        self._save_to_cache(cache_key, result)

        if expanded_terms:
            logger.info(f"查询改写命中: domain={domain}, query={original_query}, expanded={expanded_terms}")

        return result

    def _tokenize(self, text: str) -> List[str]:
        """简单分词（按空格和标点）。"""
        tokens = re.split(r"[\s,，。、；;：:！!？?]+", text)
        return [t.strip() for t in tokens if t.strip()]

    def _get_from_cache(self, key: str) -> Optional[RewritePlan]:
        """从缓存获取（带 TTL 和自动清理）。"""
        now = datetime.now()
        
        # 清理过期缓存
        expired_keys = [
            k for k, (_, timestamp) in self._cache.items()
            if (now - timestamp) >= self._cache_ttl
        ]
        for k in expired_keys:
            del self._cache[k]
            logger.debug(f"清理过期缓存: {k}")

        if key in self._cache:
            result, timestamp = self._cache[key]
            age = now - timestamp
            if age < self._cache_ttl:
                logger.debug(f"缓存命中: {key} (age={age.total_seconds():.1f}s)")
                return result
        
        return None

    def _save_to_cache(self, key: str, result: RewritePlan):
        """保存到缓存（LRU 策略）。"""
        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self._cache_max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            logger.debug(f"缓存已满，删除最旧条目: {oldest_key}")

        self._cache[key] = (result, datetime.now())

    # ========== 初始化方法 ==========

    def init_default_synonyms(
        self,
        seed_file_path: Optional[str] = None,
        domain: str = "default",
        force_reload: bool = False,
    ) -> int:
        """初始化默认同义词数据。"""
        if seed_file_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            seed_file_path = project_root / "migrations" / "init_default_synonyms.json"

        seed_file_path = Path(seed_file_path)
        if not seed_file_path.exists():
            logger.warning(f"种子数据文件不存在: {seed_file_path}")
            return 0

        existing_groups = self._list_all_groups(domain)
        if existing_groups and not force_reload:
            logger.info(
                f"领域 '{domain}' 已存在 {len(existing_groups)} 个同义词组，跳过初始化。"
            )
            return len(existing_groups)

        if force_reload and existing_groups:
            group_ids = [g.group_id for g in existing_groups]
            self._remove_groups(group_ids)
            logger.info(f"已删除 {len(existing_groups)} 个现有同义词组")

        try:
            with open(seed_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"加载种子数据文件失败: {e}", exc_info=True)
            return 0

        groups = data.get("groups", [])
        if not groups:
            logger.warning("种子数据文件中没有同义词组数据")
            return 0

        count = self.batch_import(domain, groups)
        if count > 0:
            logger.info(f"初始化完成：领域 '{domain}'，导入 {count} 个同义词组")
        return count

    def check_and_init(self, domain: str = "default") -> bool:
        """检查并初始化（如果数据为空则自动初始化）。"""
        existing_groups = self._list_all_groups(domain)
        if not existing_groups:
            logger.info(f"领域 '{domain}' 没有同义词数据，开始自动初始化...")
            count = self.init_default_synonyms(domain=domain)
            return count > 0
        return False


class ReviewService:
    """候选审核服务。"""

    def __init__(self, db: Session):
        self.db = db

    def list_candidates(self, domain: str, status: str, limit: int = 100, offset: int = 0) -> Tuple[List[SynonymCandidate], int]:
        """按状态列出候选。"""
        query = self.db.query(SynonymCandidate).filter(
            and_(SynonymCandidate.domain == domain, SynonymCandidate.status == status)
        )

        total = query.count()
        candidates = query.order_by(SynonymCandidate.score.desc()).limit(limit).offset(offset).all()

        return (candidates, total)

    def approve(self, candidate_ids: List[int]) -> int:
        """审核通过候选，并写入 synonym_group/synonym_term（带事务回滚）。"""
        try:
            candidates = (
                self.db.query(SynonymCandidate)
                .filter(SynonymCandidate.candidate_id.in_(candidate_ids))
                .filter(SynonymCandidate.status == "pending")
                .all()
            )

            if not candidates:
                return 0

            # 按 (domain, canonical) 分组
            groups_map: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}
            for candidate in candidates:
                key = (candidate.domain, candidate.canonical)
                if key not in groups_map:
                    groups_map[key] = []
                groups_map[key].append((candidate.synonym, candidate.score))

            # 批量写入同义词组
            approved_count = 0
            service = SynonymService(self.db)
            for (domain, canonical), synonym_list in groups_map.items():
                terms = []
                for synonym, score in synonym_list:
                    # 将 score (0-1) 转换为 weight (0.5-1.0)
                    weight = 0.5 + (score * 0.5)
                    terms.append((synonym, weight))

                service._upsert_group(domain, canonical, terms, enabled=1)
                approved_count += len(synonym_list)

            # 更新候选状态
            self.db.query(SynonymCandidate).filter(
                SynonymCandidate.candidate_id.in_(candidate_ids)
            ).update({"status": "approved"}, synchronize_session=False)
            self.db.commit()

            logger.info(f"审核通过候选: candidate_ids={candidate_ids}, count={approved_count}")
            return approved_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"审核通过候选失败: candidate_ids={candidate_ids}, error={e}", exc_info=True)
            raise

    def reject(self, candidate_ids: List[int]) -> int:
        """拒绝候选（带事务回滚）。"""
        try:
            count = (
                self.db.query(SynonymCandidate)
                .filter(SynonymCandidate.candidate_id.in_(candidate_ids))
                .update({"status": "rejected"}, synchronize_session=False)
            )
            self.db.commit()
            logger.info(f"拒绝候选: candidate_ids={candidate_ids}, count={count}")
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"拒绝候选失败: candidate_ids={candidate_ids}, error={e}", exc_info=True)
            raise


def init_synonyms_on_startup(db: Session, domain: str = "default"):
    """应用启动时调用此函数初始化同义词数据。"""
    try:
        service = SynonymService(db)
        initialized = service.check_and_init(domain=domain)
        if initialized:
            logger.info(f"成功初始化领域 '{domain}' 的同义词数据")
        return initialized
    except Exception as e:
        logger.error(
            f"启动时初始化同义词数据失败: {e}",
            exc_info=logger.isEnabledFor(logging.DEBUG)
        )
        return False



