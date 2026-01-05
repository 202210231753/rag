import sys
import os
import random
import uuid

# 将项目根目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from chatbot.rag.app.data.models import UserProfile, Item
from chatbot.rag.app.data.user_profile_store import UserProfileStore
from chatbot.rag.app.infra.ai_client import AIModelClient
from chatbot.rag.app.infra.vector_db import VectorDBClient

def add_user():
    """交互式添加用户到 MySQL"""
    print("\n=== 添加新用户 (MySQL) ===")
    user_id = input("请输入用户ID (例如 user_001): ").strip()
    if not user_id: return
    
    tags_str = input("请输入静态标签 (用逗号分隔, 例如 python,ai): ").strip()
    static_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    
    location = input("请输入位置 (可选): ").strip()
    
    store = UserProfileStore()
    user = UserProfile(
        user_id=user_id,
        static_tags=static_tags,
        location=location,
        negative_tags=[],
        dynamic_interests=[]
    )
    store.save(user)
    print(f"✅ 用户 {user_id} 已成功写入 MySQL!")

def add_content():
    """交互式添加内容到 Milvus"""
    print("\n=== 添加新内容 (Milvus) ===")
    content = input("请输入内容文本: ").strip()
    if not content: return
    
    tags_str = input("请输入标签 (用逗号分隔): ").strip()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    
    # 初始化客户端
    print("正在加载 AI 模型以生成向量...")
    ai_client = AIModelClient()
    vector_db = VectorDBClient(collection_name="rag_items")
    
    # 生成向量
    vector = ai_client.get_embedding(content)
    
    # 生成唯一ID
    item_id = str(uuid.uuid4())
    
    item = Item(
        item_id=item_id,
        content=content,
        tags=tags,
        vector=vector
    )
    
    # 写入
    vector_db.insert_items([item])
    print(f"✅ 内容已写入 Milvus! ID: {item_id}")

def add_query():
    """交互式添加查询词到 Milvus (作为推荐候选)"""
    print("\n=== 添加查询候选 (Milvus) ===")
    query = input("请输入查询词文本: ").strip()
    if not query: return
    
    print("正在加载 AI 模型以生成向量...")
    ai_client = AIModelClient()
    vector_db = VectorDBClient(collection_name="rag_items")
    
    # 生成向量
    vector = ai_client.get_embedding(query)
    
    # 生成唯一ID
    item_id = f"query_{uuid.uuid4().hex[:8]}"
    
    item = Item(
        item_id=item_id,
        content=query,
        tags=["query", "suggestion"], # 自动打上 query 标签
        vector=vector
    )
    
    # 写入
    vector_db.insert_items([item])
    print(f"✅ 查询词已写入 Milvus! ID: {item_id}")

def main():
    while True:
        print("\n" + "="*30)
        print("   RAG 数据管理工具")
        print("="*30)
        print("1. 添加新用户 (MySQL)")
        print("2. 添加新内容 (Milvus)")
        print("3. 添加查询候选 (Milvus)")
        print("q. 退出")
        
        choice = input("\n请选择操作: ").strip().lower()
        
        if choice == '1':
            add_user()
        elif choice == '2':
            add_content()
        elif choice == '3':
            add_query()
        elif choice == 'q':
            print("退出。")
            break
        else:
            print("无效选项，请重试。")

if __name__ == "__main__":
    main()

