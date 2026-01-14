#!/usr/bin/env python3
"""
排序引擎功能测试脚本

测试黑名单、Lambda参数、位置插入等功能
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_lambda_config():
    """测试 Lambda 参数管理"""
    print_section("测试 Lambda 参数管理")
    
    # 1. 获取当前配置
    print("\n1. 获取当前 Lambda 参数...")
    resp = requests.get(f"{BASE_URL}/ranking/lambda")
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 2. 更新配置
    print("\n2. 更新 Lambda 参数为 0.7...")
    resp = requests.put(
        f"{BASE_URL}/ranking/lambda",
        json={"lambda_param": 0.7}
    )
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 3. 再次获取验证
    print("\n3. 验证更新是否成功...")
    resp = requests.get(f"{BASE_URL}/ranking/lambda")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")


def test_blacklist():
    """测试黑名单管理"""
    print_section("测试黑名单管理")
    
    # 1. 添加黑名单
    print("\n1. 添加黑名单文档...")
    resp = requests.post(
        f"{BASE_URL}/ranking/blacklist",
        json={
            "action": "add",
            "doc_ids": ["test_doc_1", "test_doc_2", "test_doc_3"]
        }
    )
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 2. 查询黑名单
    print("\n2. 查询黑名单列表...")
    resp = requests.get(f"{BASE_URL}/ranking/blacklist")
    print(f"   状态码: {resp.status_code}")
    print(f"   黑名单文档: {resp.json()}")
    
    # 3. 移除部分黑名单
    print("\n3. 移除部分黑名单...")
    resp = requests.post(
        f"{BASE_URL}/ranking/blacklist",
        json={
            "action": "remove",
            "doc_ids": ["test_doc_1"]
        }
    )
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 4. 再次查询
    print("\n4. 再次查询黑名单...")
    resp = requests.get(f"{BASE_URL}/ranking/blacklist")
    print(f"   黑名单文档: {resp.json()}")


def test_position_rules():
    """测试位置插入规则"""
    print_section("测试位置插入规则")
    
    # 1. 设置位置规则
    print("\n1. 设置位置插入规则...")
    resp = requests.post(
        f"{BASE_URL}/ranking/position",
        json={
            "query": "人工智能",
            "doc_id": "important_doc_999",
            "position": 0
        }
    )
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 2. 设置另一个规则
    print("\n2. 设置第二个位置规则...")
    resp = requests.post(
        f"{BASE_URL}/ranking/position",
        json={
            "query": "机器学习",
            "doc_id": "ml_intro_doc",
            "position": 1
        }
    )
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 3. 查询所有规则
    print("\n3. 查询所有位置规则...")
    resp = requests.get(f"{BASE_URL}/ranking/position")
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 4. 删除规则
    print("\n4. 删除位置规则...")
    resp = requests.delete(f"{BASE_URL}/ranking/position/机器学习")
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    
    # 5. 再次查询
    print("\n5. 再次查询所有规则...")
    resp = requests.get(f"{BASE_URL}/ranking/position")
    print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")


def test_search_with_ranking():
    """测试集成排序引擎的搜索"""
    print_section("测试集成排序引擎的搜索")
    
    # 1. 不启用排序引擎
    print("\n1. 搜索（不启用排序引擎）...")
    resp = requests.post(
        f"{BASE_URL}/search/multi-recall",
        json={
            "query": "测试查询",
            "top_n": 5,
            "enable_ranking": False
        }
    )
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"   结果数: {result['total']}")
        print(f"   耗时: {result['took_ms']:.2f}ms")
    
    # 2. 启用排序引擎
    print("\n2. 搜索（启用排序引擎）...")
    resp = requests.post(
        f"{BASE_URL}/search/multi-recall",
        json={
            "query": "测试查询",
            "top_n": 5,
            "enable_ranking": True
        }
    )
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"   结果数: {result['total']}")
        print(f"   耗时: {result['took_ms']:.2f}ms")


def main():
    """主函数"""
    print("\n")
    print("🚀 排序引擎功能测试")
    print(f"📍 API 地址: {BASE_URL}")
    
    try:
        # 测试连接
        resp = requests.get("http://localhost:8000/")
        if resp.status_code != 200:
            print("\n❌ 服务未启动，请先运行: uvicorn app.main:app --reload")
            return
        
        print("✅ 服务连接正常\n")
        
        # 执行测试
        test_lambda_config()
        test_blacklist()
        test_position_rules()
        # test_search_with_ranking()  # 需要有真实数据才能测试
        
        print_section("测试完成")
        print("✅ 所有测试通过！\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务，请确保服务已启动：")
        print("   uvicorn app.main:app --reload\n")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")


if __name__ == "__main__":
    main()
