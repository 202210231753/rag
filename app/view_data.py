import sys
import os
import json
from sqlalchemy import text

# 将项目根目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

# 注意：这里不再导入 sql_models.UserProfileModel，因为那个模型和数据库不匹配
from chatbot.rag.app.core.database import SessionLocal
from chatbot.rag.app.infra.vector_db import VectorDBClient

def list_users():
    """列出 MySQL 中的所有用户 (适配旧表结构 + 关联表)"""
    print("\n=== MySQL 用户列表 (Join rag_user_traits) ===")
    db = SessionLocal()
    try:
        # 使用 Left Join 查询旧表和新表
        sql = """
        SELECT 
            u.id, u.gender, u.age, u.city, 
            r.static_tags, r.dynamic_interests
        FROM user_profiles u
        LEFT JOIN rag_user_traits r ON u.id = r.user_id
        LIMIT 20
        """
        result = db.execute(text(sql))
        rows = result.fetchall()
        
        if not rows:
            print("没有用户数据。")
            return
            
        # 打印表头
        print(f"{'ID':<5} {'性别':<5} {'年龄':<5} {'城市':<8} {'静态标签':<25} {'动态兴趣'}")
        print("-" * 100)
        
        for row in rows:
            # row: (id, gender, age, city, static_tags, dynamic_interests)
            uid = str(row[0])
            gender = row[1] if row[1] else "-"
            age = str(row[2]) if row[2] else "-"
            city = row[3] if row[3] else "-"
            
            # 辅助函数：处理 JSON 并转字符串
            def format_json_field(val):
                if val is None: return "(无)"
                try:
                    if isinstance(val, str):
                        lst = json.loads(val)
                    else:
                        lst = val
                    return ",".join(lst)
                except:
                    return str(val)

            static_str = format_json_field(row[4])
            dynamic_str = format_json_field(row[5])

            # 截断过长的显示
            if len(static_str) > 23: static_str = static_str[:20] + "..."
            if len(dynamic_str) > 30: dynamic_str = dynamic_str[:27] + "..."
                
            print(f"{uid:<5} {gender:<5} {age:<5} {city:<8} {static_str:<25} {dynamic_str}")
            
    except Exception as e:
        print(f"查询 MySQL 失败: {e}")
    finally:
        db.close()

def list_milvus_items(limit=20):
    """列出 Milvus 中的数据 (Top N)"""
    print(f"\n=== Milvus 内容列表 (前 {limit} 条) ===")
    
    try:
        client = VectorDBClient(collection_name="rag_items")
        # Milvus 的 query 接口可以直接查所有数据（不带向量）
        results = client.collection.query(
            expr="item_id > 0",  # 假设 auto_id 从 1 开始
            output_fields=["source_id", "content", "tags"],
            limit=limit
        )
        
        if not results:
            print("Milvus 中没有数据。")
            return

        print(f"{'ID':<10} {'内容片段':<40} {'标签'}")
        print("-" * 70)
        for item in results:
            content_preview = item['content'][:35] + "..." if len(item['content']) > 35 else item['content']
            # tags 解析逻辑
            try:
                tags = json.loads(item['tags'])
            except:
                tags = item['tags']
                
            print(f"{str(item['source_id']):<10} {content_preview:<40} {tags}")
            
    except Exception as e:
        print(f"查询 Milvus 失败: {e}")
        print("提示: 如果刚启动 Milvus，可能需要先运行 init_data.py 来初始化集合。")

def main():
    while True:
        print("\n" + "="*30)
        print("   RAG 数据查看器 (已适配旧表)")
        print("="*30)
        print("1. 查看所有用户 (MySQL)")
        print("2. 查看内容列表 (Milvus)")
        print("q. 退出")
        
        choice = input("\n请选择操作: ").strip().lower()
        
        if choice == '1':
            list_users()
        elif choice == '2':
            list_milvus_items()
        elif choice == 'q':
            break
        else:
            print("无效选项。")

if __name__ == "__main__":
    main()
