#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表渲染和前端集成测试
测试数据分析仪表板的图表渲染功能和前端数据处理
"""

import sys
import os
import json
import unittest
import time
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


class TestChartDataFormat(unittest.TestCase):
    """图表数据格式测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_chart_data")
        self.service = DataAnalysisService(self.logger)
    
    def test_sales_trend_chart_data_format(self):
        """测试销售趋势图表数据格式"""
        # 模拟销售数据
        mock_sales_data = {
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 30000, 'total_quantity': 150, 'order_count': 15},
                {'month': '2025-02', 'total_amount': 40000, 'total_quantity': 200, 'order_count': 20},
                {'month': '2025-03', 'total_amount': 35000, 'total_quantity': 175, 'order_count': 18}
            ]
        }
        
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = mock_sales_data
            
            result = self.service.handle_method_call('analyze_sales_trend', {
                'dimension': 'month'
            })
            
            if result.get('success') and result.get('data'):
                chart_data = result['data']
                
                # 验证Chart.js所需的数据结构
                self.assertIsInstance(chart_data, list)
                
                if chart_data:
                    first_item = chart_data[0]
                    
                    # 验证必需字段（Chart.js折线图）
                    required_fields = ['period', 'total_sales', 'order_count']
                    for field in required_fields:
                        self.assertIn(field, first_item, f"图表数据缺少字段: {field}")
                        self.assertIsInstance(first_item[field], (int, float, str))
                    
                    # 验证数据类型
                    self.assertIsInstance(first_item['total_sales'], (int, float))
                    self.assertIsInstance(first_item['order_count'], (int, float))
                    self.assertIsInstance(first_item['period'], str)
    
    def test_customer_analysis_pie_chart_data(self):
        """测试客户价值分析饼图数据格式"""
        # 模拟客户数据
        mock_customer_data = {
            'customer_details': [
                {
                    'customer_name': '客户A',
                    'total_amount': 50000,
                    'order_count': 25,
                    'last_order_date': '2025-01-15',
                    'first_order_date': '2024-06-01'
                },
                {
                    'customer_name': '客户B',
                    'total_amount': 30000,
                    'order_count': 15,
                    'last_order_date': '2025-01-10',
                    'first_order_date': '2024-08-01'
                }
            ]
        }
        
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = mock_customer_data
            
            result = self.service.handle_method_call('analyze_customer_value', {
                'analysis_type': 'rfm'
            })
            
            if result.get('success') and result.get('data'):
                customer_data = result['data']
                
                # 验证饼图数据结构
                self.assertIsInstance(customer_data, list)
                
                if customer_data:
                    first_customer = customer_data[0]
                    
                    # 验证RFM分析必需字段
                    required_fields = ['customer_name', 'customer_segment', 'customer_value', 'rfm_score']
                    for field in required_fields:
                        self.assertIn(field, first_customer, f"客户分析数据缺少字段: {field}")
                    
                    # 验证客户分类是有效的
                    valid_segments = ['冠军客户', '忠诚客户', '潜力客户', '新客户', '风险客户', '需要关注', '一般客户']
                    self.assertIn(first_customer['customer_segment'], valid_segments)
    
    def test_inventory_turnover_chart_data(self):
        """测试库存周转图表数据格式"""
        # 模拟库存数据
        mock_inventory_result = {
            'success': True,
            'data': [
                {'product_name': '产品A', 'current_stock': 100, 'stock_value': 10000, 'unit_cost': 100},
                {'product_name': '产品B', 'current_stock': 50, 'stock_value': 5000, 'unit_cost': 100}
            ],
            'statistics': {'total_value': 15000, 'total_items': 150}
        }
        
        with patch('scripts.data_analysis_service.generate_inventory_report') as mock_inventory, \
             patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales, \
             patch('scripts.data_analysis_service.generate_purchase_summary') as mock_purchase:
            
            mock_inventory.return_value = mock_inventory_result
            mock_sales.return_value = {'total_amount': 50000}
            mock_purchase.return_value = {'total_amount': 35000}
            
            result = self.service.handle_method_call('analyze_inventory_turnover', {})
            
            if result.get('success') and result.get('data'):
                inventory_data = result['data']
                
                # 验证库存周转数据结构
                self.assertIn('turnover_analysis', inventory_data)
                self.assertIn('overall_turnover_rate', inventory_data)
                self.assertIn('category_distribution', inventory_data)
                
                # 验证图表所需的分类数据
                category_dist = inventory_data['category_distribution']
                expected_categories = ['fast_moving', 'normal', 'slow_moving', 'dead_stock']
                for category in expected_categories:
                    self.assertIn(category, category_dist)
                    self.assertIsInstance(category_dist[category], int)
    
    def test_comparison_analysis_chart_data(self):
        """测试对比分析图表数据格式"""
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales, \
             patch('scripts.data_analysis_service.generate_purchase_summary') as mock_purchase:
            
            mock_sales.return_value = {
                'monthly_trend': [
                    {'month': '2025-01', 'total_amount': 30000, 'order_count': 15},
                    {'month': '2025-02', 'total_amount': 40000, 'order_count': 20}
                ]
            }
            mock_purchase.return_value = {
                'monthly_trend': [
                    {'month': '2025-01', 'total_amount': 20000, 'order_count': 10},
                    {'month': '2025-02', 'total_amount': 25000, 'order_count': 12}
                ]
            }
            
            result = self.service.handle_method_call('generate_comparison_analysis', {
                'metrics': ['total_sales', 'total_purchases'],
                'dimensions': ['month']
            })
            
            if result.get('success') and result.get('data'):
                comparison_data = result['data']
                
                # 验证对比分析数据结构
                self.assertIn('comparison_results', comparison_data)
                self.assertIn('summary_statistics', comparison_data)
                
                # 验证图表数据格式
                if comparison_data.get('comparison_results'):
                    first_result = comparison_data['comparison_results'][0]
                    self.assertIn('dimension_value', first_result)
                    self.assertIn('metrics', first_result)


