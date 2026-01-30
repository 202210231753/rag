#!/usr/bin/env python
"""直接测试论文搜索API端点，不启动完整服务器。"""
import sys
sys.path.insert(0, '/home/runner/work/rag/rag')

from fastapi.testclient import TestClient
from fastapi import FastAPI

# 创建一个最小的FastAPI应用用于测试
app = FastAPI()

# 导入并注册papers路由
from app.api.v1.endpoints.papers import router
app.include_router(router, prefix="/api/v1/papers")

# 创建测试客户端
client = TestClient(app)

def test_health_endpoint():
    """测试健康检查端点。"""
    print("=" * 80)
    print("测试健康检查端点")
    print("=" * 80)
    
    response = client.get("/api/v1/papers/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "paper_search"
    
    print("✅ 健康检查通过\n")

def test_search_endpoint():
    """测试论文搜索端点。"""
    print("=" * 80)
    print("测试论文搜索端点")
    print("=" * 80)
    
    # 测试请求
    request_data = {
        "query": "基于多智能体的安全代码生成",
        "limit": 2
    }
    
    print(f"请求数据: {request_data}\n")
    
    response = client.post("/api/v1/papers/search", json=request_data)
    print(f"状态码: {response.status_code}")
    
    assert response.status_code == 200
    
    result = response.json()
    print(f"状态码: {result['code']}")
    print(f"消息: {result['msg']}")
    print(f"查询: {result['data']['query']}")
    print(f"数据源: {result['data']['source']}")
    print(f"找到论文数: {result['data']['total']}\n")
    
    # 显示论文详情
    for i, paper in enumerate(result['data']['papers'], 1):
        print(f"{i}. {paper['title']}")
        print(f"   会议: {paper['venue']} ({paper['year']})")
        print(f"   作者: {', '.join([a['name'] for a in paper['authors']])}")
        print(f"   引用数: {paper['citationCount']}")
        if paper.get('arxivId'):
            print(f"   arXiv: {paper['arxivId']}")
        print()
    
    assert result['code'] == 200
    assert result['data']['total'] > 0
    assert len(result['data']['papers']) > 0
    
    print("✅ 论文搜索测试通过\n")

def test_search_with_filters():
    """测试带筛选条件的论文搜索。"""
    print("=" * 80)
    print("测试带筛选条件的论文搜索")
    print("=" * 80)
    
    request_data = {
        "query": "multi-agent secure code generation",
        "limit": 3,
        "yearFrom": 2020,
        "yearTo": 2024
    }
    
    print(f"请求数据: {request_data}\n")
    
    response = client.post("/api/v1/papers/search", json=request_data)
    assert response.status_code == 200
    
    result = response.json()
    print(f"找到论文数: {result['data']['total']}")
    
    # 验证年份筛选
    for paper in result['data']['papers']:
        print(f"- {paper['title']} ({paper['year']})")
        if paper['year']:
            assert 2020 <= paper['year'] <= 2024, f"年份 {paper['year']} 超出范围"
    
    print("\n✅ 筛选条件测试通过\n")

if __name__ == "__main__":
    try:
        test_health_endpoint()
        test_search_endpoint()
        test_search_with_filters()
        
        print("=" * 80)
        print("🎉 所有测试通过！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
