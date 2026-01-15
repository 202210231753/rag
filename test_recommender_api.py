"""
智能推荐 API 使用示例和测试脚本

使用方法：
1. 启动服务：uvicorn app.main:app --reload --port 8001
2. 运行此测试脚本：python test_recommender_api.py
   或指定端口：python test_recommender_api.py 8001
3. 或者访问 Swagger UI：http://localhost:8001/docs
"""

import requests
import json
import sys
from datetime import datetime

# API 基础地址 (支持命令行参数指定端口)
DEFAULT_PORT = 8001
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
BASE_URL = f"http://localhost:{PORT}/api/v1/recommender"

print(f"📍 使用端口: {PORT}")
print(f"📍 API 地址: {BASE_URL}")


def test_content_recommendation():
    """测试内容推荐接口"""
    print("\n" + "="*60)
    print("🔍 测试 1: 内容推荐接口")
    print("="*60)
    
    url = f"{BASE_URL}/content"
    payload = {
        "user_id": "user_123",
        "trace_id": "test_trace_001"
    }
    
    print(f"\n请求 URL: {url}")
    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 请求成功！")
            print(f"\n推荐结果:")
            print(f"- 用户ID: {result['user_id']}")
            print(f"- 追踪ID: {result['trace_id']}")
            print(f"- 推荐数量: {result['count']}")
            print(f"- 响应时间: {result['timestamp']}")
            
            if result['recommendations']:
                print(f"\n推荐内容详情:")
                for i, rec in enumerate(result['recommendations'][:3], 1):
                    item = rec['item']
                    print(f"\n  [{i}] {item['item_id']}")
                    print(f"      内容: {item['content'][:50]}...")
                    print(f"      分数: {item['score']:.3f}")
                    print(f"      来源: {item['strategy_source']}")
                    print(f"      理由: {rec['explanation']}")
            
            return True
        else:
            print(f"❌ 请求失败")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_query_recommendation():
    """测试查询推荐接口"""
    print("\n" + "="*60)
    print("🔍 测试 2: 查询推荐接口")
    print("="*60)
    
    url = f"{BASE_URL}/query"
    payload = {
        "current_query": "FastAPI 教程",
        "trace_id": "test_trace_002"
    }
    
    print(f"\n请求 URL: {url}")
    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 请求成功！")
            print(f"\n推荐结果:")
            print(f"- 当前查询: {result['current_query']}")
            print(f"- 追踪ID: {result['trace_id']}")
            print(f"- 推荐数量: {result['count']}")
            print(f"- 响应时间: {result['timestamp']}")
            
            if result['recommended_queries']:
                print(f"\n推荐的相关查询:")
                for i, query in enumerate(result['recommended_queries'], 1):
                    print(f"  [{i}] {query}")
            
            return True
        else:
            print(f"❌ 请求失败")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_health_check():
    """测试健康检查接口"""
    print("\n" + "="*60)
    print("🔍 测试 3: 健康检查接口")
    print("="*60)
    
    url = f"{BASE_URL}/health"
    print(f"\n请求 URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 服务健康！")
            print(f"\n服务信息:")
            print(f"- 状态: {result['status']}")
            print(f"- 服务名: {result['service']}")
            print(f"- 时间戳: {result['timestamp']}")
            print(f"\n可用端点:")
            for name, path in result['endpoints'].items():
                print(f"  - {name}: {path}")
            
            return True
        else:
            print(f"❌ 服务异常")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        print(f"💡 提示: 请确保服务已启动")
        print(f"   启动命令: uvicorn app.main:app --reload --port {PORT}")
        return False


def print_curl_examples():
    """打印 CURL 命令示例"""
    print("\n" + "="*60)
    print("📋 CURL 命令示例")
    print("="*60)
    
    print("\n1. 内容推荐:")
    print(f"""
curl -X POST "http://localhost:{PORT}/api/v1/recommender/content" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "user_id": "user_123",
    "trace_id": "test_trace_001"
  }}'
""")
    
    print("\n2. 查询推荐:")
    print(f"""
curl -X POST "http://localhost:{PORT}/api/v1/recommender/query" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "current_query": "FastAPI 教程",
    "trace_id": "test_trace_002"
  }}'
""")
    
    print("\n3. 健康检查:")
    print(f"""
curl -X GET "http://localhost:{PORT}/api/v1/recommender/health"
""")


if __name__ == "__main__":
    print("\n" + "🚀 智能推荐 API 测试脚本")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行测试
    results = []
    results.append(("健康检查", test_health_check()))
    results.append(("内容推荐", test_content_recommendation()))
    results.append(("查询推荐", test_query_recommendation()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    print(f"\n总计: {success_count}/{len(results)} 个测试通过")
    
    # 打印 CURL 示例
    print_curl_examples()
    
    print("\n" + "="*60)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    print("\n💡 提示:")
    print(f"- 访问 Swagger UI: http://localhost:{PORT}/docs")
    print(f"- 访问 ReDoc: http://localhost:{PORT}/redoc")
    print(f"- 查看所有端点: http://localhost:{PORT}/openapi.json")
    print("\n💡 使用其他端口:")
    print("  python test_recommender_api.py 8080  # 使用 8080 端口")
    print("  python test_recommender_api.py 9000  # 使用 9000 端口")

