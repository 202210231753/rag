[根目录](../../CLAUDE.md) > [app](../CLAUDE.md) > **rag**

---

# RAG 模块文档

## 模块职责

`rag` 模块封装 RAG（Retrieval-Augmented Generation）引擎的底层实现细节，包括自定义检索器、向量存储管理、文档处理流水线等。该模块为 Services 层提供可复用的 RAG 组件。

## 入口与启动

### 模块导入方式
```python
from app.rag.retrievers import CustomRetriever, MilvusRetriever
from app.rag import index_builder, query_engine
```

### 模块职责边界
- **RAG 模块**: 提供 RAG 引擎的基础组件（检索器、索引构建器等）
- **Services 模块**: 编排 RAG 组件，实现业务逻辑
- **API 模块**: 处理 HTTP 请求，调用 Services

## 对外接口

### Retrievers（待实现）
**位置**: `app/rag/retrievers.py`
**状态**: 空文件（1 行）
**职责**: 自定义检索器实现

**建议实现**:
```python
from typing import List, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.vector_stores.milvus import MilvusVectorStore
import os

class MilvusRetriever(BaseRetriever):
    """
    基于 Milvus 的自定义检索器

    支持多集合检索、自定义过滤等高级功能
    """

    def __init__(
        self,
        collection_name: str,
        top_k: int = 5,
        milvus_host: Optional[str] = None,
        milvus_port: Optional[int] = None
    ):
        self.collection_name = collection_name
        self.top_k = top_k
        self.milvus_host = milvus_host or os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = milvus_port or int(os.getenv("MILVUS_PORT", "19530"))

        # 初始化 Milvus 向量存储
        self.vector_store = MilvusVectorStore(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            collection_name=collection_name,
            dim=1536
        )

        # 创建索引
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        执行检索
        """
        retriever = self.index.as_retriever(similarity_top_k=self.top_k)
        nodes = retriever.retrieve(query_bundle.query_str)
        return nodes

class HybridRetriever(BaseRetriever):
    """
    混合检索器

    结合向量检索和关键词检索（BM25）
    """

    def __init__(
        self,
        vector_retriever: BaseRetriever,
        bm25_retriever: Optional[BaseRetriever] = None,
        alpha: float = 0.7  # 向量检索权重
    ):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.alpha = alpha

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        混合检索实现
        """
        # 向量检索
        vector_nodes = self.vector_retriever.retrieve(query_bundle.query_str)

        if self.bm25_retriever is None:
            return vector_nodes

        # BM25 检索
        bm25_nodes = self.bm25_retriever.retrieve(query_bundle.query_str)

        # 合并结果（加权平均）
        merged_nodes = self._merge_results(vector_nodes, bm25_nodes)
        return merged_nodes

    def _merge_results(
        self,
        vector_nodes: List[NodeWithScore],
        bm25_nodes: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """
        合并检索结果
        """
        # TODO: 实现结果合并逻辑
        # 使用加权平均或 Reciprocal Rank Fusion
        pass

class FilteredRetriever(BaseRetriever):
    """
    带过滤条件的检索器

    支持根据元数据过滤（如文档类型、时间范围等）
    """

    def __init__(
        self,
        base_retriever: BaseRetriever,
        metadata_filters: dict
    ):
        self.base_retriever = base_retriever
        self.metadata_filters = metadata_filters

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        带过滤的检索
        """
        nodes = self.base_retriever.retrieve(query_bundle.query_str)

        # 过滤节点
        filtered_nodes = [
            node for node in nodes
            if self._match_filters(node)
        ]

        return filtered_nodes

    def _match_filters(self, node: NodeWithScore) -> bool:
        """
        检查节点是否匹配过滤条件
        """
        for key, value in self.metadata_filters.items():
            if node.node.metadata.get(key) != value:
                return False
        return True
```

### Index Builder（建议新增）
**位置**: `app/rag/index_builder.py`
**状态**: 不存在
**职责**: 索引构建和管理

**建议实现**:
```python
from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore
from typing import List
import os

class IndexBuilder:
    """
    索引构建器

    负责创建和管理 Milvus 索引
    """

    def __init__(
        self,
        milvus_host: str = None,
        milvus_port: int = None
    ):
        self.milvus_host = milvus_host or os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = milvus_port or int(os.getenv("MILVUS_PORT", "19530"))

    def create_index(
        self,
        documents: List[Document],
        collection_name: str,
        dim: int = 1536,
        overwrite: bool = False
    ) -> VectorStoreIndex:
        """
        创建索引
        """
        # 创建向量存储
        vector_store = MilvusVectorStore(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            collection_name=collection_name,
            dim=dim,
            overwrite=overwrite
        )

        # 创建存储上下文
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store
        )

        # 从文档创建索引
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )

        return index

    def load_index(self, collection_name: str) -> VectorStoreIndex:
        """
        加载已存在的索引
        """
        vector_store = MilvusVectorStore(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            collection_name=collection_name,
            dim=1536
        )

        index = VectorStoreIndex.from_vector_store(vector_store)
        return index

    def delete_collection(self, collection_name: str):
        """
        删除 Milvus 集合
        """
        # TODO: 实现集合删除逻辑
        pass
```

### Query Engine（建议新增）
**位置**: `app/rag/query_engine.py`
**状态**: 不存在
**职责**: 查询引擎配置和管理

