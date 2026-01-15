# 智能推荐 API 使用指南

## 📋 目录

1. [快速开始](#快速开始)
2. [API 端点列表](#api-端点列表)
3. [详细说明](#详细说明)
4. [使用示例](#使用示例)
5. [错误处理](#错误处理)
6. [集成建议](#集成建议)

---

## 🚀 快速开始

### 1. 启动服务

```bash
cd /home/yl/yl/cms/chatbot/rag
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 访问 API 文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. 快速测试

运行测试脚本：
```bash
python test_recommender_api.py
```

或使用 curl：
```bash
curl http://localhost:8000/api/v1/recommender/health
```

---

## 📍 API 端点列表

| 端点 | 方法 | 路径 | 功能 |
|------|------|------|------|
| 健康检查 | GET | `/api/v1/recommender/health` | 检查服务状态 |
| 内容推荐 | POST | `/api/v1/recommender/content` | 获取个性化内容推荐 |
| 查询推荐 | POST | `/api/v1/recommender/query` | 获取相关查询推荐 |

---

## 📖 详细说明

### 1. 健康检查接口

**用途**: 监控推荐服务的运行状态

**请求**:
```http
GET /api/v1/recommender/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "service": "recommender",
  "timestamp": "2026-01-14T12:00:00",
  "endpoints": {
    "content_recommend": "/api/v1/recommender/content",
    "query_recommend": "/api/v1/recommender/query"
  }
}
```

---

### 2. 内容推荐接口

**用途**: 基于用户画像返回个性化推荐内容

**请求**:
```http
POST /api/v1/recommender/content
Content-Type: application/json

{
  "user_id": "user_123",
  "trace_id": "trace_abc_123"  // 可选，用于日志追踪
}
```

**参数说明**:
- `user_id` (必填): 用户唯一标识符
- `trace_id` (可选): 追踪ID，用于日志关联和问题排查。如不提供，系统自动生成

**响应示例**:
```json
{
  "success": true,
  "user_id": "user_123",
  "trace_id": "trace_abc_123",
  "recommendations": [
    {
      "item": {
        "item_id": "item_001",
        "content": "如何使用 FastAPI 构建 RESTful API",
        "tags": ["编程", "Python", "Web开发"],
        "score": 0.95,
        "strategy_source": "algorithm"
      },
      "explanation": "基于您对Python和Web开发的兴趣推荐"
    }
  ],
  "count": 1,
  "timestamp": "2026-01-14T12:00:00"
}
```

**推荐算法说明**:
1. **用户画像分析**: 基于用户静态标签和动态兴趣
2. **混合检索**: 使用向量相似度进行语义匹配
3. **硬过滤**: 应用地理位置和负面内容过滤
4. **软提升**: 结合热搜趋势提升相关内容
5. **多样性优化**: 使用 MMR 算法平衡相关性和多样性
6. **结果解释**: 为每个推荐生成理由说明

---

### 3. 查询推荐接口

**用途**: 根据当前查询词推荐相关的搜索词

**请求**:
```http
POST /api/v1/recommender/query
Content-Type: application/json

{
  "current_query": "FastAPI 教程",
  "trace_id": "trace_xyz_456"  // 可选
}
```

**参数说明**:
- `current_query` (必填): 用户当前输入的查询词
- `trace_id` (可选): 追踪ID，用于日志关联

**响应示例**:
```json
{
  "success": true,
  "current_query": "FastAPI 教程",
  "trace_id": "trace_xyz_456",
  "recommended_queries": [
    "FastAPI 实战项目",
    "Python Web 框架对比",
    "FastAPI 性能优化",
    "RESTful API 设计规范",
    "FastAPI 异步编程"
  ],
  "count": 5,
  "timestamp": "2026-01-14T12:00:00"
}
```

**推荐策略**:
- **槽位 0**: 精选内容（如果有配置）
- **槽位 1**: 算法相似查询（语义匹配）
- **槽位 2**: 热门搜索
- **槽位 3+**: 混合填充剩余算法结果

最多返回 5 个推荐查询，自动去重。

---

## 💡 使用示例

### Python 示例

```python
import requests

# 1. 获取内容推荐
def get_content_recommendations(user_id):
    url = "http://localhost:8000/api/v1/recommender/content"
    response = requests.post(url, json={
        "user_id": user_id
    })
    
    if response.status_code == 200:
        data = response.json()
        for rec in data['recommendations']:
            print(f"推荐: {rec['item']['content']}")
            print(f"理由: {rec['explanation']}\n")
    return response.json()

# 2. 获取查询推荐
def get_query_recommendations(query):
    url = "http://localhost:8000/api/v1/recommender/query"
    response = requests.post(url, json={
        "current_query": query
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"相关查询: {data['recommended_queries']}")
    return response.json()

# 使用
get_content_recommendations("user_123")
get_query_recommendations("FastAPI 教程")
```

### JavaScript/TypeScript 示例

```javascript
// 1. 获取内容推荐
async function getContentRecommendations(userId) {
  const response = await fetch('http://localhost:8000/api/v1/recommender/content', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      trace_id: `trace_${Date.now()}`
    })
  });
  
  const data = await response.json();
  return data.recommendations;
}

// 2. 获取查询推荐
async function getQueryRecommendations(currentQuery) {
  const response = await fetch('http://localhost:8000/api/v1/recommender/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      current_query: currentQuery
    })
  });
  
  const data = await response.json();
  return data.recommended_queries;
}