class TestFrontendMessageHandling(unittest.TestCase):
    """前端消息处理测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_frontend_message")
        self.service = DataAnalysisService(self.logger)
    
    def test_dashboard_data_message_format(self):
        """测试仪表板数据消息格式"""
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales, \
             patch('scripts.data_analysis_service.generate_purchase_summary') as mock_purchase, \
             patch('scripts.data_analysis_service.generate_inventory_report') as mock_inventory:
            
            # 设置模拟数据
            mock_sales.return_value = {'total_amount': 100000, 'order_count': 50, 'customer_count': 25}
            mock_purchase.return_value = {'total_amount': 70000, 'order_count': 30}
            mock_inventory.return_value = {
                'success': True,
                'data': [{'stock_status': '正常'}],
                'statistics': {'total_value': 50000}
            }
            
            result = self.service.handle_method_call('get_dashboard_summary', {})
            
            # 验证前端期望的消息格式
            self.assertIsInstance(result, dict)
            self.assertIn('generated_at', result)
            
            # 验证数据结构符合前端handleDashboardData函数期望
            if result.get('success') or 'total_sales' in result:
                data = result.get('data', result)
                
                # 前端期望的关键指标
                expected_metrics = [
                    'total_sales', 'active_customers', 'total_purchases',
                    'total_inventory_value', 'gross_margin'
                ]
                
                for metric in expected_metrics:
                    self.assertIn(metric, data)
                    self.assertIsInstance(data[metric], (int, float))
    
    def test_sales_trend_message_format(self):
        """测试销售趋势消息格式"""
        mock_data = {
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 30000, 'order_count': 15}
            ]
        }
        
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = mock_data
            
            result = self.service.handle_method_call('analyze_sales_trend', {
                'dimension': 'month'
            })
            
            # 验证前端handleSalesTrendData函数期望的格式
            if result.get('success'):
                self.assertEqual(result.get('dimension'), 'month')
                self.assertIsInstance(result.get('data'), list)
                
                # 验证数据项格式
                if result['data']:
                    data_item = result['data'][0]
                    self.assertIn('period', data_item)
                    self.assertIn('total_sales', data_item)
    
    def test_error_message_format(self):
        """测试错误消息格式"""
        # 测试无效方法调用
        result = self.service.handle_method_call('invalid_method', {})
        
        # 验证前端handleError函数期望的错误格式
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
        
        error = result['error']
        self.assertIn('code', error)
        self.assertIn('message', error)
        self.assertIsInstance(error['code'], str)
        self.assertIsInstance(error['message'], str)
        
        # 验证错误代码格式
        self.assertTrue(error['code'].isupper())
        self.assertIn('_', error['code'])
    
    def test_loading_state_compatibility(self):
        """测试加载状态兼容性"""
        # 测试所有主要方法都返回及时响应
        methods_to_test = [
            ('get_dashboard_summary', {}),
            ('analyze_sales_trend', {'dimension': 'month'}),
            ('analyze_customer_value', {'analysis_type': 'rfm'}),
            ('analyze_inventory_turnover', {}),
            ('generate_comparison_analysis', {'metrics': ['total_sales'], 'dimensions': ['month']})
        ]
        
        for method, params in methods_to_test:
            with self.subTest(method=method):
                start_time = time.time()
                result = self.service.handle_method_call(method, params)
                end_time = time.time()
                
                # 验证响应时间合理（不超过30秒，考虑到可能的数据库查询）
                response_time = end_time - start_time
                self.assertLess(response_time, 30, f"方法 {method} 响应时间过长: {response_time:.2f}秒")
                
                # 验证返回格式
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)


class TestUserInteractionHandling(unittest.TestCase):
    """用户交互处理测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_user_interaction")
        self.service = DataAnalysisService(self.logger)
    
    def test_date_range_parameter_handling(self):
        """测试日期范围参数处理"""
        test_cases = [
            # 有效日期范围
            {
                'params': {
                    'date_range': {
                        'start_date': '2025-01-01',
                        'end_date': '2025-01-31'
                    }
                },
                'should_succeed': True
            },
            # 空日期范围（应该使用默认值）
            {
                'params': {'date_range': {}},
                'should_succeed': True
            },
            # 缺少日期范围
            {
                'params': {},
                'should_succeed': True
            },
            # 无效日期格式
            {
                'params': {
                    'date_range': {
                        'start_date': '2025/01/01',
                        'end_date': '2025-01-31'
                    }
                },
                'should_succeed': False
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(case=i):
                result = self.service.handle_method_call('get_dashboard_summary', test_case['params'])
                
                if test_case['should_succeed']:
                    # 成功的情况下，应该有生成时间
                    self.assertIn('generated_at', result)
                else:
                    # 失败的情况下，应该有错误信息
                    if not result.get('success', True):
                        self.assertIn('error', result)
                        self.assertIn('日期格式无效', result['error']['message'])
    
    def test_dimension_parameter_handling(self):
        """测试维度参数处理"""
        valid_dimensions = ['month', 'quarter', 'product']
        invalid_dimensions = ['invalid', 'year', 'week']
        
        # 测试有效维度
        for dimension in valid_dimensions:
            with self.subTest(dimension=dimension):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': dimension
                })
                
                # 应该成功或者是数据相关的错误
                if not result.get('success', True):
                    self.assertNotEqual(result.get('error', {}).get('code'), 'METHOD_NOT_FOUND')
                else:
                    self.assertEqual(result.get('dimension'), dimension)
        
        # 测试无效维度
        for dimension in invalid_dimensions:
            with self.subTest(dimension=dimension):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': dimension
                })
                
                if not result.get('success', True):
                    self.assertIn('不支持的分析维度', result.get('error', {}).get('message', ''))
    
    def test_pagination_parameter_handling(self):
        """测试分页参数处理"""
        pagination_params = [
            {'page': 1, 'page_size': 10},
            {'page': 2, 'page_size': 20},
            {'page': 1, 'page_size': 50}
        ]
        
        for params in pagination_params:
            with self.subTest(params=params):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': 'product',
                    **params
                })
                
                # 验证分页参数被正确处理
                if result.get('success') and 'pagination' in result:
                    pagination = result['pagination']
                    self.assertEqual(pagination['current_page'], params['page'])
                    self.assertEqual(pagination['page_size'], params['page_size'])
    
    def test_button_click_simulation(self):
        """测试按钮点击模拟"""
        # 模拟前端按钮点击事件
        button_actions = [
            ('refresh_dashboard', 'get_dashboard_summary', {}),
            ('analyze_monthly_trend', 'analyze_sales_trend', {'dimension': 'month'}),
            ('analyze_quarterly_trend', 'analyze_sales_trend', {'dimension': 'quarter'}),
            ('analyze_product_ranking', 'analyze_sales_trend', {'dimension': 'product'}),
            ('analyze_customer_value', 'analyze_customer_value', {'analysis_type': 'rfm'}),
            ('analyze_inventory', 'analyze_inventory_turnover', {})
        ]
        
        for button_id, method, params in button_actions:
            with self.subTest(button=button_id):
                result = self.service.handle_method_call(method, params)
                
                # 验证每个按钮都能触发相应的分析
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
                
                # 验证响应时间合理
                self.assertIsInstance(result['generated_at'], str)


