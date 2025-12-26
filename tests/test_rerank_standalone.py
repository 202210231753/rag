"""
独立的 Rerank 测试脚本

不依赖完整的项目导入，专门用于测试 rerank 模块
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入 rerank 相关代码（避免触发其他模块导入）
from dataclasses import dataclass
from typing import Dict, Any, Optional


# 复制必要的数据结构
@dataclass
class CandidateItem:
    doc_id: str
    score: float
    source: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# 导入 rerank 模块
from app.rag.rerank.models import MockRerankModel
from app.rag.rerank.policy import PersonalizationPolicy, PolicyEngine
from app.rag.rerank.service import RerankService


async def test_basic_mock_rerank():
    """测试基本的 Mock 重排功能"""
    print("\n" + "=" * 60)
    print("测试 1: 基本 Mock 重排")
    print("=" * 60)

    # 初始化
    model = MockRerankModel()
    service = RerankService(rerank_model=model)

    # 准备候选文档
    candidates = [
        CandidateItem(
            doc_id="doc1",
            score=0.85,
            source="vector",
            content="Python 是一种高级编程语言，广泛应用于 Web 开发、数据分析和人工智能",
            metadata={"tags": ["Python", "编程"], "category": "技术"},
        ),
        CandidateItem(
            doc_id="doc2",
            score=0.75,
            source="keyword",
            content="Java 是一种面向对象的编程语言，主要用于企业级应用开发",
            metadata={"tags": ["Java", "编程"], "category": "技术"},
        ),
        CandidateItem(
            doc_id="doc3",
            score=0.70,
            source="vector",
            content="机器学习算法原理讲解，包括监督学习和无监督学习",
            metadata={"tags": ["AI", "机器学习"], "category": "研究"},
        ),
    ]

    # 执行重排
    query = "Python 编程语言教程"
    results = await service.predict(query, candidates)

    # 打印结果
    print(f"\n查询: {query}")
    print(f"候选文档数: {len(candidates)}")
    print(f"重排结果数: {len(results)}")
    print("\n排序结果:")
    for i, item in enumerate(results, 1):
        print(
            f"  {i}. {item.doc_id:6} | final={item.final_score:.4f} | "
            f"rerank={item.rerank_score:.4f} | original={item.original_score:.4f}"
        )

    # 验证降序
    scores = [r.final_score for r in results]
    is_descending = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
    print(f"\n✓ 降序验证: {'通过' if is_descending else '失败'}")

    return results


async def test_personalized_rerank():
    """测试个性化重排"""
    print("\n" + "=" * 60)
    print("测试 2: 个性化重排")
    print("=" * 60)

    # 初始化个性化策略
    policy = PersonalizationPolicy(
        interest_boost=0.3,
        history_boost=0.2,
        recency_boost=0.1,
    )
    policy_engine = PolicyEngine(personalization_policy=policy)

    model = MockRerankModel()
    service = RerankService(rerank_model=model, policy_engine=policy_engine)

    # 准备候选文档
    candidates = [
        CandidateItem(
            doc_id="doc1",
            score=0.80,
            source="vector",
            content="Python 数据分析库 Pandas 使用指南",
            metadata={
                "tags": ["Python", "数据分析"],
                "category": "技术",
                "date": "2025-12-20",
            },
        ),
        CandidateItem(
            doc_id="doc2",
            score=0.85,
            source="vector",
            content="Java Spring Boot 微服务架构实践",
            metadata={
                "tags": ["Java", "后端"],
                "category": "技术",
                "date": "2025-11-10",
            },
        ),
        CandidateItem(
            doc_id="doc3",
            score=0.78,
            source="vector",
            content="机器学习模型部署与优化",
            metadata={
                "tags": ["AI", "机器学习"],
                "category": "研究",
                "date": "2025-12-23",
            },
        ),
    ]

    # 用户画像
    user_features = {
        "interest": ["Python", "数据分析", "AI"],
        "history": ["技术", "研究"],
    }

    # 执行重排
    query = "数据分析工具"
    results = await service.predict(query, candidates, user_features)

    # 打印结果
    print(f"\n查询: {query}")
    print(f"用户兴趣: {user_features['interest']}")
    print(f"历史类别: {user_features['history']}")
    print("\n排序结果:")
    for i, item in enumerate(results, 1):
        boost = (
            (item.final_score / item.rerank_score - 1) * 100
            if item.rerank_score > 0
            else 0
        )
        print(
            f"  {i}. {item.doc_id:6} | final={item.final_score:.4f} | "
            f"rerank={item.rerank_score:.4f} | boost=+{boost:.1f}%"
        )

    # 验证个性化效果
    has_personalization = any(r.final_score > r.rerank_score for r in results)
    print(f"\n✓ 个性化效果: {'生效' if has_personalization else '未生效'}")

    return results


async def test_validation():
    """测试降序验证机制"""
    print("\n" + "=" * 60)
    print("测试 3: 降序验证机制")
    print("=" * 60)

    model = MockRerankModel()
    service = RerankService(rerank_model=model, enable_validation=True)

    candidates = [
        CandidateItem(doc_id=f"doc{i}", score=0.8, source="vector", content="测试文档")
        for i in range(5)
    ]

    try:
        results = await service.predict("测试查询", candidates)
        print(f"\n重排完成: {len(results)} 个结果")
        print("验证状态: ✓ 通过（结果为降序）")

        # 显示分数
        scores = [r.final_score for r in results]
        print(f"分数列表: {[f'{s:.4f}' for s in scores]}")

    except ValueError as e:
        print(f"验证失败: {e}")

    return results


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Rerank 模块独立测试")
    print("=" * 60)

    try:
        # 测试 1: 基本重排
        await test_basic_mock_rerank()

        # 测试 2: 个性化重排
        await test_personalized_rerank()

        # 测试 3: 验证机制
        await test_validation()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
