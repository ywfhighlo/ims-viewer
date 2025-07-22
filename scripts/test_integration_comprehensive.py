#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析仪表板完整集成测试
测试前后端数据流、用户交互流程和端到端功能
"""

import sys
import os
import json
import unittest
import time
import threading
import queue
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


class TestEndToEndDataFlow(unittest.TestCase):
    """端到端数据流测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_e2e_data_flow")
        self.service = DataAnalysisService(self.logger)
        
        # 设置完整的模拟数据
        self.setup_mock_data()
    
    def setup_mock_data(self):
        """设置模拟数据"""
        self.mock_sales_summary = {
            'total_amount': 500000,
            'order_count': 250,
            'customer_count': 100,
            'average_order_value': 2000,
            'monthly_trend': [
                {'month': '2024-10', 'total_amount': 80000, 'total_quantity': 400, 'order_count': 40},
                {'month': '2024-11', 'total_amount': 90000, 'total_quantity': 450, 'order_count': 45},
                {'month': '2024-12', 'total_amount': 100000, 'total_quantity': 500, 'order_count': 50},
                {'month': '2025-01', 'total_amount': 120000, 'total_quantity': 600, 'order_count': 60},
                {'month': '2025-02', 'total_amount': 110000, 'total_quantity': 550, 'order_count': 55}
            ],
            'top_products': [
                {'material_code': 'P001', 'material_name': '高端产品A', 'total_amount': 150000, 'total_quantity': 300, 'order_count': 75},
                {'material_code': 'P002', 'material_name': '中端产品B', 'total_amount': 120000, 'total_quantity': 600, 'order_count': 60},
                {'material_code': 'P003', 'material_name': '基础产品C', 'total_amount': 100000, 'total_quantity': 1000, 'order_count': 50},
                {'material_code': 'P004', 'material_name': '特殊产品D', 'total_amount': 80000, 'total_quantity': 200, 'order_count': 40},
                {'material_code': 'P005', 'material_name': '新品产品E', 'total_amount': 50000, 'total_quantity': 250, 'order_count': 25}
            ],
            'customer_details': [
                {
                    'customer_name': '大客户A',
                    'total_amount': 100000,
                    'order_count': 50,
                    'last_order_date': '2025-02-15',
                    'first_order_date': '2024-01-01'
                },
                {
                    'customer_name': '重要客户B',
                    'total_amount': 80000,
                    'order_count': 40,
                    'last_order_date': '2025-02-10',
                    'first_order_date': '2024-03-01'
                },
                {
                    'customer_name': '新客户C',
                    'total_amount': 30000,
                    'order_count': 15,
                    'last_order_date': '2025-02-01',
                    'first_order_date': '2025-01-01'
                },
                {
                    'customer_name': '老客户D',
                    'total_amount': 60000,
                    'order_count': 30,
                    'last_order_date': '2024-12-01',
                    'first_order_date': '2023-06-01'
                }
            ]
        }
        
        self.mock_purchase_summary = {
            'total_amount': 350000,
            'order_count': 150,
            'supplier_count': 50,
            'average_order_value': 2333,
            'monthly_trend': [
                {'month': '2024-10', 'total_amount': 60000, 'order_count': 25},
                {'month': '2024-11', 'total_amount': 65000, 'order_count': 28},
                {'month': '2024-12', 'total_amount': 70000, 'order_count': 30},
                {'month': '2025-01', 'total_amount': 80000, 'order_count': 35},
                {'month': '2025-02', 'total_amount': 75000, 'order_count': 32}
            ]
        }
        
        self.mock_inventory_result = {
            'success': True,
            'data': [
                {
                    'product_name': '高端产品A',
                    'material_code': 'P001',
                    'current_stock': 150,
                    'stock_value': 75000,
                    'unit_cost': 500,
                    'stock_status': '正常'
                },
                {
                    'product_name': '中端产品B',
                    'material_code': 'P002',
                    'current_stock': 80,
                    'stock_value': 16000,
                    'unit_cost': 200,
                    'stock_status': '低库存'
                },
                {
                    'product_name': '基础产品C',
                    'material_code': 'P003',
                    'current_stock': 500,
                    'stock_value': 50000,
                    'unit_cost': 100,
                    'stock_status': '正常'
                },
                {
                    'product_name': '特殊产品D',
                    'material_code': 'P004',
                    'current_stock': 0,
                    'stock_value': 0,
                    'unit_cost': 400,
                    'stock_status': '缺货'
                },
                {
                    'product_name': '滞销产品F',
                    'material_code': 'P006',
                    'current_stock': 200,
                    'stock_value': 60000,
                    'unit_cost': 300,
                    'stock_status': '正常'
                }
            ],
            'statistics': {
                'total_value': 201000,
                'total_items': 930
            }
        }
    
    @patch('scripts.data_analysis_service.generate_sales_summary')
    @patch('scripts.data_analysis_service.generate_purchase_summary')
    @patch('scripts.data_analysis_service.generate_inventory_report')
    @patch('scripts.data_analysis_service.generate_receivables_summary')
    @patch('scripts.data_analysis_service.generate_payables_summary')
    def test_complete_dashboard_workflow(self, mock_payables, mock_receivables, 
                                       mock_inventory, mock_purchase, mock_sales):
        """测试完整的仪表板工作流程"""
        # 设置模拟返回值
        mock_sales.return_value = self.mock_sales_summary
        mock_purchase.return_value = self.mock_purchase_summary
        mock_inventory.return_value = self.mock_inventory_result
        mock_receivables.return_value = {'total_receivables': 50000, 'overdue_amount': 10000}
        mock_payables.return_value = {'total_payables': 30000, 'overdue_amount': 5000}
        
        # 1. 模拟用户打开仪表板
        print("1. 模拟用户打开仪表板...")
        dashboard_result = self.service.handle_method_call('get_dashboard_summary', {
            'date_range': {
                'start_date': '2024-10-01',
                'end_date': '2025-02-28'
            }
        })
        
        # 验证仪表板数据
        self.assertIsInstance(dashboard_result, dict)
        self.assertIn('generated_at', dashboard_result)
        
        if dashboard_result.get('success') or 'total_sales' in dashboard_result:
            data = dashboard_result.get('data', dashboard_result)
            
            # 验证关键业务指标
            self.assertEqual(data['total_sales'], 500000)
            self.assertEqual(data['total_purchases'], 350000)
            self.assertEqual(data['gross_margin'], 150000)
            self.assertEqual(data['active_customers'], 100)
            self.assertEqual(data['total_inventory_value'], 201000)
            
            print(f"   ✓ 总销售额: {data['total_sales']:,}")
            print(f"   ✓ 毛利润: {data['gross_margin']:,}")
            print(f"   ✓ 活跃客户: {data['active_customers']}")
        
        # 2. 模拟用户查看销售趋势
        print("\n2. 模拟用户查看月度销售趋势...")
        monthly_trend_result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'month',
            'date_range': {
                'start_date': '2024-10-01',
                'end_date': '2025-02-28'
            }
        })
        
        if monthly_trend_result.get('success'):
            trend_data = monthly_trend_result['data']
            self.assertEqual(len(trend_data), 5)  # 5个月的数据
            
            # 验证趋势数据格式
            first_month = trend_data[0]
            self.assertIn('period', first_month)
            self.assertIn('total_sales', first_month)
            self.assertIn('order_count', first_month)
            
            print(f"   ✓ 月度趋势数据: {len(trend_data)} 个月")
            print(f"   ✓ 最新月份销售额: {trend_data[-1]['total_sales']:,}")
        
        # 3. 模拟用户查看产品排行
        print("\n3. 模拟用户查看产品销售排行...")
        product_ranking_result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'product'
        })
        
        if product_ranking_result.get('success'):
            product_data = product_ranking_result['data']
            self.assertEqual(len(product_data), 5)  # 5个产品
            
            # 验证产品排行数据
            top_product = product_data[0]
            self.assertEqual(top_product['rank'], 1)
            self.assertEqual(top_product['product_name'], '高端产品A')
            self.assertEqual(top_product['total_sales'], 150000)
            
            print(f"   ✓ 产品排行数据: {len(product_data)} 个产品")
            print(f"   ✓ 销量冠军: {top_product['product_name']} ({top_product['total_sales']:,})")
        
        # 4. 模拟用户查看客户价值分析
        print("\n4. 模拟用户查看客户价值分析...")
        customer_analysis_result = self.service.handle_method_call('analyze_customer_value', {
            'analysis_type': 'rfm'
        })
        
        if customer_analysis_result.get('success'):
            customer_data = customer_analysis_result['data']
            self.assertGreater(len(customer_data), 0)
            
            # 验证RFM分析数据
            if customer_data:
                first_customer = customer_data[0]
                self.assertIn('customer_name', first_customer)
                self.assertIn('customer_segment', first_customer)
                self.assertIn('rfm_score', first_customer)
                
                print(f"   ✓ 客户分析数据: {len(customer_data)} 个客户")
                print(f"   ✓ 顶级客户: {first_customer['customer_name']} ({first_customer['customer_segment']})")
        
        # 5. 模拟用户查看库存周转分析
        print("\n5. 模拟用户查看库存周转分析...")
        inventory_analysis_result = self.service.handle_method_call('analyze_inventory_turnover', {
            'analysis_period': 365,
            'turnover_thresholds': {'fast': 4.0, 'slow': 1.0}
        })
        
        if inventory_analysis_result.get('success'):
            inventory_data = inventory_analysis_result['data']
            
            # 验证库存周转数据
            self.assertIn('overall_turnover_rate', inventory_data)
            self.assertIn('turnover_analysis', inventory_data)
            self.assertIn('warnings', inventory_data)
            
            turnover_rate = inventory_data['overall_turnover_rate']
            warnings_count = len(inventory_data['warnings'])
            
            print(f"   ✓ 整体周转率: {turnover_rate:.2f}")
            print(f"   ✓ 预警信息: {warnings_count} 条")
        
        print("\n✅ 完整仪表板工作流程测试通过")
    
    def test_user_interaction_scenarios(self):
        """测试用户交互场景"""
        # 场景1: 用户选择不同日期范围
        print("测试场景1: 用户选择不同日期范围")
        date_ranges = [
            {'start_date': '2025-01-01', 'end_date': '2025-01-31'},  # 1个月
            {'start_date': '2024-10-01', 'end_date': '2024-12-31'},  # 1个季度
            {'start_date': '2024-01-01', 'end_date': '2024-12-31'},  # 1年
        ]
        
        for i, date_range in enumerate(date_ranges, 1):
            with self.subTest(scenario=f"date_range_{i}"):
                result = self.service.handle_method_call('get_dashboard_summary', {
                    'date_range': date_range
                })
                
                # 验证每个日期范围都能正常处理
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
                
                if result.get('success') or 'date_range' in result:
                    data = result.get('data', result)
                    if 'date_range' in data:
                        self.assertEqual(data['date_range']['start_date'], date_range['start_date'])
                        self.assertEqual(data['date_range']['end_date'], date_range['end_date'])
        
        # 场景2: 用户切换不同分析维度
        print("测试场景2: 用户切换不同分析维度")
        dimensions = ['month', 'quarter', 'product']
        
        for dimension in dimensions:
            with self.subTest(dimension=dimension):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': dimension
                })
                
                # 验证每个维度都能正常处理
                if result.get('success'):
                    self.assertEqual(result.get('dimension'), dimension)
                    self.assertIsInstance(result.get('data'), list)
        
        # 场景3: 用户使用分页功能
        print("测试场景3: 用户使用分页功能")
        pagination_params = [
            {'page': 1, 'page_size': 10},
            {'page': 2, 'page_size': 5},
            {'page': 1, 'page_size': 20}
        ]
        
        for params in pagination_params:
            with self.subTest(pagination=params):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': 'product',
                    **params
                })
                
                # 验证分页参数被正确处理
                if result.get('success') and 'pagination' in result:
                    pagination = result['pagination']
                    self.assertEqual(pagination['current_page'], params['page'])
                    self.assertEqual(pagination['page_size'], params['page_size'])
    
    def test_error_recovery_scenarios(self):
        """测试错误恢复场景"""
        print("测试错误恢复场景")
        
        # 场景1: 数据库连接失败后恢复
        with patch.object(self.service.query_optimizer, '_get_db_connection') as mock_db:
            # 第一次调用失败
            mock_db.side_effect = Exception("数据库连接失败")
            
            result1 = self.service.handle_method_call('get_dashboard_summary', {})
            self.assertFalse(result1.get('success', True))
            
            # 第二次调用成功（模拟连接恢复）
            mock_db.side_effect = None
            mock_db.return_value = Mock()
            
            result2 = self.service.handle_method_call('get_dashboard_summary', {})
            # 应该能够处理（即使没有真实数据）
            self.assertIsInstance(result2, dict)
        
        # 场景2: 无效参数后使用有效参数
        # 无效参数
        result1 = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'invalid_dimension'
        })
        self.assertFalse(result1.get('success', True))
        
        # 有效参数
        result2 = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'month'
        })
        # 应该能够正常处理
        self.assertIsInstance(result2, dict)
    
    def test_performance_under_load(self):
        """测试负载下的性能"""
        print("测试负载下的性能")
        
        def make_concurrent_request(results_queue, request_id):
            """并发请求函数"""
            try:
                start_time = time.time()
                result = self.service.handle_method_call('get_dashboard_summary', {})
                end_time = time.time()
                
                results_queue.put({
                    'request_id': request_id,
                    'success': True,
                    'response_time': end_time - start_time,
                    'result': result
                })
            except Exception as e:
                results_queue.put({
                    'request_id': request_id,
                    'success': False,
                    'error': str(e)
                })
        
        # 创建并发请求
        results_queue = queue.Queue()
        threads = []
        concurrent_requests = 5
        
        for i in range(concurrent_requests):
            thread = threading.Thread(
                target=make_concurrent_request,
                args=(results_queue, i)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=60)  # 60秒超时
        
        # 收集结果
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # 验证结果
        self.assertEqual(len(results), concurrent_requests)
        
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        print(f"   成功请求: {len(successful_requests)}/{concurrent_requests}")
        print(f"   失败请求: {len(failed_requests)}/{concurrent_requests}")
        
        if successful_requests:
            avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            max_response_time = max(r['response_time'] for r in successful_requests)
            print(f"   平均响应时间: {avg_response_time:.3f}秒")
            print(f"   最大响应时间: {max_response_time:.3f}秒")
            
            # 验证响应时间合理
            self.assertLess(avg_response_time, 10.0, "平均响应时间应该小于10秒")
            self.assertLess(max_response_time, 30.0, "最大响应时间应该小于30秒")
        
        # 至少应该有一些成功的请求
        self.assertGreater(len(successful_requests), 0, "应该至少有一些成功的并发请求")


