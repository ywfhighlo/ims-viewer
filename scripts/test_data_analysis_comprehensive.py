#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析服务综合测试套件
包含单元测试和集成测试，覆盖所有数据分析服务的方法和功能
"""

import sys
import os
import json
import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


class TestDataAnalysisServiceCore(unittest.TestCase):
    """数据分析服务核心功能测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_data_analysis_core")
        self.service = DataAnalysisService(self.logger)
        
        # 模拟完整的测试数据
        self.mock_sales_summary = {
            'total_amount': 500000,
            'order_count': 250,
            'customer_count': 100,
            'average_order_value': 2000,
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 150000, 'total_quantity': 750, 'order_count': 75},
                {'month': '2025-02', 'total_amount': 200000, 'total_quantity': 1000, 'order_count': 100},
                {'month': '2025-03', 'total_amount': 150000, 'total_quantity': 750, 'order_count': 75}
            ],
            'top_products': [
                {'material_code': 'P001', 'material_name': '产品A', 'total_amount': 100000, 'total_quantity': 500, 'order_count': 50},
                {'material_code': 'P002', 'material_name': '产品B', 'total_amount': 80000, 'total_quantity': 400, 'order_count': 40},
                {'material_code': 'P003', 'material_name': '产品C', 'total_amount': 60000, 'total_quantity': 300, 'order_count': 30}
            ],
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
        
        self.mock_purchase_summary = {
            'total_amount': 350000,
            'order_count': 150,
            'supplier_count': 50,
            'average_order_value': 2333
        }
        
        self.mock_inventory_result = {
            'success': True,
            'data': [
                {
                    'product_name': '产品A',
                    'material_code': 'P001',
                    'current_stock': 200,
                    'stock_value': 20000,
                    'unit_cost': 100,
                    'stock_status': '正常'
                },
                {
                    'product_name': '产品B',
                    'material_code': 'P002',
                    'current_stock': 50,
                    'stock_value': 10000,
                    'unit_cost': 200,
                    'stock_status': '低库存'
                },
                {
                    'product_name': '产品C',
                    'material_code': 'P003',
                    'current_stock': 0,
                    'stock_value': 0,
                    'unit_cost': 150,
                    'stock_status': '缺货'
                }
            ],
            'statistics': {
                'total_value': 30000,
                'total_items': 250
            }
        }
    
    def test_handle_method_call_valid_methods(self):
        """测试有效方法调用"""
        valid_methods = [
            'get_dashboard_summary',
            'analyze_sales_trend',
            'analyze_customer_value',
            'analyze_inventory_turnover',
            'generate_comparison_analysis'
        ]
        
        for method in valid_methods:
            with self.subTest(method=method):
                result = self.service.handle_method_call(method, {})
                
                # 验证响应结构
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
                
                # 如果失败，应该是数据相关的错误，不是方法不存在
                if not result.get('success', True):
                    self.assertNotEqual(
                        result.get('error', {}).get('code'),
                        'METHOD_NOT_FOUND'
                    )
    
    def test_handle_method_call_invalid_method(self):
        """测试无效方法调用"""
        result = self.service.handle_method_call('invalid_method', {})
        
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error', {}).get('code'), 'METHOD_NOT_FOUND')
        self.assertIn('不支持的方法', result.get('error', {}).get('message', ''))
    
    def test_safe_get_numeric_comprehensive(self):
        """测试安全数值获取的各种情况"""
        test_cases = [
            # (数据, 键, 默认值, 期望结果)
            ({'value': 100}, 'value', 0, 100),
            ({'value': '100.5'}, 'value', 0, 100.5),
            ({'value': '0'}, 'value', 10, 0.0),
            ({}, 'value', 50, 50),
            ({'value': None}, 'value', 25, 25),
            ({'value': 'invalid'}, 'value', 15, 15),
            ({'value': []}, 'value', 20, 20),
            ({'value': {}}, 'value', 30, 30),
            ({'value': True}, 'value', 5, 5),  # 布尔值应该返回默认值
        ]
        
        for data, key, default, expected in test_cases:
            with self.subTest(data=data, key=key):
                result = self.service._safe_get_numeric(data, key, default)
                self.assertEqual(result, expected)
    
    def test_validate_date_format_comprehensive(self):
        """测试日期格式验证的各种情况"""
        valid_dates = [
            '2025-01-01',
            '2025-12-31',
            '2024-02-29',  # 闰年
            '2025-06-15'
        ]
        
        invalid_dates = [
            '2025/01/01',
            '01-01-2025',
            '2025-1-1',
            '2025-13-01',  # 无效月份
            '2025-02-30',  # 无效日期
            'invalid',
            '',
            None,
            123,
            [],
            {}
        ]
        
        for date in valid_dates:
            with self.subTest(date=date):
                self.assertTrue(self.service._validate_date_format(date))
        
        for date in invalid_dates:
            with self.subTest(date=date):
                self.assertFalse(self.service._validate_date_format(date))


