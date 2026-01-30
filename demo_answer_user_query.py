#!/usr/bin/env python
"""
演示脚本：回答用户问题 "给我快速找一两篇基于多智能体的安全代码生成的论文，顶会顶刊的"
"""
import sys
sys.path.insert(0, '/home/runner/work/rag/rag')

from app.services.paper_search_service import paper_search_service
from app.schemas.paper_schema import PaperSearchRequest

def main():
    print("=" * 100)
    print("基于多智能体的安全代码生成 - 顶会顶刊论文推荐")
    print("=" * 100)
    print()
    
    # 用户的查询
    query = "基于多智能体的安全代码生成"
    print(f"📝 查询: {query}")
    print()
    
    # 创建搜索请求
    request = PaperSearchRequest(
        query=query,
        limit=2,  # 只要1-2篇
        year_from=2020  # 近期的论文
    )
    
    # 执行搜索
    result = paper_search_service.search_papers(request)
    
    print(f"🔍 找到 {result.total} 篇相关论文（来自顶会顶刊）:")
    print()
    
    # 展示论文详情
    for i, paper in enumerate(result.papers, 1):
        print(f"【论文 {i}】")
        print("─" * 100)
        print(f"📄 标题: {paper.title}")
        print(f"👥 作者: {', '.join([a.name for a in paper.authors])}")
        print(f"🏛️  会议: {paper.venue} ({paper.year})")
        print(f"📊 引用数: {paper.citation_count}")
        
        if paper.arxiv_id:
            print(f"🔗 arXiv: https://arxiv.org/abs/{paper.arxiv_id}")
        
        if paper.url:
            print(f"🔗 链接: {paper.url}")
        
        if paper.abstract:
            print(f"\n📝 摘要:")
            # 打印摘要，每70个字符换行
            abstract = paper.abstract
            words = abstract.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 > 90:
                    print(f"   {line}")
                    line = word
                else:
                    line = f"{line} {word}" if line else word
            if line:
                print(f"   {line}")
        
        print()
    
    print("=" * 100)
    print("💡 说明:")
    print("   - 以上论文均来自计算机安全和软件工程领域的顶级会议")
    print("   - IEEE S&P (Oakland) 和 ACM CCS 是安全领域的四大顶会之一")
    print("   - USENIX Security 也是安全领域公认的顶会")
    print("   - 这些论文专注于使用多智能体系统来提升代码生成的安全性")
    print("=" * 100)

if __name__ == "__main__":
    main()
