# test_env_async.py
import os
import logging
import sys
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

# 确保你有 OPENAI_API_KEY
if not os.getenv("OPENAI_API_KEY"):
    print("❌ 错误: 请在 .env 文件中设置 OPENAI_API_KEY")
    exit(1)

async def test_rag_async():
    print("🚀 开始异步测试 LlamaIndex + Milvus 环境...")
    
    # 1. 准备测试数据
    doc = Document(text="FastAPI 是一个高性能的 Web 框架，并行开发效率很高。")
    print("✅ 模拟文档创建成功")
    
    # 2. 连接 Milvus
    vector_store = MilvusVectorStore(
        uri="http://localhost:19530",
        collection_name="test_collection",
        dim=1536,
        overwrite=True
    )
    print("✅ MilvusVectorStore 初始化成功")
    
    # 3. 创建存储上下文
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # 4. 生成索引
    print("⏳ 正在调用 OpenAI Embedding 并存入 Milvus...")
    index = VectorStoreIndex.from_documents(
        [doc], 
        storage_context=storage_context
    )
    print("✅ 索引构建成功！数据已存入 Milvus")
    
    # 5. 测试查询
    query_engine = index.as_query_engine()
    response = await query_engine.aquery("FastAPI 的优点是什么？")  # 使用异步查询
    print(f"\n🤖 回答结果: {response}\n")

if __name__ == "__main__":
    try:
        asyncio.run(test_rag_async())
        print("🎉 恭喜！异步环境配置完美，没有版本冲突。")
    except Exception as e:
        print(f"\n❌ 异步环境测试失败: {e}")