class TestDashboardSummary(unittest.TestCase):
    """仪表板概览功能测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_dashboard")
        self.service = DataAnalysisService(self.logger)
    
    @patch('scripts.data_analysis_service.generate_sales_summary')
    @patch('scripts.data_analysis_service.generate_purchase_summary')
    @patch('scripts.data_analysis_service.generate_inventory_report')
    @patch('scripts.data_analysis_service.generate_receivables_summary')
    @patch('scripts.data_analysis_service.generate_payables_summary')
    def test_dashboard_summary_complete_data(self, mock_payables, mock_receivables, 
                                           mock_inventory, mock_purchase, mock_sales):
        """测试完整数据的仪表板概览"""
        # 设置模拟返回值
        mock_sales.return_value = {
            'total_amount': 100000,
            'order_count': 50,
            'customer_count': 25,
            'average_order_value': 2000
        }
        mock_purchase.return_value = {
            'total_amount': 70000,
            'order_count': 30,
            'supplier_count': 15,
            'average_order_value': 2333
        }
        mock_inventory.return_value = {
            'success': True,
            'data': [
                {'stock_status': '低库存'},
                {'stock_status': '缺货'},
                {'stock_status': '正常'}
            ],
            'statistics': {'total_value': 50000, 'total_items': 100}
        }
        mock_receivables.return_value = {
            'total_receivables': 15000,
            'overdue_amount': 3000
        }
        mock_payables.return_value = {
            'total_payables': 8000,
            'overdue_amount': 1000
        }
        
        # 测试参数
        params = {
            'date_range': {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31'
            }
        }
        
        # 调用方法
        result = self.service._get_dashboard_summary_uncached(params)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn('generated_at', result)
        
        # 验证关键指标
        self.assertEqual(result['total_sales'], 100000)
        self.assertEqual(result['total_purchases'], 70000)
        self.assertEqual(result['gross_margin'], 30000)
        self.assertEqual(result['active_customers'], 25)
        self.assertEqual(result['total_inventory_value'], 50000)
        self.assertEqual(result['low_stock_items'], 1)
        self.assertEqual(result['out_of_stock_items'], 1)
        self.assertEqual(result['total_receivables'], 15000)
        self.assertEqual(result['total_payables'], 8000)
        
        # 验证计算字段
        self.assertAlmostEqual(result['gross_margin_rate'], 30.0, places=1)
        self.assertAlmostEqual(result['inventory_turnover_estimate'], 1.4, places=1)
        
        # 验证元数据
        self.assertIn('date_range', result)
        self.assertIn('data_sources', result)
        self.assertTrue(result['data_sources']['sales_available'])
        self.assertTrue(result['data_sources']['inventory_available'])
    
    def test_dashboard_summary_missing_data(self):
        """测试缺失数据的仪表板概览"""
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales, \
             patch('scripts.data_analysis_service.generate_purchase_summary') as mock_purchase, \
             patch('scripts.data_analysis_service.generate_inventory_report') as mock_inventory:
            
            # 模拟数据获取失败
            mock_sales.return_value = None
            mock_purchase.return_value = {}
            mock_inventory.return_value = {'success': False}
            
            result = self.service._get_dashboard_summary_uncached({})
            
            # 验证默认值处理
            self.assertEqual(result['total_sales'], 0)
            self.assertEqual(result['total_purchases'], 0)
            self.assertEqual(result['total_inventory_value'], 0)
            self.assertFalse(result['data_sources']['sales_available'])
            self.assertFalse(result['data_sources']['inventory_available'])
    
    def test_dashboard_summary_invalid_dates(self):
        """测试无效日期的处理"""
        invalid_params = [
            {'date_range': {'start_date': '2025/01/01', 'end_date': '2025-01-31'}},
            {'date_range': {'start_date': '2025-01-01', 'end_date': 'invalid'}},
            {'date_range': {'start_date': '2025-13-01', 'end_date': '2025-01-31'}}
        ]
        
        for params in invalid_params:
            with self.subTest(params=params):
                result = self.service._get_dashboard_summary_uncached(params)
                
                # 验证错误响应
                self.assertTrue(result.get('error'))
                self.assertEqual(result.get('error_code'), 'DASHBOARD_SUMMARY_FAILED')
                self.assertIn('日期格式无效', result.get('error_message', ''))


class TestSalesTrendAnalysis(unittest.TestCase):
    """销售趋势分析测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_sales_trend")
        self.service = DataAnalysisService(self.logger)
        
        self.mock_sales_data = {
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 30000, 'total_quantity': 150, 'order_count': 15},
                {'month': '2025-02', 'total_amount': 40000, 'total_quantity': 200, 'order_count': 20},
                {'month': '2025-03', 'total_amount': 35000, 'total_quantity': 175, 'order_count': 18},
                {'month': '2025-04', 'total_amount': 45000, 'total_quantity': 225, 'order_count': 22}
            ],
            'top_products': [
                {'material_code': 'P001', 'material_name': '产品A', 'total_amount': 50000, 'total_quantity': 250, 'order_count': 25},
                {'material_code': 'P002', 'material_name': '产品B', 'total_amount': 40000, 'total_quantity': 200, 'order_count': 20}
            ]
        }
    
    def test_monthly_trend_processing(self):
        """测试月度趋势数据处理"""
        result = self.service._process_monthly_trend(self.mock_sales_data)
        
        # 验证数据结构
        self.assertEqual(len(result), 4)
        
        # 验证第一个月的数据
        first_month = result[0]
        self.assertEqual(first_month['month'], '2025-01')
        self.assertEqual(first_month['total_sales'], 30000)
        self.assertEqual(first_month['order_count'], 15)
        self.assertEqual(first_month['avg_order_value'], 2000)  # 30000 / 15
        
        # 验证数据排序
        months = [item['month'] for item in result]
        self.assertEqual(months, sorted(months))
        
        # 验证所有必需字段存在
        required_fields = ['period', 'month', 'total_sales', 'total_amount', 'total_quantity', 'order_count', 'avg_order_value']
        for field in required_fields:
            self.assertIn(field, first_month)
    
    def test_quarterly_trend_processing(self):
        """测试季度趋势数据处理"""
        result = self.service._process_quarterly_trend(self.mock_sales_data)
        
        # 验证季度聚合
        self.assertEqual(len(result), 2)  # 2025-Q1 和 2025-Q2
        
        # 验证第一季度数据
        q1_data = next(item for item in result if item['quarter'] == '2025-Q1')
        self.assertEqual(q1_data['total_sales'], 105000)  # 30000 + 40000 + 35000
        self.assertEqual(q1_data['order_count'], 53)  # 15 + 20 + 18
        self.assertEqual(q1_data['months_count'], 3)
        
        # 验证第二季度数据
        q2_data = next(item for item in result if item['quarter'] == '2025-Q2')
        self.assertEqual(q2_data['total_sales'], 45000)
        self.assertEqual(q2_data['months_count'], 1)
        
        # 验证必需字段
        required_fields = ['period', 'quarter', 'year', 'quarter_num', 'total_sales', 'avg_order_value']
        for field in required_fields:
            self.assertIn(field, q1_data)
    
    def test_product_analysis_processing(self):
        """测试产品分析数据处理"""
        result = self.service._process_product_analysis(self.mock_sales_data)
        
        # 验证产品排行
        self.assertEqual(len(result), 2)
        
        # 验证排名和数据
        first_product = result[0]
        self.assertEqual(first_product['rank'], 1)
        self.assertEqual(first_product['product_name'], '产品A')
        self.assertEqual(first_product['total_sales'], 50000)
        self.assertEqual(first_product['avg_unit_price'], 200)  # 50000 / 250
        
        second_product = result[1]
        self.assertEqual(second_product['rank'], 2)
        self.assertEqual(second_product['product_name'], '产品B')
        
        # 验证必需字段
        required_fields = ['rank', 'product_name', 'total_sales', 'total_quantity', 'order_count', 'avg_order_value', 'avg_unit_price']
        for field in required_fields:
            self.assertIn(field, first_product)
    
    @patch('scripts.data_analysis_service.generate_sales_summary')
    def test_sales_trend_analysis_dimensions(self, mock_sales):
        """测试不同维度的销售趋势分析"""
        mock_sales.return_value = self.mock_sales_data
        
        dimensions = ['month', 'quarter', 'product']
        
        for dimension in dimensions:
            with self.subTest(dimension=dimension):
                params = {'dimension': dimension}
                result = self.service._analyze_sales_trend_uncached(params)
                
                # 验证响应结构
                self.assertTrue(result.get('success'))
                self.assertEqual(result.get('dimension'), dimension)
                self.assertIsInstance(result.get('data'), list)
                self.assertIn('summary', result)
                self.assertIn('generated_at', result)
    
    def test_sales_trend_invalid_dimension(self):
        """测试无效维度处理"""
        params = {'dimension': 'invalid_dimension'}
        result = self.service._analyze_sales_trend_uncached(params)
        
        # 验证错误响应
        self.assertFalse(result.get('success'))
        self.assertIn('不支持的分析维度', result.get('error', {}).get('message', ''))
    
    def test_empty_sales_data_handling(self):
        """测试空销售数据处理"""
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = None
            
            params = {'dimension': 'month'}
            result = self.service._analyze_sales_trend_uncached(params)
            
            # 验证空数据响应
            self.assertTrue(result.get('success'))
            self.assertEqual(len(result.get('data', [])), 0)
            self.assertIn('未找到符合条件的销售数据', result.get('message', ''))


