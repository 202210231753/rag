import requests
import json
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.document import Document, DocStatus
from app.models.chunk import Chunk

# --- 配置 ---
API_BASE = "http://127.0.0.1:8001/api/v1/intervention"
DB_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_SERVER}:{settings.DB_PORT}/{settings.DB_NAME}"

# --- 数据库连接 ---
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def setup_data():
    """造假数据"""
    print("🛠️  正在初始化测试数据...")
    
    # [新增] 自动建表 (仅在测试时使用)
    from app.core.database import Base
    # 确保所有 Model 都被导入，否则 create_all 找不到它们
    import app.models.document
    import app.models.chunk
    print("📦 正在检查并创建数据库表...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. 插入 Document
        doc = Document(
            id=9999,
            filename="测试合同_AUTO_TEST.pdf",
            file_path="/tmp/test.pdf",
            file_hash="hash_123456",
            status=DocStatus.COMPLETED,
            chunk_count=1
        )
        db.add(doc)
        db.commit()

        # 2. 插入 Chunk
        chunk = Chunk(
            id=8888,
            document_id=9999,
            content="原文：甲方应支付乙方100元。",
            vector_id=None, # 暂时不测 Milvus 的手动插入，太复杂，主要测 API 逻辑
            index=0,
            is_active=True
        )
        db.add(chunk)
        db.commit()
        print("✅ 测试数据插入成功 (Doc ID: 9999, Chunk ID: 8888)")
    except Exception as e:
        print(f"⚠️  数据初始化可能已存在或失败: {e}")
        db.rollback()
    finally:
        db.close()

def test_get_documents():
    """测试获取列表"""
    print("\n🧪 [Test 1] 获取文档列表...")
    resp = requests.get(f"{API_BASE}/documents")
    if resp.status_code == 200:
        data = resp.json()
        found = any(d['id'] == 9999 for d in data)
        if found:
            print("✅ PASS: 成功在列表中找到测试文档")
        else:
            print("❌ FAIL: 列表中未找到测试文档")
    else:
        print(f"❌ FAIL: API 报错 {resp.status_code} - {resp.text}")

def test_get_chunks():
    """测试获取切片"""
    print("\n🧪 [Test 2] 获取切片详情...")
    resp = requests.get(f"{API_BASE}/documents/9999/chunks")
    if resp.status_code == 200:
        data = resp.json()
        if len(data) > 0 and data[0]['id'] == 8888:
            print(f"✅ PASS: 成功获取切片内容: {data[0]['content']}")
        else:
            print("❌ FAIL: 切片数据不匹配")
    else:
        print(f"❌ FAIL: API 报错 {resp.status_code}")

def test_update_chunk():
    """测试干预修改"""
    print("\n🧪 [Test 3] 执行数据干预 (修改文本)...")
    new_content = "修正后：甲方应支付乙方1000万！"
    payload = {"content": new_content}
    
    resp = requests.put(f"{API_BASE}/chunks/8888", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        if data['content'] == new_content:
            print("✅ PASS: API 返回更新后的内容")
            
            # 二次验证：查数据库
            db = SessionLocal()
            chunk = db.query(Chunk).filter(Chunk.id == 8888).first()
            if chunk.content == new_content:
                print("✅ PASS: 数据库内容已同步更新")
            else:
                print("❌ FAIL: 数据库内容未更新")
            db.close()
        else:
            print("❌ FAIL: API 返回内容未更新")
    else:
        print(f"❌ FAIL: 干预失败 {resp.status_code} - {resp.text}")

def test_delete_document():
    """测试删除"""
    print("\n🧪 [Test 4] 删除文档及级联数据...")
    resp = requests.delete(f"{API_BASE}/documents/9999")
    
    if resp.status_code == 200:
        print("✅ PASS: API 删除成功")
        
        # 验证数据库
        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == 9999).first()
        chunk = db.query(Chunk).filter(Chunk.id == 8888).first()
        db.close()
        
        if not doc and not chunk:
            print("✅ PASS: 数据库记录已彻底清除 (级联删除生效)")
        else:
            print(f"❌ FAIL: 数据库仍有残留 (Doc: {doc}, Chunk: {chunk})")
    else:
        print(f"❌ FAIL: 删除失败 {resp.status_code}")

if __name__ == "__main__":
    # 确保服务已启动
    try:
        requests.get(f"{API_BASE}/documents", timeout=2)
    except:
        print("❌ 错误: 无法连接到后端服务，请先运行 'uvicorn app.main:app --reload --port 8001'")
        exit(1)

    setup_data()
    input("\n👀 [暂停 1/3] 数据已初始化。请去 DBeaver 刷新查看 'documents' 和 'chunks' 表。\n👉 确认看到数据后，按回车键继续...")

    test_get_documents()
    test_get_chunks()
    
    test_update_chunk()
    input("\n👀 [暂停 2/3] 数据已干预修改。请去 DBeaver 刷新查看 'chunks' 表的内容是否变成了'1000万'。\n👉 确认变化后，按回车键继续...")

    test_delete_document()
    print("\n🎉 测试结束！数据已清理。现在去 DBeaver 刷新，数据应该消失了。")
