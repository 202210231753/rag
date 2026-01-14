#!/usr/bin/env python3
"""
排序引擎单元测试

直接测试核心模块，不需要启动完整服务
"""

import sys
import asyncio
from typing import List

# 添加项目路径
sys.path.insert(0, '/home/barry/debug/rag')

print("=" * 60)
print("  排序引擎单元测试")
print("=" * 60)


# ============================================
# 测试 1: MMR 算法
# ============================================
def test_mmr_algorithm():
    """测试 MMR 算法"""
    print("\n[测试 1] MMR 算法")
    print("-" * 60)
    
    try:
        from app.rag.ranking.mmr import mmr_rerank, calculate_similarity
        
        # 创建模拟数据
        class MockItem:
            def __init__(self, doc_id, score, category, source):
                self.doc_id = doc_id
                self.final_score = score
                self.metadata = {"category": category, "source": source}
        
        items = [
            MockItem("doc_1", 0.95, "AI", "blog"),
            MockItem("doc_2", 0.93, "AI", "blog"),      # 和 doc_1 很相似
            MockItem("doc_3", 0.91, "ML", "paper"),     # 不同类别
            MockItem("doc_4", 0.89, "AI", "paper"),     # 不同来源
            MockItem("doc_5", 0.87, "NLP", "wiki"),     # 完全不同
        ]
        
        print(f"✓ 创建了 {len(items)} 个测试文档")
        print("  原始顺序（按分数）:")
        for i, item in enumerate(items):
            print(f"    {i+1}. {item.doc_id} (score={item.final_score}, "
                  f"category={item.metadata['category']}, "
                  f"source={item.metadata['source']})")
        
        # 测试相似度计算
        print("\n  测试相似度计算:")
        sim_12 = calculate_similarity(items[0], items[1])
        sim_13 = calculate_similarity(items[0], items[2])
        print(f"    doc_1 vs doc_2 (同类别同来源): {sim_12:.2f}")
        print(f"    doc_1 vs doc_3 (不同类别不同来源): {sim_13:.2f}")
        
        # 测试 MMR 重排（lambda=0.5，平衡模式）
        print("\n  应用 MMR (lambda=0.5):")
        result = mmr_rerank(items, lambda_param=0.5, top_n=5)
        
        print("  重排后顺序:")
        for i, item in enumerate(result):
            print(f"    {i+1}. {item.doc_id} (score={item.final_score}, "
                  f"category={item.metadata['category']}, "
                  f"source={item.metadata['source']})")
        
        # 验证多样性
        categories = [item.metadata['category'] for item in result]
        unique_categories = len(set(categories))
        print(f"\n  多样性检查: {unique_categories}/{len(result)} 个不同类别")
        
        assert len(result) == 5, "返回数量错误"
        assert result[0].doc_id == "doc_1", "第一个应该是最高分"
        print("\n✅ MMR 算法测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ MMR 算法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 测试 2: Redis 客户端
# ============================================
async def test_redis_client():
    """测试 Redis 客户端"""
    print("\n[测试 2] Redis 客户端")
    print("-" * 60)
    
    try:
        from app.core.redis_client import RedisClient
        
        # 创建客户端
        client = RedisClient()
        await client.connect()
        print("✓ Redis 连接成功")
        
        # 测试黑名单
        print("\n  测试黑名单功能:")
        await client.add_to_blacklist(["test_doc_1", "test_doc_2"])
        print("    ✓ 添加黑名单")
        
        blacklist = await client.get_blacklist()
        print(f"    ✓ 查询黑名单: {len(blacklist)} 个文档")
        
        is_blacklisted = await client.is_blacklisted("test_doc_1")
        print(f"    ✓ 检查 test_doc_1: {'在黑名单中' if is_blacklisted else '不在'}")
        
        await client.remove_from_blacklist(["test_doc_1"])
        print("    ✓ 移除黑名单")
        
        # 测试位置规则
        print("\n  测试位置规则功能:")
        await client.set_position_rule("测试查询", "doc_999", 0)
        print("    ✓ 设置位置规则")
        
        rule = await client.get_position_rule("测试查询")
        print(f"    ✓ 查询位置规则: doc={rule[0]}, position={rule[1]}")
        
        all_rules = await client.get_all_position_rules()
        print(f"    ✓ 查询所有规则: {len(all_rules)} 个")
        
        await client.delete_position_rule("测试查询")
        print("    ✓ 删除位置规则")
        
        # 清理测试数据
        await client.remove_from_blacklist(["test_doc_2"])
        
        await client.close()
        print("\n✅ Redis 客户端测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ Redis 客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 测试 3: 排序引擎
# ============================================
async def test_ranking_engine():
    """测试排序引擎"""
    print("\n[测试 3] 排序引擎集成")
    print("-" * 60)
    
    try:
        from app.core.redis_client import RedisClient
        from app.rag.ranking.engine import RankingEngine
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # 创建 Redis 客户端
        redis_client = RedisClient()
        await redis_client.connect()
        print("✓ Redis 连接成功")
        
        # 创建数据库连接（使用内存数据库进行测试）
        from sqlalchemy import text
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # 创建测试表
        db.execute(text("""
            CREATE TABLE diversity_config (
                id INTEGER PRIMARY KEY,
                lambda_param REAL DEFAULT 0.5,
                updated_at TEXT
            )
        """))
        db.execute(text("INSERT INTO diversity_config (id, lambda_param) VALUES (1, 0.5)"))
        db.commit()
        print("✓ 测试数据库创建成功")
        
        # 创建排序引擎
        engine_obj = RankingEngine(redis_client=redis_client, db_session=db)
        print("✓ 排序引擎创建成功")
        
        # 创建测试数据
        class MockItem:
            def __init__(self, doc_id, score, category, source):
                self.doc_id = doc_id
                self.final_score = score
                self.metadata = {"category": category, "source": source}
        
        items = [
            MockItem("doc_1", 0.95, "AI", "blog"),
            MockItem("doc_2", 0.93, "AI", "blog"),
            MockItem("doc_3", 0.91, "ML", "paper"),
            MockItem("doc_4", 0.89, "AI", "paper"),
            MockItem("doc_5", 0.87, "NLP", "wiki"),
            MockItem("blacklisted_doc", 0.99, "AI", "spam"),  # 将被过滤
        ]
        
        print(f"\n  准备 {len(items)} 个测试文档")
        
        # 添加黑名单
        await redis_client.add_to_blacklist(["blacklisted_doc"])
        print("  ✓ 添加黑名单: blacklisted_doc")
        
        # 设置位置规则
        await redis_client.set_position_rule("测试查询", "doc_5", 0)
        print("  ✓ 设置位置规则: doc_5 置顶")
        
        # 应用排序引擎
        print("\n  应用排序引擎...")
        result = await engine_obj.apply(
            query="测试查询",
            items=items,
            top_n=5,
            enable_diversity=True,
            enable_position_rules=True
        )
        
        print(f"\n  排序后结果 ({len(result)} 个):")
        for i, item in enumerate(result):
            print(f"    {i+1}. {item.doc_id} (score={item.final_score})")
        
        # 验证结果
        assert len(result) <= 5, "返回数量不应超过 top_n"
        assert all(item.doc_id != "blacklisted_doc" for item in result), "黑名单文档未被过滤"
        assert result[0].doc_id == "doc_5", "位置规则未生效（doc_5 应该在第一位）"
        
        # 清理
        await redis_client.remove_from_blacklist(["blacklisted_doc"])
        await redis_client.delete_position_rule("测试查询")
        await redis_client.close()
        db.close()
        
        print("\n✅ 排序引擎集成测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 排序引擎集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 主函数
# ============================================
async def main():
    """运行所有测试"""
    print("\n开始测试...\n")
    
    results = []
    
    # 测试 1: MMR 算法（不需要外部依赖）
    results.append(("MMR 算法", test_mmr_algorithm()))
    
    # 测试 2: Redis 客户端
    try:
        results.append(("Redis 客户端", await test_redis_client()))
    except Exception as e:
        print(f"❌ Redis 客户端测试跳过（Redis 未运行）: {e}")
        results.append(("Redis 客户端", False))
    
    # 测试 3: 排序引擎集成
    try:
        results.append(("排序引擎集成", await test_ranking_engine()))
    except Exception as e:
        print(f"❌ 排序引擎集成测试跳过: {e}")
        results.append(("排序引擎集成", False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}  {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n总计: {passed_count}/{total_count} 个测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total_count - passed_count} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