class TestCustomerValueAnalysis(unittest.TestCase):
    """客户价值分析测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_customer_value")
        self.service = DataAnalysisService(self.logger)
    
    def test_customer_classification(self):
        """测试客户分类算法"""
        test_cases = [
            # (R, F, M, 期望分类)
            (5, 5, 5, '冠军客户'),
            (4, 5, 5, '冠军客户'),
            (3, 5, 5, '忠诚客户'),
            (2, 4, 4, '忠诚客户'),
            (5, 3, 4, '潜力客户'),
            (4, 2, 3, '潜力客户'),
            (5, 1, 2, '新客户'),
            (4, 2, 1, '新客户'),
            (1, 3, 3, '风险客户'),
            (2, 2, 2, '风险客户'),
            (2, 3, 5, '需要关注'),
            (1, 2, 4, '需要关注'),
            (3, 3, 3, '一般客户'),
            (3, 2, 2, '一般客户')
        ]
        
        for recency, frequency, monetary, expected_class in test_cases:
            with self.subTest(R=recency, F=frequency, M=monetary):
                result = self.service._classify_customer(recency, frequency, monetary)
                self.assertEqual(result, expected_class)
    
    def test_customer_segmentation_distribution(self):
        """测试客户分类分布计算"""
        rfm_data = [
            {'customer_segment': '冠军客户', 'customer_value': 50000},
            {'customer_segment': '冠军客户', 'customer_value': 40000},
            {'customer_segment': '忠诚客户', 'customer_value': 30000},
            {'customer_segment': '潜力客户', 'customer_value': 20000},
            {'customer_segment': '风险客户', 'customer_value': 10000}
        ]
        
        distribution = self.service._calculate_segment_distribution(rfm_data)
        
        # 验证分布统计
        self.assertEqual(distribution['冠军客户'], 2)
        self.assertEqual(distribution['忠诚客户'], 1)
        self.assertEqual(distribution['潜力客户'], 1)
        self.assertEqual(distribution['风险客户'], 1)
    
    def test_customer_grouping_by_segment(self):
        """测试客户分类分组"""
        rfm_data = [
            {'customer_segment': '冠军客户', 'customer_value': 50000},
            {'customer_segment': '冠军客户', 'customer_value': 40000},
            {'customer_segment': '忠诚客户', 'customer_value': 30000}
        ]
        
        segments = self.service._group_customers_by_segment(rfm_data)
        
        # 验证冠军客户分组
        champion_segment = segments['冠军客户']
        self.assertEqual(champion_segment['customer_count'], 2)
        self.assertEqual(champion_segment['total_value'], 90000)
        self.assertEqual(champion_segment['avg_value'], 45000)
        
        # 验证忠诚客户分组
        loyal_segment = segments['忠诚客户']
        self.assertEqual(loyal_segment['customer_count'], 1)
        self.assertEqual(loyal_segment['total_value'], 30000)
        self.assertEqual(loyal_segment['avg_value'], 30000)


class TestInventoryTurnoverAnalysis(unittest.TestCase):
    """库存周转分析测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_inventory_turnover")
        self.service = DataAnalysisService(self.logger)
    
    def test_product_turnover_calculation(self):
        """测试产品周转率计算"""
        inventory_data = [
            {
                'product_name': '产品A',
                'current_stock': 100,
                'stock_value': 10000,
                'unit_cost': 100
            },
            {
                'product_name': '产品B',
                'current_stock': 50,
                'stock_value': 5000,
                'unit_cost': 100
            }
        ]
        
        product_sales_data = {
            '产品A': {
                'total_sales_amount': 20000,
                'total_quantity_sold': 200,
                'sales_count': 10,
                'last_sale_date': '2025-01-15'
            },
            '产品B': {
                'total_sales_amount': 2000,
                'total_quantity_sold': 20,
                'sales_count': 2,
                'last_sale_date': '2024-06-01'
            }
        }
        
        result = self.service._calculate_product_turnover_analysis(
            inventory_data, 
            product_sales_data, 
            365, 
            {'fast': 4.0, 'slow': 1.0}
        )
        
        # 验证结果数量
        self.assertEqual(len(result), 2)
        
        # 验证产品A的周转分析
        product_a = next(item for item in result if item['product_name'] == '产品A')
        self.assertGreater(product_a['turnover_rate'], 1.0)
        self.assertEqual(product_a['category'], 'fast_moving')
        self.assertLess(product_a['days_since_last_sale'], 30)
        
        # 验证产品B的周转分析（长时间未销售）
        product_b = next(item for item in result if item['product_name'] == '产品B')
        self.assertEqual(product_b['category'], 'dead_stock')
        self.assertGreater(product_b['days_since_last_sale'], 180)
        
        # 验证必需字段
        required_fields = [
            'product_name', 'turnover_rate', 'category', 'category_name',
            'stock_value', 'days_since_last_sale', 'warning_level'
        ]
        for field in required_fields:
            self.assertIn(field, product_a)
    
    def test_inventory_warnings_generation(self):
        """测试库存预警生成"""
        turnover_analysis = [
            {
                'product_name': '产品A',
                'category': 'fast_moving',
                'stock_value': 5000,
                'current_stock': 100
            },
            {
                'product_name': '产品B',
                'category': 'dead_stock',
                'stock_value': 15000,
                'current_stock': 50
            },
            {
                'product_name': '产品C',
                'category': 'slow_moving',
                'stock_value': 12000,
                'current_stock': 0
            },
            {
                'product_name': '产品D',
                'category': 'slow_moving',
                'stock_value': 8000,
                'current_stock': 20
            }
        ]
        
        warnings = self.service._generate_inventory_warnings(
            turnover_analysis, 
            {'fast': 4.0, 'slow': 1.0}
        )
        
        # 验证预警类型
        warning_types = [w['type'] for w in warnings]
        self.assertIn('dead_stock', warning_types)
        self.assertIn('slow_moving', warning_types)
        self.assertIn('out_of_stock', warning_types)
        
        # 验证呆滞库存预警
        dead_stock_warning = next(w for w in warnings if w['type'] == 'dead_stock')
        self.assertEqual(dead_stock_warning['level'], 'high')
        self.assertEqual(dead_stock_warning['count'], 1)
        self.assertEqual(dead_stock_warning['value'], 15000)
        
        # 验证缺货预警
        out_of_stock_warning = next(w for w in warnings if w['type'] == 'out_of_stock')
        self.assertEqual(out_of_stock_warning['count'], 1)
        self.assertIn('产品C', out_of_stock_warning['items'])


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_error_handling")
        self.service = DataAnalysisService(self.logger)
    
    def test_database_connection_error_handling(self):
        """测试数据库连接错误处理"""
        with patch.object(self.service.query_optimizer, '_get_db_connection') as mock_db:
            mock_db.side_effect = Exception("数据库连接失败")
            
            result = self.service.handle_method_call('get_dashboard_summary', {})
            
            # 验证错误被正确处理
            self.assertFalse(result.get('success', True))
            self.assertIn('error', result)
    
    def test_invalid_parameter_handling(self):
        """测试无效参数处理"""
        test_cases = [
            {
                'method': 'analyze_sales_trend',
                'params': {'dimension': 'invalid'},
                'expected_error_pattern': '不支持的分析维度'
            },
            {
                'method': 'get_dashboard_summary',
                'params': {'date_range': {'start_date': 'invalid'}},
                'expected_error_pattern': '日期格式无效'
            }
        ]
        
        for case in test_cases:
            with self.subTest(method=case['method']):
                result = self.service.handle_method_call(case['method'], case['params'])
                
                if not result.get('success', True):
                    error_message = result.get('error', {}).get('message', '')
                    self.assertIn(case['expected_error_pattern'], error_message)
    
    def test_empty_data_handling(self):
        """测试空数据处理"""
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = None
            
            result = self.service.handle_method_call('analyze_sales_trend', {
                'dimension': 'month'
            })
            
            # 验证空数据被正确处理
            self.assertTrue(result.get('success'))
            self.assertEqual(len(result.get('data', [])), 0)
            self.assertIn('message', result)


if __name__ == '__main__':
    # 创建测试套件
    test_classes = [
        TestDataAnalysisServiceCore,
        TestDashboardSummary,
        TestSalesTrendAnalysis,
        TestCustomerValueAnalysis,
        TestInventoryTurnoverAnalysis,
        TestErrorHandling
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
        print(f"✅ 所有测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print(f"❌ 测试失败！")
        print(f"运行了 {result.testsRun} 个测试")
        print(f"{len(result.failures)} 个失败，{len(result.errors)} 个错误")
        
        if result.failures:
            print(f"\n失败的测试:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
        
        if result.errors:
            print(f"\n错误的测试:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback.split('\\n')[-2]}")
        
        sys.exit(1)
    
    print(f"{'='*60}")