class TestChartRenderingCompatibility(unittest.TestCase):
    """图表渲染兼容性测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_chart_compatibility")
        self.service = DataAnalysisService(self.logger)
    
    def test_chartjs_line_chart_compatibility(self):
        """测试Chart.js折线图兼容性"""
        mock_data = {
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 30000, 'order_count': 15},
                {'month': '2025-02', 'total_amount': 40000, 'order_count': 20},
                {'month': '2025-03', 'total_amount': 35000, 'order_count': 18}
            ]
        }
        
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = mock_data
            
            result = self.service.handle_method_call('analyze_sales_trend', {
                'dimension': 'month'
            })
            
            if result.get('success') and result.get('data'):
                chart_data = result['data']
                
                # 验证Chart.js折线图所需的数据格式
                self.assertIsInstance(chart_data, list)
                
                # 模拟Chart.js数据转换
                labels = [item['period'] for item in chart_data]
                sales_values = [item['total_sales'] for item in chart_data]
                order_values = [item['order_count'] for item in chart_data]
                
                # 验证数据可以被Chart.js使用
                self.assertEqual(len(labels), len(sales_values))
                self.assertEqual(len(labels), len(order_values))
                self.assertTrue(all(isinstance(v, (int, float)) for v in sales_values))
                self.assertTrue(all(isinstance(v, (int, float)) for v in order_values))
    
    def test_chartjs_pie_chart_compatibility(self):
        """测试Chart.js饼图兼容性"""
        # 模拟客户分析数据
        mock_customer_data = {
            'customer_details': [
                {'customer_name': '客户A', 'total_amount': 50000, 'order_count': 25, 'last_order_date': '2025-01-15'},
                {'customer_name': '客户B', 'total_amount': 30000, 'order_count': 15, 'last_order_date': '2025-01-10'}
            ]
        }
        
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = mock_customer_data
            
            result = self.service.handle_method_call('analyze_customer_value', {
                'analysis_type': 'rfm'
            })
            
            if result.get('success') and result.get('data'):
                customer_data = result['data']
                
                # 模拟饼图数据转换
                segment_distribution = {}
                for customer in customer_data:
                    segment = customer.get('customer_segment', '未分类')
                    segment_distribution[segment] = segment_distribution.get(segment, 0) + 1
                
                # 验证饼图数据格式
                labels = list(segment_distribution.keys())
                values = list(segment_distribution.values())
                
                self.assertGreater(len(labels), 0)
                self.assertEqual(len(labels), len(values))
                self.assertTrue(all(isinstance(v, int) for v in values))
    
    def test_chartjs_bar_chart_compatibility(self):
        """测试Chart.js柱状图兼容性"""
        # 模拟库存周转数据
        mock_inventory_result = {
            'success': True,
            'data': [
                {'product_name': '产品A', 'current_stock': 100, 'stock_value': 10000},
                {'product_name': '产品B', 'current_stock': 50, 'stock_value': 5000}
            ],
            'statistics': {'total_value': 15000}
        }
        
        with patch('scripts.data_analysis_service.generate_inventory_report') as mock_inventory:
            mock_inventory.return_value = mock_inventory_result
            
            result = self.service.handle_method_call('analyze_inventory_turnover', {})
            
            if result.get('success') and result.get('data'):
                inventory_data = result['data']
                
                # 模拟柱状图数据转换
                if 'turnover_analysis' in inventory_data:
                    turnover_items = inventory_data['turnover_analysis'][:10]  # 前10个
                    
                    labels = [item['product_name'] for item in turnover_items]
                    turnover_rates = [item['turnover_rate'] for item in turnover_items]
                    
                    # 验证柱状图数据格式
                    self.assertEqual(len(labels), len(turnover_rates))
                    self.assertTrue(all(isinstance(rate, (int, float)) for rate in turnover_rates))
    
    def test_responsive_chart_data(self):
        """测试响应式图表数据"""
        # 测试不同数据量的处理
        data_sizes = [5, 50, 500]  # 小、中、大数据量
        
        for size in data_sizes:
            with self.subTest(size=size):
                # 模拟不同大小的数据集
                mock_data = {
                    'top_products': [
                        {
                            'material_code': f'P{i:03d}',
                            'material_name': f'产品{i}',
                            'total_amount': 1000 * (size - i),
                            'total_quantity': 10 * (size - i),
                            'order_count': size - i
                        }
                        for i in range(min(size, 100))  # 限制最大100个产品
                    ]
                }
                
                with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
                    mock_sales.return_value = mock_data
                    
                    result = self.service.handle_method_call('analyze_sales_trend', {
                        'dimension': 'product'
                    })
                    
                    if result.get('success') and result.get('data'):
                        chart_data = result['data']
                        
                        # 验证数据量合理（前端图表性能考虑）
                        self.assertLessEqual(len(chart_data), 100)
                        
                        # 验证数据结构一致性
                        if chart_data:
                            first_item = chart_data[0]
                            required_fields = ['product_name', 'total_sales', 'rank']
                            for field in required_fields:
                                self.assertIn(field, first_item)


if __name__ == '__main__':
    # 创建测试套件
    test_classes = [
        TestChartDataFormat,
        TestFrontendMessageHandling,
        TestUserInteractionHandling,
        TestChartRenderingCompatibility
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    print(f"\n{'='*60}")
    if result.wasSuccessful():
        print(f"✅ 所有图表渲染测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print(f"❌ 图表渲染测试失败！")
        print(f"运行了 {result.testsRun} 个测试")
        print(f"{len(result.failures)} 个失败，{len(result.errors)} 个错误")
        
        if result.failures:
            print(f"\n失败的测试:")
            for test, traceback in result.failures:
                print(f"- {test}")
        
        if result.errors:
            print(f"\n错误的测试:")
            for test, traceback in result.errors:
                print(f"- {test}")
        
        sys.exit(1)
    
    print(f"{'='*60}")