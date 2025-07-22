#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析服务单元测试
测试数据分析服务的各个方法的单元测试
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


class TestDataAnalysisService(unittest.TestCase):
    """数据分析服务单元测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_data_analysis")
        self.service = DataAnalysisService(self.logger)
        
        # 模拟数据
        self.mock_sales_summary = {
            'total_amount': 100000,
            'order_count': 50,
            'customer_count': 25,
            'average_order_value': 2000,
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 30000, 'total_quantity': 150, 'order_count': 15},
                {'month': '2025-02', 'total_amount': 40000, 'total_quantity': 200, 'order_count': 20},
                {'month': '2025-03', 'total_amount': 30000, 'total_quantity': 150, 'order_count': 15}
            ],
            'top_products': [
                {'material_code': 'P001', 'material_name': '产品A', 'total_amount': 20000, 'total_quantity': 100, 'order_count': 10},
                {'material_code': 'P002', 'material_name': '产品B', 'total_amount': 15000, 'total_quantity': 75, 'order_count': 8}
            ]
        }
        
        self.mock_purchase_summary = {
            'total_amount': 70000,
            'order_count': 30,
            'supplier_count': 15,
            'average_order_value': 2333
        }
        
        self.mock_inventory_result = {
            'success': True,
            'data': [
                {'product_name': '产品A', 'current_stock': 100, 'stock_value': 10000, 'unit_cost': 100, 'stock_status': '正常'},
                {'product_name': '产品B', 'current_stock': 0, 'stock_value': 0, 'unit_cost': 200, 'stock_status': '缺货'}
            ],
            'statistics': {
                'total_value': 10000,
                'total_items': 100
            }
        }
    
    def test_safe_get_numeric(self):
        """测试安全获取数值方法"""
        # 测试正常数值
        result = self.service._safe_get_numeric({'value': 100}, 'value', 0)
        self.assertEqual(result, 100)
        
        # 测试字符串数值
        result = self.service._safe_get_numeric({'value': '100'}, 'value', 0)
        self.assertEqual(result, 100.0)
        
        # 测试缺失键
        result = self.service._safe_get_numeric({}, 'value', 50)
        self.assertEqual(result, 50)
        
        # 测试无效数值
        result = self.service._safe_get_numeric({'value': 'invalid'}, 'value', 0)
        self.assertEqual(result, 0)
        
        # 测试None值
        result = self.service._safe_get_numeric({'value': None}, 'value', 10)
        self.assertEqual(result, 10)
    
    def test_validate_date_format(self):
        """测试日期格式验证方法"""
        # 测试有效日期格式
        self.assertTrue(self.service._validate_date_format('2025-01-01'))
        self.assertTrue(self.service._validate_date_format('2025-12-31'))
        
        # 测试无效日期格式
        self.assertFalse(self.service._validate_date_format('2025/01/01'))
        self.assertFalse(self.service._validate_date_format('01-01-2025'))
        self.assertFalse(self.service._validate_date_format('invalid'))
        self.assertFalse(self.service._validate_date_format(''))
        self.assertFalse(self.service._validate_date_format(None))
    
    @patch('scripts.data_analysis_service.generate_sales_summary')
    @patch('scripts.data_analysis_service.generate_purchase_summary')
    @patch('scripts.data_analysis_service.generate_inventory_report')
    @patch('scripts.data_analysis_service.generate_receivables_summary')
    @patch('scripts.data_analysis_service.generate_payables_summary')
    def test_get_dashboard_summary_success(self, mock_payables, mock_receivables, 
                                         mock_inventory, mock_purchase, mock_sales):
        """测试仪表板概览数据获取成功"""
        # 设置模拟返回值
        mock_sales.return_value = self.mock_sales_summary
        mock_purchase.return_value = self.mock_purchase_summary
        mock_inventory.return_value = self.mock_inventory_result
        mock_receivables.return_value = {'total_receivables': 5000, 'overdue_amount': 1000}
        mock_payables.return_value = {'total_payables': 3000, 'overdue_amount': 500}
        
        # 测试参数
        params = {
            'date_range': {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31'
            }
        }
        
        # 调用方法
        result = self.service._get_dashboard_summary_uncached(params)
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_sales'], 100000)
        self.assertEqual(result['total_purchases'], 70000)
        self.assertEqual(result['gross_margin'], 30000)
        self.assertEqual(result['active_customers'], 25)
        self.assertEqual(result['total_inventory_value'], 10000)
        self.assertEqual(result['low_stock_items'], 0)
        self.assertEqual(result['out_of_stock_items'], 1)
        
        # 验证调用参数
        mock_sales.assert_called_once_with('2025-01-01', '2025-01-31', self.logger)
        mock_purchase.assert_called_once_with('2025-01-01', '2025-01-31', self.logger)
    
    def test_get_dashboard_summary_invalid_date(self):
        """测试仪表板概览数据获取 - 无效日期"""
        params = {
            'date_range': {
                'start_date': '2025/01/01',  # 无效格式
                'end_date': '2025-01-31'
            }
        }
        
        result = self.service._get_dashboard_summary_uncached(params)
        
        # 验证错误响应
        self.assertTrue(result.get('error'))
        self.assertEqual(result.get('error_code'), 'DASHBOARD_SUMMARY_FAILED')
        self.assertIn('开始日期格式无效', result.get('error_message', ''))
    
    def test_process_monthly_trend(self):
        """测试月度趋势数据处理"""
        result = self.service._process_monthly_trend(self.mock_sales_summary)
        
        # 验证结果
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['month'], '2025-01')
        self.assertEqual(result[0]['total_sales'], 30000)
        self.assertEqual(result[0]['avg_order_value'], 2000)  # 30000 / 15
        
        # 验证排序
        months = [item['month'] for item in result]
        self.assertEqual(months, sorted(months))
    
    def test_process_quarterly_trend(self):
        """测试季度趋势数据处理"""
        result = self.service._process_quarterly_trend(self.mock_sales_summary)
        
        # 验证结果
        self.assertEqual(len(result), 1)  # 所有月份都在2025年第一季度
        self.assertEqual(result[0]['quarter'], '2025-Q1')
        self.assertEqual(result[0]['total_sales'], 100000)  # 30000 + 40000 + 30000
        self.assertEqual(result[0]['months_count'], 3)
    
    def test_process_product_analysis(self):
        """测试产品分析数据处理"""
        result = self.service._process_product_analysis(self.mock_sales_summary)
        
        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['rank'], 1)
        self.assertEqual(result[0]['product_name'], '产品A')
        self.assertEqual(result[0]['total_sales'], 20000)
        self.assertEqual(result[0]['avg_unit_price'], 200)  # 20000 / 100
    
    def test_classify_customer(self):
        """测试客户分类算法"""
        # 测试冠军客户
        result = self.service._classify_customer(5, 5, 5)
        self.assertEqual(result, '冠军客户')
        
        # 测试忠诚客户
        result = self.service._classify_customer(3, 5, 5)
        self.assertEqual(result, '忠诚客户')
        
        # 测试潜力客户
        result = self.service._classify_customer(5, 3, 3)
        self.assertEqual(result, '潜力客户')
        
        # 测试新客户
        result = self.service._classify_customer(5, 1, 2)
        self.assertEqual(result, '新客户')
        
        # 测试风险客户
        result = self.service._classify_customer(1, 3, 3)
        self.assertEqual(result, '风险客户')
        
        # 测试需要关注的客户
        result = self.service._classify_customer(2, 3, 5)
        self.assertEqual(result, '需要关注')
        
        # 测试一般客户
        result = self.service._classify_customer(3, 3, 3)
        self.assertEqual(result, '一般客户')
    
    def test_calculate_product_turnover_analysis(self):
        """测试产品周转分析计算"""
        inventory_data = [
            {'product_name': '产品A', 'current_stock': 100, 'stock_value': 10000, 'unit_cost': 100},
            {'product_name': '产品B', 'current_stock': 50, 'stock_value': 5000, 'unit_cost': 100}
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
                'last_sale_date': '2024-06-01'  # 很久以前
            }
        }
        
        result = self.service._calculate_product_turnover_analysis(
            inventory_data, product_sales_data, 365, {'fast': 4.0, 'slow': 1.0}
        )
        
        # 验证结果
        self.assertEqual(len(result), 2)
        
        # 产品A应该是快速周转
        product_a = next(item for item in result if item['product_name'] == '产品A')
        self.assertEqual(product_a['category'], 'fast_moving')
        self.assertGreater(product_a['turnover_rate'], 1.0)
        
        # 产品B应该是呆滞库存（很久未销售）
        product_b = next(item for item in result if item['product_name'] == '产品B')
        self.assertEqual(product_b['category'], 'dead_stock')
        self.assertGreater(product_b['days_since_last_sale'], 180)
    
    def test_generate_inventory_warnings(self):
        """测试库存预警信息生成"""
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
                'stock_value': 8000,
                'current_stock': 0
            }
        ]
        
        result = self.service._generate_inventory_warnings(
            turnover_analysis, {'fast': 4.0, 'slow': 1.0}
        )
        
        # 验证预警数量
        self.assertGreaterEqual(len(result), 2)  # 至少有呆滞库存和缺货预警
        
        # 验证呆滞库存预警
        dead_stock_warning = next((w for w in result if w['type'] == 'dead_stock'), None)
        self.assertIsNotNone(dead_stock_warning)
        self.assertEqual(dead_stock_warning['level'], 'high')
        self.assertEqual(dead_stock_warning['count'], 1)
        self.assertEqual(dead_stock_warning['value'], 15000)
        
        # 验证缺货预警
        out_of_stock_warning = next((w for w in result if w['type'] == 'out_of_stock'), None)
        self.assertIsNotNone(out_of_stock_warning)
        self.assertEqual(out_of_stock_warning['count'], 1)
    
    def test_create_empty_responses(self):
        """测试空响应创建方法"""
        # 测试空趋势响应
        result = self.service._create_empty_trend_response('month')
        self.assertTrue(result['success'])
        self.assertEqual(result['dimension'], 'month')
        self.assertEqual(len(result['data']), 0)
        
        # 测试空客户分析响应
        result = self.service._create_empty_customer_analysis_response('rfm')
        self.assertTrue(result['success'])
        self.assertEqual(result['analysis_type'], 'rfm')
        self.assertEqual(len(result['data']), 0)
        
        # 测试空库存分析响应
        result = self.service._create_empty_inventory_analysis_response()
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['overall_turnover_rate'], 0)
        self.assertEqual(len(result['data']['turnover_analysis']), 0)


class TestDataAnalysisServiceIntegration(unittest.TestCase):
    """数据分析服务集成测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_integration")
        self.service = DataAnalysisService(self.logger)
    
    @patch('scripts.data_analysis_service.cache_report_data')
    def test_caching_integration(self, mock_cache):
        """测试缓存集成"""
        # 设置模拟缓存返回值
        mock_cache.return_value = {
            'success': True,
            'data': {'total_sales': 100000},
            'cached': True
        }
        
        params = {'date_range': {'start_date': '2025-01-01', 'end_date': '2025-01-31'}}
        result = self.service.get_dashboard_summary(params)
        
        # 验证缓存被调用
        mock_cache.assert_called_once()
        self.assertTrue(result.get('cached'))
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效方法名
        result = self.service.handle_method_call('invalid_method', {})
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error', {}).get('code'), 'METHOD_NOT_FOUND')
        
        # 测试无效参数
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'invalid_dimension'
        })
        self.assertFalse(result.get('success'))
        self.assertIn('不支持的分析维度', result.get('error', {}).get('message', ''))


if __name__ == '__main__':
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加单元测试
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataAnalysisService))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataAnalysisServiceIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print(f"\n✅ 所有测试通过！运行了 {result.testsRun} 个测试")
    else:
        print(f"\n❌ 测试失败！{len(result.failures)} 个失败，{len(result.errors)} 个错误")
        sys.exit(1)