**建议实现**:
```python
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import BaseQueryEngine
from app.rag.retrievers import MilvusRetriever

class QueryEngineFactory:
    """
    查询引擎工厂

    根据不同场景创建不同配置的查询引擎
    """

    @staticmethod
    def create_simple_query_engine(
        index: VectorStoreIndex,
        top_k: int = 5
    ) -> BaseQueryEngine:
        """
        创建简单查询引擎
        """
        return index.as_query_engine(
            similarity_top_k=top_k,
            response_mode="compact"
        )

    @staticmethod
    def create_chat_query_engine(
        index: VectorStoreIndex,
        memory_limit: int = 10
    ) -> BaseQueryEngine:
        """
        创建对话式查询引擎（带历史记忆）
        """
        return index.as_chat_engine(
            chat_mode="condense_question",
            memory_limit=memory_limit
        )

    @staticmethod
    def create_streaming_query_engine(
        index: VectorStoreIndex,
        top_k: int = 5
    ) -> BaseQueryEngine:
        """
        创建流式查询引擎
        """
        return index.as_query_engine(
            similarity_top_k=top_k,
            streaming=True
        )
```

## 关键依赖与配置

### 外部依赖
- **LlamaIndex Core** (>=0.10.0): RAG 框架核心
- **LlamaIndex Vector Stores Milvus**: Milvus 集成
- **LlamaIndex Embeddings OpenAI**: OpenAI Embedding
- **LlamaIndex LLMs OpenAI**: OpenAI LLM

### LlamaIndex 全局配置
建议在 `app/core/config.py` 中统一配置：
```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

def setup_llama_index():
    """初始化 LlamaIndex 全局配置"""
    Settings.llm = OpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7
    )

    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-ada-002"
    )

    Settings.chunk_size = 512
    Settings.chunk_overlap = 50
```

### Milvus 配置
- **URI**: `http://{MILVUS_HOST}:{MILVUS_PORT}`
- **向量维度**: 1536（OpenAI text-embedding-ada-002）
- **相似度度量**: L2（欧氏距离）或 IP（内积）

## 数据模型

### Node Schema
LlamaIndex 中的基本数据单元：
```python
from llama_index.core.schema import TextNode

node = TextNode(
    text="文档内容",
    metadata={
        "document_id": 123,
        "chunk_index": 0,
        "source": "document.pdf"
    }
)
```

### Document Schema
```python
from llama_index.core import Document

document = Document(
    text="文档全文",
    metadata={
        "filename": "example.pdf",
        "page_count": 10
    }
)
```

## 测试与质量

### 当前测试覆盖
- **单元测试**: 无
- **环境测试**: `test_env.py` 间接测试

### 测试建议

#### 检索器测试
```python
def test_milvus_retriever():
    retriever = MilvusRetriever(
        collection_name="test_collection",
        top_k=5
    )

    query = "What is FastAPI?"
    nodes = retriever.retrieve(query)

    assert len(nodes) <= 5
    assert all(node.score >= 0 for node in nodes)
```

#### 索引构建测试
```python
def test_index_builder():
    builder = IndexBuilder()

    documents = [
        Document(text="Test document 1"),
        Document(text="Test document 2")
    ]

    index = builder.create_index(
        documents,
        collection_name="test_collection",
        overwrite=True
    )

    assert index is not None
```

## 常见问题 (FAQ)

### Q1: 如何选择合适的检索器？
A:
- **简单场景**: 使用 `MilvusRetriever`
- **需要关键词匹配**: 使用 `HybridRetriever`
- **需要过滤**: 使用 `FilteredRetriever`

### Q2: 如何调优检索效果？
A:
1. 调整 `top_k` 参数（相关文档数量）
2. 调整 `chunk_size` 和 `chunk_overlap`
3. 尝试不同的 Embedding 模型
4. 使用混合检索（向量 + BM25）

### Q3: 如何处理多语言检索？
A: 使用支持多语言的 Embedding 模型，如 OpenAI 的 `text-embedding-ada-002`。

### Q4: 如何实现重排序（Reranking）？
A: 使用 LlamaIndex 的 Reranker：
```python
from llama_index.core.postprocessor import SimilarityPostprocessor

query_engine = index.as_query_engine(
    node_postprocessors=[
        SimilarityPostprocessor(similarity_cutoff=0.7)
    ]
)
```

### Q5: 如何监控检索性能？
A: 记录检索时间、相似度分数等指标：
```python
import time

start = time.time()
nodes = retriever.retrieve(query)
duration = time.time() - start

print(f"检索耗时: {duration}秒")
print(f"平均相似度: {sum(n.score for n in nodes) / len(nodes)}")
```

## 相关文件清单

### 已存在文件
- `/home/yl/yl/wy/rag/rag_project/app/rag/retrievers.py` (1 行，空实现)
- `app/rag/__init__.py`

### 建议新增文件
- `app/rag/index_builder.py`: 索引构建器
- `app/rag/query_engine.py`: 查询引擎工厂
- `app/rag/document_processor.py`: 文档处理器
- `app/rag/prompt_templates.py`: 提示词模板

## 变更记录 (Changelog)

### 2025-12-18 15:00:06
- 创建 rag 模块文档
- 发现 `retrievers.py` 为空实现
- 提供了完整的检索器、索引构建器、查询引擎实现建议
- 建议新增多个 RAG 组件文件

---

## 下一步建议

### 立即优先级（必须实现）
1. **实现 MilvusRetriever**:
   - 基于 Milvus 的基础检索器
   - 支持自定义 top_k 和过滤条件

2. **实现 IndexBuilder**:
   - 索引创建和加载
   - 集合管理（创建、删除）

3. **实现 QueryEngineFactory**:
   - 简单查询引擎
   - 对话式查询引擎

### 短期优先级
1. 实现混合检索器（HybridRetriever）
2. 实现过滤检索器（FilteredRetriever）
3. 添加文档处理流水线（DocumentProcessor）
4. 实现自定义提示词模板

### 中期优先级
1. 实现重排序（Reranking）
2. 实现查询结果缓存
3. 添加检索性能监控
4. 实现多集合检索
5. 支持异步检索
