#!/usr/bin/env python
"""测试论文搜索API的脚本。"""
import sys
sys.path.insert(0, '/home/runner/work/rag/rag')

from app.services.paper_search_service import paper_search_service
from app.schemas.paper_schema import PaperSearchRequest

def test_paper_search():
    """测试论文搜索功能。"""
    print("=" * 80)
    print("测试论文搜索服务")
    print("=" * 80)
    
    # 测试中文查询：基于多智能体的安全代码生成
    print("\n【测试1】中文查询：基于多智能体的安全代码生成")
    print("-" * 80)
    request = PaperSearchRequest(
        query="基于多智能体的安全代码生成",
        limit=2
    )
    
    result = paper_search_service.search_papers(request)
    print(f"查询: {result.query}")
    print(f"数据源: {result.source}")
    print(f"找到 {result.total} 篇论文\n")
    
    for i, paper in enumerate(result.papers, 1):
        print(f"{i}. 【{paper.venue}】{paper.title}")
        print(f"   作者: {', '.join([a.name for a in paper.authors])}")
        print(f"   年份: {paper.year} | 引用数: {paper.citation_count}")
        if paper.arxiv_id:
            print(f"   arXiv: https://arxiv.org/abs/{paper.arxiv_id}")
        if paper.abstract:
            print(f"   摘要: {paper.abstract[:150]}...")
        print()
    
    # 测试英文查询：multi-agent secure code generation
    print("\n【测试2】英文查询：multi-agent secure code generation")
    print("-" * 80)
    request = PaperSearchRequest(
        query="multi-agent secure code generation",
        limit=3,
        year_from=2020
    )
    
    result = paper_search_service.search_papers(request)
    print(f"查询: {result.query}")
    print(f"数据源: {result.source}")
    print(f"找到 {result.total} 篇论文\n")
    
    for i, paper in enumerate(result.papers, 1):
        print(f"{i}. 【{paper.venue}】{paper.title}")
        print(f"   作者: {', '.join([a.name for a in paper.authors])}")
        print(f"   年份: {paper.year} | 引用数: {paper.citation_count}")
        if paper.url:
            print(f"   链接: {paper.url}")
        print()
    
    print("=" * 80)
    print("✅ 论文搜索服务测试通过！")
    print("=" * 80)

if __name__ == "__main__":
    test_paper_search()
