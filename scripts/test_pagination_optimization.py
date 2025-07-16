#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分页和数据传输优化测试脚本
测试所有分页、数据压缩、虚拟滚动和传输优化功能
"""

import sys
import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.data_paginator import DataPaginator
from scripts.data_transfer_optimizer import DataTransferOptimizer
from scripts.virtual_scroll_manager import VirtualScrollManager


def create_test_data(count: int = 500) -> List[Dict[str, Any]]:
    """创建测试数据"""
    test_data = []
    for i in range(count):
        test_data.append({
            'id': i + 1,
            'product_code': f'P{i+1:06d}',
            'product_name': f'测试产品_{i + 1}',
            'product_model': f'型号_{i % 10}',
            'unit': '个',
            'current_stock': (i * 7) % 1000,
            'unit_price': round((i + 1) * 12.5, 2),
            'stock_value': round((i * 7) % 1000 * (i + 1) * 12.5, 2),
            'stock_status': ['正常', '低库存', '缺货'][i % 3],
            'supplier_name': f'供应商_{i % 20}',
            'category': f'分类_{i % 15}',
            'description': f'这是第{i + 1}个测试产品的详细描述信息' + ('，包含额外内容' * (i % 3)),
            'last_updated': datetime.now().isoformat(),
            'empty_field': None if i % 5 == 0 else f'值_{i}',
            'blank_field': '' if i % 7 == 0 else f'内容_{i}'
        })
    return test_data


def test_data_paginator():
    """测试数据分页器"""
    print("=== 测试数据分页器 ===")
    logger = EnhancedLogger("test_paginator")
    
    try:
        # 创建测试数据
        test_data = create_test_data(250)
        print(f"创建测试数据: {len(test_data)} 条")
        
        # 创建分页器
        paginator = DataPaginator(
            default_page_size=20,
            pagination_threshold=50,
            compression_threshold=30,
            logger=logger
        )
        
        # 测试分页判断
        print(f"\n1. 测试分页判断")
        print(f"30条数据需要分页: {paginator.should_paginate(30)}")
        print(f"100条数据需要分页: {paginator.should_paginate(100)}")
        
        # 测试分页处理
        print(f"\n2. 测试分页处理")
        page_result = paginator.paginate_results(
            data=test_data,
            page=1,
            page_size=25,
            enable_compression=True
        )
        
        print(f"第1页数据量: {len(page_result['data'])}")
        print(f"分页信息: 第{page_result['pagination']['current_page']}页，"
              f"共{page_result['pagination']['total_pages']}页")
        print(f"压缩信息: 启用={page_result['compression']['enabled']}")
        
        if page_result['compression']['enabled']:
            print(f"压缩率: {page_result['compression']['compression_ratio']}%")
        
        # 测试数据压缩
        print(f"\n3. 测试数据压缩")
        large_data = test_data[:100]
        compressed = paginator.compress_data(large_data)
        decompressed = paginator.decompress_data(compressed)
        
        original_size = len(json.dumps(large_data, ensure_ascii=False).encode('utf-8'))
        compressed_size = len(compressed)
        
        print(f"原始大小: {original_size} bytes")
        print(f"压缩后: {compressed_size} bytes")
        print(f"压缩率: {((1 - compressed_size / original_size) * 100):.2f}%")
        print(f"解压缩验证: {len(decompressed) == len(large_data)}")
        
        # 测试虚拟滚动配置
        print(f"\n4. 测试虚拟滚动配置")
        virtual_config = paginator.create_virtual_scroll_config(
            total_count=len(test_data),
            item_height=50,
            container_height=400
        )
        print(f"启用虚拟滚动: {virtual_config['enable_virtual_scroll']}")
        print(f"可见项目数: {virtual_config['visible_count']}")
        print(f"渲染项目数: {virtual_config['render_count']}")
        
        # 测试数据导出
        print(f"\n5. 测试数据导出")
        export_data = test_data[:10]
        
        # JSON导出
        json_export = paginator.export_full_dataset(export_data, format_type='json', compress=False)
        json_compressed = paginator.export_full_dataset(export_data, format_type='json', compress=True)
        
        print(f"JSON导出: {len(json_export)} 字符")
        print(f"JSON压缩导出: {len(json_compressed)} bytes")
        
        # CSV导出
        csv_export = paginator.export_full_dataset(export_data, format_type='csv', compress=False)
        print(f"CSV导出: {len(csv_export)} 字符")
        
        print("✓ 数据分页器测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 数据分页器测试失败: {str(e)}")
        return False


def test_data_transfer_optimizer():
    """测试数据传输优化器"""
    print("\n=== 测试数据传输优化器 ===")
    logger = EnhancedLogger("test_transfer_optimizer")
    
    try:
        # 创建测试数据
        test_data = create_test_data(200)
        print(f"创建测试数据: {len(test_data)} 条")
        
        # 创建传输优化器
        optimizer = DataTransferOptimizer(
            chunk_size=50,
            compression_threshold=30,
            logger=logger
        )
        
        # 测试数据优化
        print(f"\n1. 测试数据传输优化")
        optimization_result = optimizer.optimize_data_for_transfer(test_data)
        optimization_info = optimization_result['optimization_info']
        
        print(f"原始大小: {optimization_info['original_size']} bytes")
        print(f"优化后大小: {optimization_info['optimized_size']} bytes")
        print(f"减少: {optimization_info['reduction_percentage']}%")
        print(f"应用的优化: {optimization_info['optimizations_applied']}")
        
        # 测试分块传输准备
        print(f"\n2. 测试分块传输准备")
        optimized_data = optimization_result['optimized_data']
        transfer_info = optimizer.prepare_chunked_transfer(optimized_data, enable_compression=True)
        
        if 'error' not in transfer_info:
            session_id = transfer_info['session_id']
            print(f"会话ID: {session_id}")
            print(f"总分块数: {transfer_info['total_chunks']}")
            print(f"估算传输时间: {transfer_info['estimated_transfer_time']['estimated_seconds']}秒")
            
            # 测试获取数据块
            print(f"\n3. 测试获取数据块")
            for i in range(min(3, transfer_info['total_chunks'])):
                chunk_result = optimizer.get_chunk(session_id, i)
                if 'error' not in chunk_result:
                    data_count = len(chunk_result.get('data', []))
                    compressed = chunk_result.get('compressed', False)
                    progress = chunk_result['progress']['percentage']
                    print(f"块 {i}: 数据量={data_count}, 压缩={compressed}, 进度={progress}%")
                else:
                    print(f"获取块 {i} 失败: {chunk_result['error']}")
            
            # 测试传输进度
            print(f"\n4. 测试传输进度")
            progress = optimizer.get_transfer_progress(session_id)
            if 'error' not in progress:
                print(f"传输进度: {progress['progress_percentage']}%")
                print(f"已接收块数: {progress['received_chunks']}/{progress['total_chunks']}")
                print(f"传输速度: {progress['transfer_rate_chunks_per_second']} 块/秒")
            
            # 测试取消传输
            print(f"\n5. 测试取消传输")
            cancel_result = optimizer.cancel_transfer(session_id)
            print(f"取消结果: {cancel_result.get('success', False)}")
        
        # 测试增量更新
        print(f"\n6. 测试增量更新")
        # 创建修改后的数据
        modified_data = test_data.copy()
        # 修改一些记录
        modified_data[0]['product_name'] = '修改后的产品名称'
        modified_data[1]['unit_price'] = 999.99
        # 删除一些记录
        modified_data = modified_data[:-10]
        # 添加一些新记录
        for i in range(5):
            modified_data.append({
                'id': len(test_data) + i + 1,
                'product_name': f'新增产品_{i + 1}',
                'unit_price': i * 100,
                'category': '新分类'
            })
        
        incremental_update = optimizer.create_incremental_update(test_data, modified_data, key_field='id')
        stats = incremental_update['statistics']
        print(f"增量更新统计: 新增={stats['added_count']}, "
              f"更新={stats['updated_count']}, 删除={stats['deleted_count']}")
        print(f"变化比例: {stats['change_ratio']:.2%}")
        print(f"增量更新高效: {stats['is_efficient']}")
        
        print("✓ 数据传输优化器测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 数据传输优化器测试失败: {str(e)}")
        return False


def test_virtual_scroll_manager():
    """测试虚拟滚动管理器"""
    print("\n=== 测试虚拟滚动管理器 ===")
    logger = EnhancedLogger("test_virtual_scroll")
    
    try:
        # 创建测试数据
        test_data = create_test_data(1000)
        print(f"创建测试数据: {len(test_data)} 条")
        
        # 创建虚拟滚动管理器
        scroll_manager = VirtualScrollManager(
            default_item_height=60,
            default_container_height=500,
            buffer_size=5,
            logger=logger
        )
        
        # 测试创建虚拟滚动配置
        print(f"\n1. 测试创建虚拟滚动配置")
        config = scroll_manager.create_virtual_scroll_config(
            data_source='test_data',
            total_count=len(test_data),
            item_height=60,
            container_height=500
        )
        
        print(f"启用虚拟滚动: {config['enable_virtual_scroll']}")
        print(f"可见项目数: {config['visible_count']}")
        print(f"渲染项目数: {config['render_count']}")
        print(f"总高度: {config['total_height']}px")
        print(f"性能优化比例: {config['performance']['render_optimization_ratio']}%")
        
        # 测试获取可见范围
        print(f"\n2. 测试获取可见范围")
        scroll_positions = [0, 2000, 10000, 20000]
        for scroll_top in scroll_positions:
            range_info = scroll_manager.get_visible_range(
                scroll_top=scroll_top,
                container_height=500,
                item_height=60,
                total_count=len(test_data)
            )
            print(f"滚动位置 {scroll_top}: 渲染范围 {range_info['render_start']}-{range_info['render_end']}, "
                  f"滚动百分比 {range_info['scroll_percentage']}%")
        
        # 测试获取虚拟数据
        print(f"\n3. 测试获取虚拟数据")
        virtual_data = scroll_manager.get_virtual_data(
            data_source='test_data',
            data=test_data,
            start_index=100,
            end_index=150
        )
        print(f"虚拟数据: 起始索引={virtual_data['start_index']}, "
              f"数据量={virtual_data['count']}, 缓存命中={virtual_data['cache_hit']}")
        
        # 再次获取相同数据测试缓存
        virtual_data2 = scroll_manager.get_virtual_data(
            data_source='test_data',
            data=test_data,
            start_index=100,
            end_index=150
        )
        print(f"第二次获取: 缓存命中={virtual_data2['cache_hit']}")
        
        # 测试计算滚动位置
        print(f"\n4. 测试计算滚动位置")
        target_index = 500
        for position in ['top', 'center', 'bottom']:
            scroll_pos = scroll_manager.calculate_scroll_position(
                target_index=target_index,
                item_height=60,
                container_height=500,
                position=position
            )
            print(f"滚动到索引 {target_index} ({position}): 滚动位置={scroll_pos['scroll_top']}")
        
        # 测试动态高度配置
        print(f"\n5. 测试动态高度配置")
        
        def height_calculator(item):
            # 根据描述长度计算高度
            base_height = 60
            desc_length = len(item.get('description', ''))
            extra_height = (desc_length // 30) * 15
            return base_height + extra_height
        
        dynamic_config = scroll_manager.create_dynamic_height_config(
            data=test_data[:100],  # 只测试前100项
            height_calculator=height_calculator
        )
        
        if 'statistics' in dynamic_config:
            stats = dynamic_config['statistics']
            print(f"动态高度统计: 平均={stats['avg_height']}px, "
                  f"最小={stats['min_height']}px, 最大={stats['max_height']}px")
            print(f"高度差异: {stats['height_variance']}px")
        
        # 测试缓存统计
        print(f"\n6. 测试缓存统计")
        cache_stats = scroll_manager.get_cache_stats()
        print(f"缓存项目数: {cache_stats['total_cached_items']}")
        print(f"缓存使用率: {cache_stats['cache_usage_ratio']:.2%}")
        
        # 测试清理缓存
        print(f"\n7. 测试清理缓存")
        scroll_manager.clear_cache('test_data')
        cache_stats_after = scroll_manager.get_cache_stats()
        print(f"清理后缓存项目数: {cache_stats_after['total_cached_items']}")
        
        print("✓ 虚拟滚动管理器测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 虚拟滚动管理器测试失败: {str(e)}")
        return False


def test_integrated_functionality():
    """测试集成功能"""
    print("\n=== 测试集成功能 ===")
    logger = EnhancedLogger("test_integrated")
    
    try:
        # 创建大量测试数据
        test_data = create_test_data(500)
        print(f"创建测试数据: {len(test_data)} 条")
        
        # 创建所有组件
        paginator = DataPaginator(logger=logger)
        optimizer = DataTransferOptimizer(logger=logger)
        scroll_manager = VirtualScrollManager(logger=logger)
        
        # 测试完整的数据处理流程
        print(f"\n1. 测试完整数据处理流程")
        
        # 步骤1: 数据传输优化
        optimization_result = optimizer.optimize_data_for_transfer(test_data)
        optimized_data = optimization_result['optimized_data']
        print(f"数据优化完成，减少 {optimization_result['optimization_info']['reduction_percentage']}%")
        
        # 步骤2: 分页处理
        paginated_result = paginator.paginate_results(
            data=optimized_data,
            page=1,
            page_size=50,
            enable_compression=True
        )
        print(f"分页处理完成，第1页包含 {len(paginated_result['data'])} 条记录")
        
        # 步骤3: 虚拟滚动配置
        virtual_config = scroll_manager.create_virtual_scroll_config(
            data_source='integrated_test',
            total_count=len(optimized_data),
            item_height=50,
            container_height=400
        )
        print(f"虚拟滚动配置完成，渲染优化 {virtual_config['performance']['render_optimization_ratio']}%")
        
        # 测试性能对比
        print(f"\n2. 测试性能对比")
        
        # 原始数据大小
        original_size = len(json.dumps(test_data, ensure_ascii=False).encode('utf-8'))
        
        # 优化后数据大小
        optimized_size = len(json.dumps(optimized_data, ensure_ascii=False).encode('utf-8'))
        
        # 分页后数据大小
        page_data = paginated_result['data']
        page_size = len(json.dumps(page_data, ensure_ascii=False).encode('utf-8'))
        
        print(f"原始数据大小: {original_size:,} bytes")
        print(f"优化后数据大小: {optimized_size:,} bytes")
        print(f"单页数据大小: {page_size:,} bytes")
        print(f"总体优化比例: {((1 - page_size / original_size) * 100):.2f}%")
        
        # 测试内存使用估算
        print(f"\n3. 测试内存使用估算")
        
        # DOM节点估算
        dom_nodes_full = len(test_data)
        dom_nodes_virtual = virtual_config['render_count']
        dom_reduction = ((1 - dom_nodes_virtual / dom_nodes_full) * 100)
        
        print(f"完整渲染DOM节点: {dom_nodes_full:,}")
        print(f"虚拟滚动DOM节点: {dom_nodes_virtual:,}")
        print(f"DOM节点减少: {dom_reduction:.2f}%")
        
        # 内存使用估算
        memory_full = dom_nodes_full * 0.5  # 假设每个节点0.5KB
        memory_virtual = dom_nodes_virtual * 0.5
        memory_reduction = ((1 - memory_virtual / memory_full) * 100)
        
        print(f"完整渲染内存估算: {memory_full:.1f} KB")
        print(f"虚拟滚动内存估算: {memory_virtual:.1f} KB")
        print(f"内存使用减少: {memory_reduction:.2f}%")
        
        print("✓ 集成功能测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 集成功能测试失败: {str(e)}")
        return False


def test_performance_benchmarks():
    """测试性能基准"""
    print("\n=== 测试性能基准 ===")
    
    try:
        # 创建不同大小的测试数据
        data_sizes = [100, 500, 1000, 2000]
        results = []
        
        for size in data_sizes:
            print(f"\n测试数据量: {size} 条")
            test_data = create_test_data(size)
            
            # 测试分页性能
            start_time = time.time()
            paginator = DataPaginator()
            paginated_result = paginator.paginate_results(
                data=test_data,
                page=1,
                page_size=50,
                enable_compression=True
            )
            pagination_time = time.time() - start_time
            
            # 测试传输优化性能
            start_time = time.time()
            optimizer = DataTransferOptimizer()
            optimization_result = optimizer.optimize_data_for_transfer(test_data)
            optimization_time = time.time() - start_time
            
            # 测试虚拟滚动配置性能
            start_time = time.time()
            scroll_manager = VirtualScrollManager()
            virtual_config = scroll_manager.create_virtual_scroll_config(
                data_source=f'benchmark_{size}',
                total_count=size,
                item_height=50,
                container_height=400
            )
            virtual_scroll_time = time.time() - start_time
            
            # 记录结果
            result = {
                'data_size': size,
                'pagination_time_ms': round(pagination_time * 1000, 2),
                'optimization_time_ms': round(optimization_time * 1000, 2),
                'virtual_scroll_time_ms': round(virtual_scroll_time * 1000, 2),
                'total_time_ms': round((pagination_time + optimization_time + virtual_scroll_time) * 1000, 2),
                'compression_ratio': paginated_result['compression'].get('compression_ratio', 0),
                'optimization_reduction': optimization_result['optimization_info']['reduction_percentage']
            }
            results.append(result)
            
            print(f"分页处理: {result['pagination_time_ms']} ms")
            print(f"传输优化: {result['optimization_time_ms']} ms")
            print(f"虚拟滚动: {result['virtual_scroll_time_ms']} ms")
            print(f"总耗时: {result['total_time_ms']} ms")
        
        # 输出性能基准报告
        print(f"\n性能基准报告:")
        print(f"{'数据量':<8} {'分页(ms)':<10} {'优化(ms)':<10} {'虚拟滚动(ms)':<12} {'总耗时(ms)':<10}")
        print("-" * 60)
        
        for result in results:
            print(f"{result['data_size']:<8} "
                  f"{result['pagination_time_ms']:<10} "
                  f"{result['optimization_time_ms']:<10} "
                  f"{result['virtual_scroll_time_ms']:<12} "
                  f"{result['total_time_ms']:<10}")
        
        # 分析性能趋势
        if len(results) >= 2:
            print(f"\n性能趋势分析:")
            first_result = results[0]
            last_result = results[-1]
            
            size_ratio = last_result['data_size'] / first_result['data_size']
            time_ratio = last_result['total_time_ms'] / first_result['total_time_ms']
            
            print(f"数据量增长: {size_ratio:.1f}x")
            print(f"处理时间增长: {time_ratio:.1f}x")
            print(f"性能扩展性: {'良好' if time_ratio <= size_ratio * 1.5 else '需要优化'}")
        
        print("✓ 性能基准测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 性能基准测试失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("开始分页和数据传输优化测试")
    print("=" * 60)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("数据分页器", test_data_paginator),
        ("数据传输优化器", test_data_transfer_optimizer),
        ("虚拟滚动管理器", test_virtual_scroll_manager),
        ("集成功能", test_integrated_functionality),
        ("性能基准", test_performance_benchmarks)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}测试异常: {str(e)}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    print(f"\n{'='*60}")
    print("测试总结:")
    print("-" * 60)
    
    passed_count = 0
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed_count += 1
    
    print("-" * 60)
    print(f"总计: {passed_count}/{len(test_results)} 个测试通过")
    
    if passed_count == len(test_results):
        print("🎉 所有测试通过！分页和数据传输优化功能正常工作。")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)