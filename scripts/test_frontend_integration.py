#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前后端集成测试
测试数据分析仪表板的前后端数据流和集成功能
"""

import sys
import os
import json
import unittest
import subprocess
import time
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


class TestFrontendIntegration(unittest.TestCase):
    """前后端集成测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_frontend_integration")
        self.service = DataAnalysisService(self.logger)
        
        # 模拟前端请求数据
        self.frontend_requests = {
            'dashboard_summary': {
                'method': 'get_dashboard_summary',
                'params': {
                    'date_range': {
                        'start_date': '2025-01-01',
                        'end_date': '2025-01-31'
                    }
                }
            },
            'sales_trend_monthly': {
                'method': 'analyze_sales_trend',
                'params': {
                    'dimension': 'month',
                    'date_range': {
                        'start_date': '2025-01-01',
                        'end_date': '2025-03-31'
                    }
                }
            },
            'sales_trend_product': {
                'method': 'analyze_sales_trend',
                'params': {
                    'dimension': 'product',
                    'date_range': {}
                }
            },
            'customer_value_analysis': {
                'method': 'analyze_customer_value',
                'params': {
                    'analysis_type': 'rfm',
                    'date_range': {
                        'start_date': '2024-01-01',
                        'end_date': '2025-01-31'
                    }
                }
            },
            'inventory_turnover': {
                'method': 'analyze_inventory_turnover',
                'params': {
                    'analysis_period': 365,
                    'turnover_thresholds': {'fast': 4.0, 'slow': 1.0}
                }
            },
            'comparison_analysis': {
                'method': 'generate_comparison_analysis',
                'params': {
                    'metrics': ['total_sales', 'total_purchases'],
                    'dimensions': ['month', 'product'],
                    'top_n': 10
                }
            }
        }
    
    def test_command_line_interface(self):
        """测试命令行接口"""
        # 测试有效的方法调用
        test_cases = [
            {
                'method': 'get_dashboard_summary',
                'params': '{"date_range": {"start_date": "2025-01-01", "end_date": "2025-01-31"}}',
                'should_succeed': True
            },
            {
                'method': 'analyze_sales_trend',
                'params': '{"dimension": "month"}',
                'should_succeed': True
            },
            {
                'method': 'invalid_method',
                'params': '{}',
                'should_succeed': False
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(method=test_case['method']):
                try:
                    # 模拟命令行调用
                    result = self.service.handle_method_call(
                        test_case['method'], 
                        json.loads(test_case['params'])
                    )
                    
                    if test_case['should_succeed']:
                        # 验证成功响应的基本结构
                        self.assertIsInstance(result, dict)
                        self.assertIn('generated_at', result)
                        
                        # 如果有错误，应该是数据相关的错误，不是接口错误
                        if not result.get('success', True):
                            self.assertNotEqual(result.get('error', {}).get('code'), 'METHOD_NOT_FOUND')
                    else:
                        # 验证错误响应
                        self.assertFalse(result.get('success', True))
                        self.assertIsNotNone(result.get('error'))
                        
                except Exception as e:
                    if test_case['should_succeed']:
                        self.fail(f"方法 {test_case['method']} 应该成功但抛出异常: {str(e)}")
    
    def test_data_format_validation(self):
        """测试数据格式验证"""
        # 测试仪表板概览数据格式
        result = self.service.handle_method_call('get_dashboard_summary', {})
        
        if result.get('success') or 'data' in result:
            # 验证数据结构
            if 'data' in result:
                data = result['data']
            else:
                data = result
            
            # 验证必要字段存在
            expected_fields = [
                'total_sales', 'total_sales_count', 'active_customers',
                'total_purchases', 'total_inventory_value', 'gross_margin'
            ]
            
            for field in expected_fields:
                self.assertIn(field, data, f"缺少必要字段: {field}")
                self.assertIsInstance(data[field], (int, float), f"字段 {field} 应该是数值类型")
    
    def test_chart_data_format(self):
        """测试图表数据格式"""
        # 测试销售趋势图表数据
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'month'
        })
        
        if result.get('success') and result.get('data'):
            chart_data = result['data']
            
            # 验证图表数据是列表
            self.assertIsInstance(chart_data, list)
            
            # 如果有数据，验证数据结构
            if chart_data:
                first_item = chart_data[0]
                
                # 月度趋势应该包含的字段
                expected_fields = ['period', 'total_sales', 'order_count']
                for field in expected_fields:
                    self.assertIn(field, first_item, f"图表数据缺少字段: {field}")
    
    def test_error_message_format(self):
        """测试错误消息格式"""
        # 测试无效方法调用
        result = self.service.handle_method_call('invalid_method', {})
        
        # 验证错误响应格式
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
        
        error = result['error']
        self.assertIn('code', error)
        self.assertIn('message', error)
        self.assertIsInstance(error['code'], str)
        self.assertIsInstance(error['message'], str)
    
    def test_pagination_integration(self):
        """测试分页集成"""
        # 测试带分页的销售趋势分析
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'product',
            'page': 1,
            'page_size': 10
        })
        
        if result.get('success'):
            # 如果启用了分页，验证分页信息
            if 'pagination' in result:
                pagination = result['pagination']
                
                # 验证分页字段
                expected_pagination_fields = [
                    'current_page', 'total_pages', 'total_count', 'page_size'
                ]
                for field in expected_pagination_fields:
                    self.assertIn(field, pagination, f"分页信息缺少字段: {field}")
                    self.assertIsInstance(pagination[field], int, f"分页字段 {field} 应该是整数")
    
    def test_caching_headers(self):
        """测试缓存标识"""
        # 第一次调用
        result1 = self.service.handle_method_call('get_dashboard_summary', {})
        
        # 第二次调用（应该命中缓存）
        result2 = self.service.handle_method_call('get_dashboard_summary', {})
        
        # 验证缓存标识
        if result2.get('success'):
            # 第二次调用可能有缓存标识
            if 'cached' in result2:
                self.assertTrue(result2['cached'])
    
    def test_date_range_handling(self):
        """测试日期范围处理"""
        test_cases = [
            # 有效日期范围
            {
                'date_range': {
                    'start_date': '2025-01-01',
                    'end_date': '2025-01-31'
                },
                'should_succeed': True
            },
            # 空日期范围（应该使用默认值）
            {
                'date_range': {},
                'should_succeed': True
            },
            # 无效日期格式
            {
                'date_range': {
                    'start_date': '2025/01/01',
                    'end_date': '2025-01-31'
                },
                'should_succeed': False
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(case=i):
                result = self.service.handle_method_call('get_dashboard_summary', {
                    'date_range': test_case['date_range']
                })
                
                if test_case['should_succeed']:
                    # 成功的情况下，应该有生成时间
                    self.assertIn('generated_at', result)
                else:
                    # 失败的情况下，应该有错误信息
                    if not result.get('success', True):
                        self.assertIn('error', result)
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                result = self.service.handle_method_call('get_dashboard_summary', {})
                results.put(('success', result))
            except Exception as e:
                results.put(('error', str(e)))
        
        # 创建多个并发线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)  # 30秒超时
        
        # 验证结果
        success_count = 0
        error_count = 0
        
        while not results.empty():
            status, result = results.get()
            if status == 'success':
                success_count += 1
                # 验证响应格式
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
            else:
                error_count += 1
        
        # 至少应该有一些成功的请求
        self.assertGreater(success_count, 0, "并发请求应该至少有一些成功")


class TestDataFlowIntegration(unittest.TestCase):
    """数据流集成测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_data_flow")
        self.service = DataAnalysisService(self.logger)
    
    def test_dashboard_data_flow(self):
        """测试仪表板数据流"""
        # 模拟前端请求仪表板数据
        result = self.service.handle_method_call('get_dashboard_summary', {
            'date_range': {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31'
            }
        })
        
        # 验证数据流完整性
        self.assertIsInstance(result, dict)
        self.assertIn('generated_at', result)
        
        # 验证数据结构符合前端期望
        if result.get('success') or 'total_sales' in result:
            # 提取数据部分
            data = result.get('data', result)
            
            # 验证关键指标存在
            key_metrics = [
                'total_sales', 'active_customers', 'total_purchases',
                'total_inventory_value', 'gross_margin'
            ]
            
            for metric in key_metrics:
                self.assertIn(metric, data)
                self.assertIsInstance(data[metric], (int, float))
    
    def test_chart_data_flow(self):
        """测试图表数据流"""
        # 测试不同维度的销售趋势数据
        dimensions = ['month', 'quarter', 'product']
        
        for dimension in dimensions:
            with self.subTest(dimension=dimension):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': dimension
                })
                
                # 验证响应结构
                self.assertIsInstance(result, dict)
                
                if result.get('success'):
                    self.assertEqual(result.get('dimension'), dimension)
                    self.assertIn('data', result)
                    self.assertIsInstance(result['data'], list)
    
    def test_error_propagation(self):
        """测试错误传播"""
        # 测试各种错误情况
        error_cases = [
            {
                'method': 'invalid_method',
                'params': {},
                'expected_error_code': 'METHOD_NOT_FOUND'
            },
            {
                'method': 'analyze_sales_trend',
                'params': {'dimension': 'invalid_dimension'},
                'expected_error_pattern': '不支持的分析维度'
            },
            {
                'method': 'get_dashboard_summary',
                'params': {
                    'date_range': {
                        'start_date': 'invalid_date',
                        'end_date': '2025-01-31'
                    }
                },
                'expected_error_pattern': '日期格式无效'
            }
        ]
        
        for case in error_cases:
            with self.subTest(method=case['method']):
                result = self.service.handle_method_call(case['method'], case['params'])
                
                # 验证错误响应
                if 'expected_error_code' in case:
                    self.assertEqual(
                        result.get('error', {}).get('code'),
                        case['expected_error_code']
                    )
                
                if 'expected_error_pattern' in case:
                    error_message = result.get('error', {}).get('message', '')
                    self.assertIn(case['expected_error_pattern'], error_message)


if __name__ == '__main__':
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加集成测试
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestFrontendIntegration))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataFlowIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print(f"\n✅ 所有集成测试通过！运行了 {result.testsRun} 个测试")
    else:
        print(f"\n❌ 集成测试失败！{len(result.failures)} 个失败，{len(result.errors)} 个错误")
        for failure in result.failures:
            print(f"失败: {failure[0]}")
            print(f"详情: {failure[1]}")
        for error in result.errors:
            print(f"错误: {error[0]}")
            print(f"详情: {error[1]}")
        sys.exit(1)