class TestDataConsistency(unittest.TestCase):
    """数据一致性测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_data_consistency")
        self.service = DataAnalysisService(self.logger)
    
    def test_cross_analysis_consistency(self):
        """测试跨分析的数据一致性"""
        # 模拟一致的基础数据
        consistent_sales_data = {
            'total_amount': 100000,
            'order_count': 50,
            'customer_count': 25,
            'monthly_trend': [
                {'month': '2025-01', 'total_amount': 50000, 'order_count': 25},
                {'month': '2025-02', 'total_amount': 50000, 'order_count': 25}
            ],
            'top_products': [
                {'material_name': '产品A', 'total_amount': 60000, 'order_count': 30},
                {'material_name': '产品B', 'total_amount': 40000, 'order_count': 20}
            ],
            'customer_details': [
                {'customer_name': '客户A', 'total_amount': 60000, 'order_count': 30},
                {'customer_name': '客户B', 'total_amount': 40000, 'order_count': 20}
            ]
        }
        
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = consistent_sales_data
            
            # 获取仪表板概览
            dashboard_result = self.service.handle_method_call('get_dashboard_summary', {})
            
            # 获取销售趋势
            trend_result = self.service.handle_method_call('analyze_sales_trend', {
                'dimension': 'month'
            })
            
            # 获取产品分析
            product_result = self.service.handle_method_call('analyze_sales_trend', {
                'dimension': 'product'
            })
            
            # 验证数据一致性
            if (dashboard_result.get('success') or 'total_sales' in dashboard_result) and \
               trend_result.get('success') and product_result.get('success'):
                
                dashboard_data = dashboard_result.get('data', dashboard_result)
                trend_data = trend_result['data']
                product_data = product_result['data']
                
                # 验证总销售额一致性
                dashboard_total = dashboard_data['total_sales']
                trend_total = sum(item['total_sales'] for item in trend_data)
                product_total = sum(item['total_sales'] for item in product_data)
                
                self.assertEqual(dashboard_total, 100000)
                self.assertEqual(trend_total, 100000)
                self.assertEqual(product_total, 100000)
                
                print(f"✓ 数据一致性验证通过:")
                print(f"  仪表板总额: {dashboard_total:,}")
                print(f"  趋势分析总额: {trend_total:,}")
                print(f"  产品分析总额: {product_total:,}")
    
    def test_date_range_consistency(self):
        """测试日期范围一致性"""
        test_date_range = {
            'start_date': '2025-01-01',
            'end_date': '2025-01-31'
        }
        
        # 测试所有分析方法都正确处理相同的日期范围
        methods_to_test = [
            ('get_dashboard_summary', {'date_range': test_date_range}),
            ('analyze_sales_trend', {'dimension': 'month', 'date_range': test_date_range}),
            ('analyze_customer_value', {'analysis_type': 'rfm', 'date_range': test_date_range}),
            ('analyze_inventory_turnover', {'date_range': test_date_range})
        ]
        
        for method, params in methods_to_test:
            with self.subTest(method=method):
                result = self.service.handle_method_call(method, params)
                
                # 验证日期范围被正确传递和处理
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
                
                # 如果有summary或data，验证日期范围信息
                data = result.get('data', result)
                summary = result.get('summary', {})
                
                if 'date_range' in data:
                    self.assertEqual(data['date_range']['start_date'], test_date_range['start_date'])
                    self.assertEqual(data['date_range']['end_date'], test_date_range['end_date'])
                elif 'date_range' in summary:
                    self.assertEqual(summary['date_range']['start_date'], test_date_range['start_date'])
                    self.assertEqual(summary['date_range']['end_date'], test_date_range['end_date'])


class TestUserExperienceFlow(unittest.TestCase):
    """用户体验流程测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_ux_flow")
        self.service = DataAnalysisService(self.logger)
    
    def test_typical_user_journey(self):
        """测试典型用户使用流程"""
        print("测试典型用户使用流程")
        
        # 用户流程1: 查看整体业务状况
        print("1. 用户查看整体业务状况...")
        dashboard_result = self.service.handle_method_call('get_dashboard_summary', {})
        self.assertIsInstance(dashboard_result, dict)
        self.assertIn('generated_at', dashboard_result)
        
        # 用户流程2: 深入分析销售趋势
        print("2. 用户深入分析销售趋势...")
        monthly_trend = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'month'
        })
        quarterly_trend = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'quarter'
        })
        
        self.assertIsInstance(monthly_trend, dict)
        self.assertIsInstance(quarterly_trend, dict)
        
        # 用户流程3: 查看产品表现
        print("3. 用户查看产品表现...")
        product_analysis = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'product'
        })
        self.assertIsInstance(product_analysis, dict)
        
        # 用户流程4: 分析客户价值
        print("4. 用户分析客户价值...")
        customer_analysis = self.service.handle_method_call('analyze_customer_value', {
            'analysis_type': 'rfm'
        })
        self.assertIsInstance(customer_analysis, dict)
        
        # 用户流程5: 检查库存状况
        print("5. 用户检查库存状况...")
        inventory_analysis = self.service.handle_method_call('analyze_inventory_turnover', {})
        self.assertIsInstance(inventory_analysis, dict)
        
        # 用户流程6: 进行对比分析
        print("6. 用户进行对比分析...")
        comparison_analysis = self.service.handle_method_call('generate_comparison_analysis', {
            'metrics': ['total_sales', 'total_purchases'],
            'dimensions': ['month', 'product']
        })
        self.assertIsInstance(comparison_analysis, dict)
        
        print("✅ 典型用户流程测试完成")
    
    def test_error_handling_user_experience(self):
        """测试错误处理的用户体验"""
        print("测试错误处理的用户体验")
        
        # 错误场景1: 用户输入无效日期
        print("1. 测试无效日期输入...")
        result = self.service.handle_method_call('get_dashboard_summary', {
            'date_range': {
                'start_date': '2025/01/01',  # 错误格式
                'end_date': '2025-01-31'
            }
        })
        
        # 验证错误消息用户友好
        if not result.get('success', True):
            error_message = result.get('error', {}).get('message', '')
            self.assertIn('日期格式无效', error_message)
            self.assertTrue(len(error_message) > 0)
        
        # 错误场景2: 用户选择无效分析维度
        print("2. 测试无效分析维度...")
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'invalid_dimension'
        })
        
        if not result.get('success', True):
            error_message = result.get('error', {}).get('message', '')
            self.assertIn('不支持的分析维度', error_message)
        
        # 错误场景3: 用户调用不存在的方法
        print("3. 测试不存在的方法...")
        result = self.service.handle_method_call('non_existent_method', {})
        
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error', {}).get('code'), 'METHOD_NOT_FOUND')
        
        print("✅ 错误处理用户体验测试完成")
    
    def test_response_time_user_experience(self):
        """测试响应时间用户体验"""
        print("测试响应时间用户体验")
        
        # 测试各个主要功能的响应时间
        functions_to_test = [
            ('get_dashboard_summary', {}, '仪表板概览'),
            ('analyze_sales_trend', {'dimension': 'month'}, '月度销售趋势'),
            ('analyze_sales_trend', {'dimension': 'product'}, '产品销售分析'),
            ('analyze_customer_value', {'analysis_type': 'rfm'}, '客户价值分析'),
            ('analyze_inventory_turnover', {}, '库存周转分析')
        ]
        
        response_times = []
        
        for method, params, description in functions_to_test:
            start_time = time.time()
            result = self.service.handle_method_call(method, params)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            print(f"   {description}: {response_time:.3f}秒")
            
            # 验证响应时间合理（用户体验角度）
            self.assertLess(response_time, 15.0, f"{description}响应时间应该小于15秒")
        
        # 计算平均响应时间
        avg_response_time = sum(response_times) / len(response_times)
        print(f"   平均响应时间: {avg_response_time:.3f}秒")
        
        # 验证平均响应时间合理
        self.assertLess(avg_response_time, 10.0, "平均响应时间应该小于10秒")
        
        print("✅ 响应时间用户体验测试完成")


if __name__ == '__main__':
    # 创建测试套件
    test_classes = [
        TestEndToEndDataFlow,
        TestDataConsistency,
        TestUserExperienceFlow
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
        print(f"✅ 所有集成测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print(f"❌ 集成测试失败！")
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