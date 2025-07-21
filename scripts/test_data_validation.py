#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证功能测试脚本
测试数据分析服务的参数验证和清理功能
"""

import sys
import os
import json
from datetime import datetime, timedelta

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_analysis_service import DataAnalysisService
from enhanced_logger import EnhancedLogger

def test_date_validation():
    """测试日期验证功能"""
    print("=== 测试日期验证功能 ===")
    
    logger = EnhancedLogger("test_validation")
    service = DataAnalysisService(logger)
    
    # 测试用例
    test_cases = [
        # 有效日期格式
        {
            'name': '有效日期格式',
            'params': {
                'date_range': {
                    'start_date': '2025-01-01',
                    'end_date': '2025-01-31'
                }
            },
            'should_pass': True
        },
        # 无效日期格式
        {
            'name': '无效日期格式',
            'params': {
                'date_range': {
                    'start_date': '2025/01/01',
                    'end_date': '2025-01-31'
                }
            },
            'should_pass': False
        },
        # 日期范围颠倒
        {
            'name': '日期范围颠倒',
            'params': {
                'date_range': {
                    'start_date': '2025-01-31',
                    'end_date': '2025-01-01'
                }
            },
            'should_pass': False
        },
        # 空日期范围（应该使用默认值）
        {
            'name': '空日期范围',
            'params': {},
            'should_pass': True
        },
        # 未来日期
        {
            'name': '未来日期',
            'params': {
                'date_range': {
                    'start_date': '2026-01-01',
                    'end_date': '2026-01-31'
                }
            },
            'should_pass': False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            validated_params = service.validate_and_clean_params('get_dashboard_summary', test_case['params'])
            if test_case['should_pass']:
                print(f"✓ 通过 - 验证后的参数: {validated_params.get('date_range', {})}")
            else:
                print(f"✗ 失败 - 应该抛出异常但没有")
        except ValueError as e:
            if not test_case['should_pass']:
                print(f"✓ 通过 - 正确捕获异常: {str(e)}")
            else:
                print(f"✗ 失败 - 不应该抛出异常: {str(e)}")
        except Exception as e:
            print(f"✗ 失败 - 意外异常: {str(e)}")

def test_numeric_validation():
    """测试数值参数验证功能"""
    print("\n=== 测试数值参数验证功能 ===")
    
    logger = EnhancedLogger("test_validation")
    service = DataAnalysisService(logger)
    
    test_cases = [
        # 有效数值参数
        {
            'name': '有效数值参数',
            'params': {
                'page': 1,
                'page_size': 50,
                'limit': 100
            },
            'expected_page': 1,
            'expected_page_size': 50
        },
        # 字符串数值参数（应该转换）
        {
            'name': '字符串数值参数',
            'params': {
                'page': '2',
                'page_size': '25'
            },
            'expected_page': 2,
            'expected_page_size': 25
        },
        # 负数参数（应该调整）
        {
            'name': '负数参数',
            'params': {
                'page': -1,
                'page_size': -10
            },
            'expected_page': 1,
            'expected_page_size': 10
        },
        # 过大参数（应该限制）
        {
            'name': '过大参数',
            'params': {
                'page': 99999,
                'page_size': 5000
            },
            'expected_page': 10000,
            'expected_page_size': 1000
        },
        # 无效参数（应该使用默认值）
        {
            'name': '无效参数',
            'params': {
                'page': 'invalid',
                'page_size': None
            },
            'expected_page': 1,
            'expected_page_size': 50
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            validated_params = service.validate_and_clean_params('analyze_sales_trend', test_case['params'])
            actual_page = validated_params.get('page')
            actual_page_size = validated_params.get('page_size')
            
            if (actual_page == test_case['expected_page'] and 
                actual_page_size == test_case['expected_page_size']):
                print(f"✓ 通过 - page: {actual_page}, page_size: {actual_page_size}")
            else:
                print(f"✗ 失败 - 期望 page: {test_case['expected_page']}, page_size: {test_case['expected_page_size']}")
                print(f"        实际 page: {actual_page}, page_size: {actual_page_size}")
        except Exception as e:
            print(f"✗ 失败 - 异常: {str(e)}")

def test_string_validation():
    """测试字符串参数验证功能"""
    print("\n=== 测试字符串参数验证功能 ===")
    
    logger = EnhancedLogger("test_validation")
    service = DataAnalysisService(logger)
    
    test_cases = [
        # 有效维度参数
        {
            'name': '有效维度参数',
            'params': {'dimension': 'month'},
            'expected_dimension': 'month'
        },
        # 无效维度参数（应该使用默认值）
        {
            'name': '无效维度参数',
            'params': {'dimension': 'invalid_dimension'},
            'expected_dimension': 'month'
        },
        # 包含危险字符的参数（应该清理）
        {
            'name': '包含危险字符的参数',
            'params': {'dimension': 'month<script>'},
            'expected_dimension': 'monthscript'
        },
        # 过长的字符串参数（应该截断）
        {
            'name': '过长的字符串参数',
            'params': {'dimension': 'a' * 150},
            'expected_dimension': 'month'  # 会被验证为无效并使用默认值
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            validated_params = service.validate_and_clean_params('analyze_sales_trend', test_case['params'])
            actual_dimension = validated_params.get('dimension')
            
            if actual_dimension == test_case['expected_dimension']:
                print(f"✓ 通过 - dimension: {actual_dimension}")
            else:
                print(f"✗ 失败 - 期望: {test_case['expected_dimension']}, 实际: {actual_dimension}")
        except Exception as e:
            print(f"✗ 失败 - 异常: {str(e)}")

def test_array_validation():
    """测试数组参数验证功能"""
    print("\n=== 测试数组参数验证功能 ===")
    
    logger = EnhancedLogger("test_validation")
    service = DataAnalysisService(logger)
    
    test_cases = [
        # 有效指标数组
        {
            'name': '有效指标数组',
            'params': {
                'metrics': ['total_sales', 'total_purchases'],
                'dimensions': ['month', 'product']
            },
            'expected_metrics': ['total_sales', 'total_purchases'],
            'expected_dimensions': ['month', 'product']
        },
        # 包含无效指标的数组
        {
            'name': '包含无效指标的数组',
            'params': {
                'metrics': ['total_sales', 'invalid_metric', 'total_purchases'],
                'dimensions': ['month', 'invalid_dimension']
            },
            'expected_metrics': ['total_sales', 'total_purchases'],
            'expected_dimensions': ['month']
        },
        # 字符串转数组
        {
            'name': '字符串转数组',
            'params': {
                'metrics': 'total_sales',
                'dimensions': 'month'
            },
            'expected_metrics': ['total_sales'],
            'expected_dimensions': ['month']
        },
        # 空数组（应该使用默认值）
        {
            'name': '空数组',
            'params': {
                'metrics': [],
                'dimensions': []
            },
            'expected_metrics': ['total_sales', 'total_purchases'],
            'expected_dimensions': ['month', 'product']
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            validated_params = service.validate_and_clean_params('generate_comparison_analysis', test_case['params'])
            actual_metrics = validated_params.get('metrics')
            actual_dimensions = validated_params.get('dimensions')
            
            if (actual_metrics == test_case['expected_metrics'] and 
                actual_dimensions == test_case['expected_dimensions']):
                print(f"✓ 通过 - metrics: {actual_metrics}, dimensions: {actual_dimensions}")
            else:
                print(f"✗ 失败 - 期望 metrics: {test_case['expected_metrics']}, dimensions: {test_case['expected_dimensions']}")
                print(f"        实际 metrics: {actual_metrics}, dimensions: {actual_dimensions}")
        except Exception as e:
            print(f"✗ 失败 - 异常: {str(e)}")

def test_data_integrity():
    """测试数据完整性检查功能"""
    print("\n=== 测试数据完整性检查功能 ===")
    
    logger = EnhancedLogger("test_validation")
    service = DataAnalysisService(logger)
    
    test_cases = [
        # 有效数据
        {
            'name': '有效销售汇总数据',
            'data': {'total_amount': 1000, 'order_count': 10},
            'data_type': 'sales_summary',
            'expected': True
        },
        # 空数据
        {
            'name': '空数据',
            'data': None,
            'data_type': 'sales_summary',
            'expected': False
        },
        # 缺少必要字段的数据
        {
            'name': '缺少必要字段的销售数据',
            'data': {'total_amount': 1000},  # 缺少order_count
            'data_type': 'sales_summary',
            'expected': False
        },
        # 包含错误信息的数据
        {
            'name': '包含错误信息的数据',
            'data': {'error': True, 'message': 'Database error'},
            'data_type': 'sales_summary',
            'expected': False
        },
        # 有效库存数据
        {
            'name': '有效库存数据',
            'data': {'data': [{'product': 'A', 'stock': 100}]},
            'data_type': 'inventory_data',
            'expected': True
        },
        # 空库存数据列表
        {
            'name': '空库存数据列表',
            'data': {'data': []},
            'data_type': 'inventory_data',
            'expected': False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            result = service._check_data_integrity(test_case['data'], test_case['data_type'])
            if result == test_case['expected']:
                print(f"✓ 通过 - 完整性检查结果: {result}")
            else:
                print(f"✗ 失败 - 期望: {test_case['expected']}, 实际: {result}")
        except Exception as e:
            print(f"✗ 失败 - 异常: {str(e)}")

def test_method_call_validation():
    """测试方法调用的完整验证流程"""
    print("\n=== 测试方法调用的完整验证流程 ===")
    
    logger = EnhancedLogger("test_validation")
    service = DataAnalysisService(logger)
    
    # 测试有效的方法调用
    print("\n测试: 有效的仪表板概览调用")
    try:
        result = service.handle_method_call('get_dashboard_summary', {
            'date_range': {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31'
            }
        })
        
        if result.get('success') and result.get('validation_applied'):
            print("✓ 通过 - 方法调用成功，参数验证已应用")
        else:
            print(f"✗ 失败 - 方法调用结果: {result}")
    except Exception as e:
        print(f"✗ 失败 - 异常: {str(e)}")
    
    # 测试无效参数的方法调用
    print("\n测试: 无效参数的方法调用")
    try:
        result = service.handle_method_call('analyze_sales_trend', {
            'dimension': 'invalid_dimension',
            'date_range': {
                'start_date': '2025/01/01',  # 无效格式
                'end_date': '2025-01-31'
            }
        })
        
        if not result.get('success') and result.get('error', {}).get('code') == 'INVALID_PARAMETERS':
            print("✓ 通过 - 正确捕获参数验证错误")
        else:
            print(f"✗ 失败 - 应该返回参数验证错误，实际结果: {result}")
    except Exception as e:
        print(f"✗ 失败 - 异常: {str(e)}")

def main():
    """运行所有测试"""
    print("开始数据验证功能测试")
    print("=" * 50)
    
    try:
        test_date_validation()
        test_numeric_validation()
        test_string_validation()
        test_array_validation()
        test_data_integrity()
        test_method_call_validation()
        
        print("\n" + "=" * 50)
        print("数据验证功能测试完成")
        
    except Exception as e:
        print(f"测试执行失败: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())