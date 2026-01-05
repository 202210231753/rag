import sys
import os

# 将项目根目录添加到路径（确保我们可以导入 'chatbot' 包）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from chatbot.rag.app.data.user_profile_store import UserProfileStore
from chatbot.rag.app.infra.config import ConfigCenter
from chatbot.rag.app.infra.ai_client import AIModelClient
from chatbot.rag.app.infra.vector_db import VectorDBClient
from chatbot.rag.app.core.user_profile_manager import UserProfileManager
from chatbot.rag.app.core.ranking_engine import RankingEngine
from chatbot.rag.app.services.recommender_service import ContentRecommenderService
from chatbot.rag.app.services.recommender_service import QueryRecommenderService
from chatbot.rag.app.services.feedback_service import FeedbackService

def main():
    print("=== 初始化 RAG 系统 (真实数据库模式) ===")
    
    # 1. 基础设施设置
    config = ConfigCenter()
    ai_client = AIModelClient()
    
    # 初始化真实数据库客户端
    vector_db = VectorDBClient(collection_name="rag_items")
    profile_store = UserProfileStore()
    
    # 2. 核心逻辑设置
    ranking_engine = RankingEngine()
    profile_manager = UserProfileManager(profile_store, ai_client, vector_db)
    
    # 3. 服务设置
    content_service = ContentRecommenderService(
        profile_manager, ranking_engine, config, ai_client, vector_db
    )
    query_service = QueryRecommenderService(config, ai_client, vector_db)
    feedback_service = FeedbackService()
    
    print("\n=== 场景 1: 用户数据导入与猜你喜欢 ===")
    # 导入用户数据 (现在会写入真实 MySQL)
    # 注意：为了适配旧表 user_profiles，这里必须使用真实存在的数字 ID (例如 1, 2)
    # 如果数据库里没有 ID 1 或 2，请先确保数据存在，或者修改下面的 CSV ID
    csv_data = """user_id,static_tags,location
    1,python;ai;coding,Shanghai
    2,travel;food,Beijing
    """
    count = profile_manager.import_user_dataset(csv_data)
    print(f"Imported {count} users into MySQL.")
    
    # 模拟用户互动（更新动态兴趣 - 写入 MySQL）
    # 使用 ID 1
    profile_manager.update_user_interests("1", "I want to learn advanced python concurrency")
    
    # 推荐 (现在会去 Milvus 检索)
    trace_id_1 = "trace_abc_1"
    print(f"\nRequesting recommendation for user_1 (Trace: {trace_id_1})...")
    recommendations = content_service.recommend("1", trace_id_1)
    
    if not recommendations:
        print("No recommendations found. Did you run 'python app/init_data.py' to seed Milvus?")
    
    for i, res in enumerate(recommendations):
        print(f"  [{i+1}] {res.item.content} (Score: {res.item.score:.2f}) - Reason: {res.explanation}")
        
    # 反馈（验证）
    if recommendations:
        feedback_service.submit_feedback(trace_id_1, recommendations[0].item.item_id, "click")

    print("\n=== 场景 2: 相关查询推荐 ===")
    current_query = "How to optimize RAG?"
    trace_id_2 = "trace_abc_2"
    
    print(f"Current Query: {current_query}")
    next_queries = query_service.recommend_next_queries(current_query, trace_id_2)
    
    print("推荐的下一个查询：")
    for i, q in enumerate(next_queries):
        print(f"  [{i+1}] {q}")

    print("\n=== 验证：策略报告 ===")
    # 在真实场景中，这将聚合来自数据库的数据
    report = feedback_service.get_strategy_report("v1")
    print(f"Strategy Report: {report}")

if __name__ == "__main__":
    main()
