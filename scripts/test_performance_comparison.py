#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务视图性能对比测试
比较优化版本和简化版本的性能差异
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.business_view_supplier_reconciliation import generate_supplier_reconciliation
from scripts.business_view_supplier_reconciliation_simple import generate_supplier_reconciliation_simple

def test_performance_comparison():
    """测试性能对比"""
    logger = EnhancedLogger("performance_comparison")
    
    print("=== 业务视图性能对比测试 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试参数
    test_cases = [
        {
            'name': '全部数据',
            'params': {}
        },
        {
            'name': '指定供应商',
            'params': {'supplier_name': '供应商_1'}
        },
        {
            'name': '指定日期范围',
            'params': {'start_date': '2024-01-01', 'end_date': '2024-12-31'}
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"测试场景: {test_case['name']}")
        print("-" * 60)
        
        # 测试简化版本
        print("1. 测试简化版本...")
        try:
            start_time = time.time()
            simple_result = generate_supplier_reconciliation_simple(
                logger=logger,
                **test_case['params']
            )
            simple_duration = time.time() - start_time
            simple_count = len(simple_result)
            simple_success = True
            print(f"   简化版本: {simple_duration:.3f}秒, {simple_count}条记录")
        except Exception as e:
            simple_duration = 0
            simple_count = 0
            simple_success = False
            print(f"   简化版本: 失败 - {str(e)}")
        
        # 测试优化版本
        print("2. 测试优化版本...")
        try:
            start_time = time.time()
            optimized_result = generate_supplier_reconciliation(
                logger=logger,
                **test_case['params']
            )
            optimized_duration = time.time() - start_time
            optimized_count = len(optimized_result)
            optimized_success = True
            print(f"   优化版本: {optimized_duration:.3f}秒, {optimized_count}条记录")
        except Exception as e:
            optimized_duration = 0
            optimized_count = 0
            optimized_success = False
            print(f"   优化版本: 失败 - {str(e)}")
        
        # 计算性能差异
        if simple_success and optimized_success:
            if simple_duration > 0:
                performance_ratio = optimized_duration / simple_duration
                if performance_ratio > 1:
                    print(f"   性能差异: 优化版本比简化版本慢 {performance_ratio:.2f}倍")
                else:
                    print(f"   性能差异: 优化版本比简化版本快 {1/performance_ratio:.2f}倍")
            else:
                print("   性能差异: 无法计算（简化版本耗时为0）")
            
            # 验证数据一致性
            if simple_count == optimized_count:
                print("   数据一致性: ✓ 记录数量一致")
            else:
                print(f"   数据一致性: ✗ 记录数量不一致 (简化:{simple_count}, 优化:{optimized_count})")
        
        # 记录结果
        result = {
            'test_case': test_case['name'],
            'simple_duration': simple_duration,
            'simple_count': simple_count,
            'simple_success': simple_success,
            'optimized_duration': optimized_duration,
            'optimized_count': optimized_count,
            'optimized_success': optimized_success,
            'performance_ratio': optimized_duration / simple_duration if simple_success and optimized_success and simple_duration > 0 else None
        }
        results.append(result)
        
        print()
    
    # 输出总结
    print("=== 性能测试总结 ===")
    print(f"{'测试场景':<15} {'简化版本(秒)':<12} {'优化版本(秒)':<12} {'性能比率':<10} {'状态'}")
    print("-" * 70)
    
    for result in results:
        status = "正常" if result['simple_success'] and result['optimized_success'] else "异常"
        ratio_str = f"{result['performance_ratio']:.2f}" if result['performance_ratio'] else "N/A"
        
        print(f"{result['test_case']:<15} "
              f"{result['simple_duration']:<12.3f} "
              f"{result['optimized_duration']:<12.3f} "
              f"{ratio_str:<10} "
              f"{status}")
    
    # 分析结果
    print("\n=== 分析结果 ===")
    
    successful_tests = [r for r in results if r['simple_success'] and r['optimized_success']]
    if successful_tests:
        avg_simple = sum(r['simple_duration'] for r in successful_tests) / len(successful_tests)
        avg_optimized = sum(r['optimized_duration'] for r in successful_tests) / len(successful_tests)
        
        print(f"平均执行时间:")
        print(f"  简化版本: {avg_simple:.3f}秒")
        print(f"  优化版本: {avg_optimized:.3f}秒")
        
        if avg_simple > 0:
            overall_ratio = avg_optimized / avg_simple
            if overall_ratio > 1.2:
                print(f"  结论: 优化版本比简化版本慢 {overall_ratio:.2f}倍，可能存在性能问题")
                print("  建议: 检查查询优化器、缓存系统等组件是否引入了额外开销")
            elif overall_ratio < 0.8:
                print(f"  结论: 优化版本比简化版本快 {1/overall_ratio:.2f}倍，优化效果良好")
            else:
                print(f"  结论: 两个版本性能相近，优化版本性能比率为 {overall_ratio:.2f}")
        
        # 检查是否有缓存效果
        print("\n=== 缓存效果测试 ===")
        print("重复执行优化版本测试，检查缓存效果...")
        
        for i, test_case in enumerate(test_cases[:1]):  # 只测试第一个场景
            print(f"第{i+2}次执行 {test_case['name']}:")
            try:
                start_time = time.time()
                cached_result = generate_supplier_reconciliation(
                    logger=logger,
                    **test_case['params']
                )
                cached_duration = time.time() - start_time
                cached_count = len(cached_result)
                
                original_duration = results[i]['optimized_duration']
                if original_duration > 0:
                    cache_ratio = cached_duration / original_duration
                    if cache_ratio < 0.5:
                        print(f"   缓存效果: ✓ 第二次执行快 {1/cache_ratio:.2f}倍 ({cached_duration:.3f}秒)")
                    else:
                        print(f"   缓存效果: ? 第二次执行时间比率 {cache_ratio:.2f} ({cached_duration:.3f}秒)")
                else:
                    print(f"   缓存效果: 无法比较 ({cached_duration:.3f}秒)")
                    
            except Exception as e:
                print(f"   缓存测试失败: {str(e)}")
    
    else:
        print("没有成功的测试用例，无法进行性能分析")
    
    return results

def main():
    """主函数"""
    try:
        results = test_performance_comparison()
        
        # 保存结果到文件
        output_file = f"performance_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"性能测试失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()