// 使用
getContentRecommendations('user_123').then(recs => {
  recs.forEach(rec => {
    console.log(`推荐: ${rec.item.content}`);
    console.log(`理由: ${rec.explanation}`);
  });
});

getQueryRecommendations('FastAPI 教程').then(queries => {
  console.log('相关查询:', queries);
});
```

### CURL 示例

```bash
# 1. 健康检查
curl -X GET "http://localhost:8000/api/v1/recommender/health"

# 2. 内容推荐
curl -X POST "http://localhost:8000/api/v1/recommender/content" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "trace_id": "test_trace_001"
  }'

# 3. 查询推荐
curl -X POST "http://localhost:8000/api/v1/recommender/query" \
  -H "Content-Type: application/json" \
  -d '{
    "current_query": "FastAPI 教程",
    "trace_id": "test_trace_002"
  }'
```

---

## ⚠️ 错误处理

### 错误响应格式

```json
{
  "detail": {
    "error_code": "ERROR_CODE",
    "error_message": "详细错误信息"
  }
}
```

### 常见错误码

| HTTP 状态码 | 错误码 | 说明 | 处理建议 |
|------------|--------|------|---------|
| 404 | USER_NOT_FOUND | 用户不存在 | 检查 user_id 是否正确 |
| 500 | INTERNAL_ERROR | 系统内部错误 | 查看日志，联系技术支持 |

### 错误处理示例

```python
import requests

try:
    response = requests.post(
        "http://localhost:8000/api/v1/recommender/content",
        json={"user_id": "invalid_user"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("推荐成功:", data['recommendations'])
    elif response.status_code == 404:
        error = response.json()['detail']
        print(f"用户不存在: {error['error_message']}")
    else:
        error = response.json()['detail']
        print(f"系统错误: {error['error_message']}")
        
except requests.exceptions.ConnectionError:
    print("无法连接到服务，请检查服务是否启动")
except Exception as e:
    print(f"未知错误: {str(e)}")
```

---

## 🔗 集成建议

### 1. RAG 系统集成

在你的 RAG 对话流程中集成推荐功能：

```python
from app.services.recommender_service import ContentRecommenderService

class RAGChatService:
    def __init__(self, recommender: ContentRecommenderService):
        self.recommender = recommender
    
    def process_query(self, user_id: str, query: str):
        # 1. 处理用户查询
        answer = self.get_rag_answer(query)
        
        # 2. 获取相关推荐
        recommendations = self.recommender.recommend(
            user_id=user_id,
            trace_id=f"chat_{user_id}_{time.time()}"
        )
        
        # 3. 组合返回
        return {
            "answer": answer,
            "recommendations": recommendations[:3]  # 只返回前3个
        }
```

### 2. 前端调用示例

```typescript
// React 组件示例
import { useState, useEffect } from 'react';

function RecommendationPanel({ userId }) {
  const [recommendations, setRecommendations] = useState([]);
  
  useEffect(() => {
    fetch('/api/v1/recommender/content', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    })
    .then(res => res.json())
    .then(data => setRecommendations(data.recommendations));
  }, [userId]);
  
  return (
    <div className="recommendations">
      <h3>为你推荐</h3>
      {recommendations.map(rec => (
        <div key={rec.item.item_id} className="rec-item">
          <h4>{rec.item.content}</h4>
          <p className="explanation">{rec.explanation}</p>
          <span className="score">相关度: {rec.item.score.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}
```

### 3. 性能优化建议

- **缓存推荐结果**: 对于同一用户，可以缓存推荐结果 5-10 分钟
- **异步调用**: 推荐接口可以异步调用，不阻塞主流程
- **批量请求**: 如需为多个用户推荐，考虑实现批量接口
- **超时设置**: 设置合理的请求超时时间（建议 3-5 秒）

```python
# 带超时的请求示例
import requests

response = requests.post(
    url,
    json=payload,
    timeout=3  # 3秒超时
)
```

---

## 🎯 最佳实践

1. **始终传入 trace_id**: 便于问题排查和性能分析
2. **处理所有异常**: 推荐服务失败不应影响主业务流程
3. **监控推荐质量**: 记录用户对推荐内容的反馈
4. **A/B 测试**: 通过实验配置测试不同推荐策略
5. **日志记录**: 记录每次推荐请求的关键信息

---

## 📞 技术支持

如遇到问题，请提供以下信息：
- 请求的 trace_id
- 完整的错误信息
- 请求时间和用户ID
- 期望的行为描述

查看服务日志：
```bash
# 查看最近的推荐日志
grep "ContentRecommender\|QueryRecommender" app.log
```

---

**最后更新**: 2026-01-14  
**API 版本**: v1.0.0

