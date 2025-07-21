#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据分析服务的缓存和性能优化功能
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


def test_caching_functionality():
    """测试缓存功能"""
    print("=== 测试缓存功能 ===")
    
    logger = EnhancedLogger("test_caching")
    service = DataAnalysisService(logger)
    
    # 测试参数
    test_params = {
        'date_range': {
            'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d')
        }
    }
    
    print("1. 测试仪表板概览缓存...")
    
    # 第一次调用（缓存未命中）
    start_time = time.time()
    result1 = service.get_dashboard_summary(test_params)
    first_call_time = time.time() - start_time
    
    print(f"第一次调用时间: {first_call_time:.3f}秒")
    print(f"结果类型: {type(result1)}")
    print(f"是否有缓存标记: {'cached' in result1}")
    
    # 第二次调用（缓存命中）
    start_time = time.time()
    result2 = service.get_dashboard_summary(test_params)
    second_call_time = time.time() - start_time
    
    print(f"第二次调用时间: {second_call_time:.3f}秒")
    print(f"是否有缓存标记: {result2.get('cached', False)}")
    print(f"性能提升: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
    
    return service


def test_pagination_functionality(service):
    """测试分页功能"""
    print("\n=== 测试分页功能 ===")
    
    # 测试销售趋势分析的分页
    test_params = {
        'dimension': 'product',
        'date_range': {},
        'page': 1,
        'page_size': 10
    }
    
    print("1. 测试销售趋势分析分页...")
    result = service.analyze_sales_trend(test_params)
    
    if result.get('success'):
        print(f"分析维度: {result.get('dimension')}")
        print(f"数据条数: {len(result.get('data', []))}")
        
        if 'pagination' in result:
            pagination = result['pagination']
            print(f"分页信息: 第{pagination['current_page']}页，共{pagination['total_pages']}页")
            print(f"总记录数: {pagination['total_count']}")
            print(f"是否启用分页: {pagination['is_paginated']}")
        
        if 'compression' in result:
            compression = result['compression']
            print(f"压缩状态: {compression['enabled']}")
            if compression['enabled']:
                print(f"压缩率: {compression.get('compression_ratio', 0)}%")
    else:
        print(f"分析失败: {result.get('error', {}).get('message', '未知错误')}")


def test_cache_management(service):
    """测试缓存管理功能"""
    print("\n=== 测试缓存管理功能 ===")
    
    # 获取缓存统计
    print("1. 获取缓存统计...")
    cache_stats = service.get_cache_stats()
    print(f"缓存统计: {json.dumps(cache_stats, indent=2, ensure_ascii=False)}")
    
    # 测试缓存失效
    print("\n2. 测试缓存失效...")
    invalidate_result = service.invalidate_cache("dashboard_*")
    print(f"失效结果: {invalidate_result}")
    
    # 再次获取缓存统计
    print("\n3. 失效后的缓存统计...")
    cache_stats_after = service.get_cache_stats()
    print(f"失效后缓存大小: {cache_stats_after.get('cache_stats', {}).get('cache_size', 0)}")


def test_performance_optimization(service):
    """测试性能优化功能"""
    print("\n=== 测试性能优化功能 ===")
    
    # 测试性能基准测试
    print("1. 运行性能基准测试...")
    benchmark_params = {
        'iterations': 2,
        'test_dashboard': True,
        'test_sales_trend': True,
        'test_customer_value': False  # 跳过客户价值分析以节省时间
    }
    
    benchmark_result = service.benchmark_performance(benchmark_params)
    
    if benchmark_result.get('success'):
        print("基准测试结果:")
        for test_name, stats in benchmark_result.get('benchmark_results', {}).items():
            print(f"  {test_name}:")
            print(f"    平均时间: {stats['avg_time']:.3f}秒")
            print(f"    最小时间: {stats['min_time']:.3f}秒")
            print(f"    最大时间: {stats['max_time']:.3f}秒")
    else:
        print(f"基准测试失败: {benchmark_result.get('error', '未知错误')}")
    
    # 测试查询性能优化
    print("\n2. 测试查询性能优化...")
    optimize_params = {
        'preload_cache': True,
        'optimize_queries': True,
        'cleanup_memory': True
    }
    
    optimize_result = service.optimize_query_performance(optimize_params)
    print(f"优化结果: {optimize_result}")


def test_pagination_config(service):
    """测试分页配置功能"""
    print("\n=== 测试分页配置功能 ===")
    
    # 测试不同数据大小的分页配置
    test_sizes = [50, 150, 500, 1000]
    
    for size in test_sizes:
        config = service.get_pagination_config(size)
        print(f"数据大小 {size}:")
        print(f"  是否需要分页: {config['should_paginate']}")
        print(f"  建议页面大小: {config['recommended_page_size']}")
        print(f"  总页数: {config['total_pages']}")
        print(f"  建议压缩: {config['compression_recommended']}")
        print(f"  建议虚拟滚动: {config['virtual_scroll_recommended']}")


def main():
    """主测试函数"""
    try:
        print("开始测试数据分析服务的缓存和性能优化功能...\n")
        
        # 测试缓存功能
        service = test_caching_functionality()
        
        # 测试分页功能
        test_pagination_functionality(service)
        
        # 测试缓存管理
        test_cache_management(service)
        
        # 测试性能优化
        test_performance_optimization(service)
        
        # 测试分页配置
        test_pagination_config(service)
        
        print("\n=== 所有测试完成 ===")
        
        # 最终缓存统计
        final_stats = service.get_cache_stats()
        print(f"最终缓存统计:")
        print(f"  缓存大小: {final_stats.get('cache_stats', {}).get('cache_size', 0)}")
        print(f"  命中率: {final_stats.get('cache_stats', {}).get('hit_rate', 0)}%")
        print(f"  总请求数: {final_stats.get('cache_stats', {}).get('total_requests', 0)}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()