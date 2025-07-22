#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表渲染和用户交互功能测试
测试前端图表渲染逻辑和用户交互功能
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger


class TestChartDataFormat(unittest.TestCase):
    """图表数据格式测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_chart_rendering")
        self.service = DataAnalysisService(self.logger)
    
    def test_sales_trend_chart_data_format(self):
        """测试销售趋势图表数据格式"""
        # 测试月度趋势数据格式
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'month'
        })
        
        if result.get('success') and result.get('data'):
            chart_data = result['data']
            
            # 验证数据是列表格式
            self.assertIsInstance(chart_data, list)
            
            if chart_data:
                # 验证第一个数据项的结构
                first_item = chart_data[0]
                
                # Chart.js 需要的字段
                required_fields = {
                    'period': str,  # X轴标签
                    'total_sales': (int, float),  # Y轴数值
                    'order_count': (int, float)  # 可选的额外数据
                }
                
                for field, expected_type in required_fields.items():
                    self.assertIn(field, first_item, f"缺少图表必需字段: {field}")
                    self.assertIsInstance(first_item[field], expected_type, 
                                        f"字段 {field} 类型错误，期望 {expected_type}")
                
                # 验证数据排序（月度数据应该按时间排序）
                if len(chart_data) > 1:
                    periods = [item.get('period', '') for item in chart_data]
                    self.assertEqual(periods, sorted(periods), "月度数据应该按时间排序")
    
    def test_product_analysis_chart_data_format(self):
        """测试产品分析图表数据格式"""
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'product'
        })
        
        if result.get('success') and result.get('data'):
            chart_data = result['data']
            
            self.assertIsInstance(chart_data, list)
            
            if chart_data:
                first_item = chart_data[0]
                
                # 产品排行榜需要的字段
                required_fields = {
                    'product_name': str,
                    'total_sales': (int, float),
                    'rank': int
                }
                
                for field, expected_type in required_fields.items():
                    self.assertIn(field, first_item, f"产品分析缺少字段: {field}")
                    self.assertIsInstance(first_item[field], expected_type)
                
                # 验证排名顺序
                if len(chart_data) > 1:
                    ranks = [item.get('rank', 0) for item in chart_data]
                    self.assertEqual(ranks, sorted(ranks), "产品排行应该按排名排序")
    
    def test_customer_value_pie_chart_data_format(self):
        """测试客户价值饼图数据格式"""
        result = self.service.handle_method_call('analyze_customer_value', {
            'analysis_type': 'segmentation'
        })
        
        if result.get('success') and result.get('data'):
            # 客户价值分析可能返回不同格式的数据
            data = result['data']
            
            if isinstance(data, dict) and 'segment_distribution' in data:
                # 分组数据格式
                segment_data = data['segment_distribution']
                self.assertIsInstance(segment_data, dict)
                
                # 验证每个分组的数据
                for segment_name, count in segment_data.items():
                    self.assertIsInstance(segment_name, str)
                    self.assertIsInstance(count, int)
                    self.assertGreaterEqual(count, 0)
            
            elif isinstance(data, list):
                # 列表格式的客户数据
                if data:
                    first_customer = data[0]
                    
                    # RFM分析需要的字段
                    expected_fields = {
                        'customer_name': str,
                        'customer_segment': str,
                        'customer_value': (int, float)
                    }
                    
                    for field, expected_type in expected_fields.items():
                        if field in first_customer:
                            self.assertIsInstance(first_customer[field], expected_type)
    
    def test_inventory_turnover_chart_data_format(self):
        """测试库存周转图表数据格式"""
        result = self.service.handle_method_call('analyze_inventory_turnover', {})
        
        if result.get('success') and result.get('data'):
            data = result['data']
            
            # 验证整体指标
            overall_metrics = [
                'overall_turnover_rate',
                'fast_moving_items',
                'slow_moving_items',
                'dead_stock_count'
            ]
            
            for metric in overall_metrics:
                if metric in data:
                    self.assertIsInstance(data[metric], (int, float))
            
            # 验证详细分析数据
            if 'turnover_analysis' in data:
                turnover_data = data['turnover_analysis']
                self.assertIsInstance(turnover_data, list)
                
                if turnover_data:
                    first_item = turnover_data[0]
                    
                    # 库存周转分析需要的字段
                    expected_fields = {
                        'product_name': str,
                        'turnover_rate': (int, float),
                        'category': str,
                        'stock_value': (int, float)
                    }
                    
                    for field, expected_type in expected_fields.items():
                        if field in first_item:
                            self.assertIsInstance(first_item[field], expected_type)


class TestDataVisualizationLogic(unittest.TestCase):
    """数据可视化逻辑测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_visualization")
        self.service = DataAnalysisService(self.logger)
    
    def test_color_coding_logic(self):
        """测试颜色编码逻辑"""
        # 获取库存周转分析数据
        result = self.service.handle_method_call('analyze_inventory_turnover', {})
        
        if result.get('success') and result.get('data'):
            turnover_data = result['data'].get('turnover_analysis', [])
            
            # 验证分类逻辑
            categories = set()
            for item in turnover_data:
                category = item.get('category')
                if category:
                    categories.add(category)
            
            # 验证分类的有效性
            valid_categories = {'fast_moving', 'normal', 'slow_moving', 'dead_stock'}
            for category in categories:
                self.assertIn(category, valid_categories, f"无效的库存分类: {category}")
    
    def test_chart_data_aggregation(self):
        """测试图表数据聚合逻辑"""
        # 测试季度数据聚合
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'quarter'
        })
        
        if result.get('success') and result.get('data'):
            quarterly_data = result['data']
            
            if quarterly_data:
                # 验证季度数据的聚合逻辑
                for quarter_item in quarterly_data:
                    # 验证季度格式
                    quarter = quarter_item.get('quarter', '')
                    if quarter:
                        self.assertRegex(quarter, r'^\d{4}-Q[1-4]$',$',$', 
                                       f"季度格式错误: {quarter}")
                    
                    # 验证聚合数据的合理性
                    total_sales = quarter_item.get('total_sales', 0)
                    order_count = quarter_item.get('order_count', 0)
                    
                    if order_count > 0:
                        avg_order_value = quarter_item.get('avg_order_value', 0)
                        expected_avg = total_sales / order_count
                        self.assertAlmostEqual(avg_order_value, expected_avg, places=2,
                                             msg="平均订单价值计算错误")
    
    def test_data_sorting_and_ranking(self):
        """测试数据排序和排名逻辑"""
        # 测试产品排行榜
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'product'
        })
        
        if result.get('success') and result.get('data'):
            product_data = result['data']
            
            if len(product_data) > 1:
                # 验证排序逻辑（应该按销售额降序排列）
                sales_amounts = [item.get('total_sales', 0) for item in product_data]
                self.assertEqual(sales_amounts, sorted(sales_amounts, reverse=True),
                               "产品排行榜应该按销售额降序排列")
                
                # 验证排名连续性
                ranks = [item.get('rank', 0) for item in product_data]
                expected_ranks = list(range(1, len(product_data) + 1))
                self.assertEqual(ranks, expected_ranks, "产品排名应该连续")
    
    def test_percentage_calculations(self):
        """测试百分比计算逻辑"""
        # 获取仪表板概览数据
        result = self.service.handle_method_call('get_dashboard_summary', {})
        
        if result.get('success') or 'gross_margin_rate' in result:
            data = result.get('data', result)
            
            # 验证毛利率计算
            total_sales = data.get('total_sales', 0)
            total_purchases = data.get('total_purchases', 0)
            gross_margin = data.get('gross_margin', 0)
            gross_margin_rate = data.get('gross_margin_rate', 0)
            
            if total_sales > 0:
                expected_margin = total_sales - total_purchases
                expected_rate = (expected_margin / total_sales) * 100
                
                self.assertAlmostEqual(gross_margin, expected_margin, places=2,
                                     msg="毛利润计算错误")
                self.assertAlmostEqual(gross_margin_rate, expected_rate, places=2,
                                     msg="毛利率计算错误")


class TestUserInteractionSimulation(unittest.TestCase):
    """用户交互模拟测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_user_interaction")
        self.service = DataAnalysisService(self.logger)
    
    def test_tab_switching_simulation(self):
        """模拟标签页切换"""
        # 模拟用户点击不同的分析标签
        tab_requests = [
            {'dimension': 'month'},
            {'dimension': 'quarter'},
            {'dimension': 'product'}
        ]
        
        for tab_request in tab_requests:
            with self.subTest(dimension=tab_request['dimension']):
                result = self.service.handle_method_call('analyze_sales_trend', tab_request)
                
                # 验证每个标签页都能正确响应
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
                
                if result.get('success'):
                    self.assertEqual(result.get('dimension'), tab_request['dimension'])
    
    def test_date_range_interaction(self):
        """模拟日期范围选择交互"""
        # 模拟用户选择不同的日期范围
        date_ranges = [
            # 最近30天
            {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31'
            },
            # 最近3个月
            {
                'start_date': '2024-11-01',
                'end_date': '2025-01-31'
            },
            # 自定义范围
            {
                'start_date': '2024-06-01',
                'end_date': '2024-12-31'
            }
        ]
        
        for date_range in date_ranges:
            with self.subTest(date_range=date_range):
                result = self.service.handle_method_call('get_dashboard_summary', {
                    'date_range': date_range
                })
                
                # 验证日期范围被正确处理
                self.assertIsInstance(result, dict)
                
                # 检查返回的日期范围信息
                if result.get('success') or 'date_range' in result:
                    returned_range = result.get('date_range') or result.get('summary', {}).get('date_range')
                    if returned_range:
                        self.assertEqual(returned_range.get('start_date'), date_range['start_date'])
                        self.assertEqual(returned_range.get('end_date'), date_range['end_date'])
    
    def test_pagination_interaction(self):
        """模拟分页交互"""
        # 模拟用户翻页操作
        page_requests = [
            {'page': 1, 'page_size': 10},
            {'page': 2, 'page_size': 10},
            {'page': 1, 'page_size': 20}
        ]
        
        for page_request in page_requests:
            with self.subTest(page=page_request['page'], page_size=page_request['page_size']):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': 'product',
                    **page_request
                })
                
                # 验证分页响应
                if result.get('success') and 'pagination' in result:
                    pagination = result['pagination']
                    
                    self.assertEqual(pagination['current_page'], page_request['page'])
                    self.assertEqual(pagination['page_size'], page_request['page_size'])
                    self.assertGreaterEqual(pagination['total_pages'], 1)
    
    def test_refresh_data_interaction(self):
        """模拟数据刷新交互"""
        # 模拟用户点击刷新按钮
        refresh_requests = [
            'get_dashboard_summary',
            'analyze_sales_trend',
            'analyze_customer_value',
            'analyze_inventory_turnover'
        ]
        
        for method in refresh_requests:
            with self.subTest(method=method):
                # 第一次请求
                result1 = self.service.handle_method_call(method, {})
                
                # 短暂延迟后的第二次请求（模拟刷新）
                import time
                time.sleep(0.1)
                result2 = self.service.handle_method_call(method, {})
                
                # 验证两次请求都成功
                self.assertIsInstance(result1, dict)
                self.assertIsInstance(result2, dict)
                
                # 验证生成时间不同（表示重新生成了数据）
                time1 = result1.get('generated_at')
                time2 = result2.get('generated_at')
                
                if time1 and time2:
                    self.assertNotEqual(time1, time2, "刷新后应该生成新的时间戳")


class TestErrorHandlingInUI(unittest.TestCase):
    """UI错误处理测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_ui_error_handling")
        self.service = DataAnalysisService(self.logger)
    
    def test_user_friendly_error_messages(self):
        """测试用户友好的错误消息"""
        error_scenarios = [
            {
                'method': 'invalid_method',
                'params': {},
                'expected_user_message_pattern': '方法'
            },
            {
                'method': 'analyze_sales_trend',
                'params': {'dimension': 'invalid_dimension'},
                'expected_user_message_pattern': '维度'
            },
            {
                'method': 'get_dashboard_summary',
                'params': {
                    'date_range': {
                        'start_date': 'invalid_date',
                        'end_date': '2025-01-31'
                    }
                },
                'expected_user_message_pattern': '日期'
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(method=scenario['method']):
                result = self.service.handle_method_call(scenario['method'], scenario['params'])
                
                # 验证错误响应包含用户友好的消息
                if not result.get('success', True):
                    error_message = result.get('error', {}).get('message', '')
                    self.assertIsInstance(error_message, str)
                    self.assertGreater(len(error_message), 0, "错误消息不能为空")
                    
                    # 验证消息包含预期的关键词
                    pattern = scenario['expected_user_message_pattern']
                    self.assertIn(pattern, error_message, f"错误消息应包含关键词: {pattern}")
    
    def test_loading_state_simulation(self):
        """模拟加载状态测试"""
        # 这个测试主要验证方法调用的响应时间合理性
        import time
        
        methods_to_test = [
            'get_dashboard_summary',
            'analyze_sales_trend',
            'analyze_customer_value'
        ]
        
        for method in methods_to_test:
            with self.subTest(method=method):
                start_time = time.time()
                result = self.service.handle_method_call(method, {})
                end_time = time.time()
                
                response_time = end_time - start_time
                
                # 验证响应时间合理（不超过30秒）
                self.assertLess(response_time, 30, f"方法 {method} 响应时间过长: {response_time:.2f}秒")
                
                # 验证有响应
                self.assertIsInstance(result, dict)


if __name__ == '__main__':
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加图表渲染测试
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestChartDataFormat))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestDataVisualizationLogic))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUserInteractionSimulation))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestErrorHandlingInUI))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print(f"\n✅ 所有图表渲染测试通过！运行了 {result.testsRun} 个测试")
    else:
        print(f"\n❌ 图表渲染测试失败！{len(result.failures)} 个失败，{len(result.errors)} 个错误")
        for failure in result.failures:
            print(f"失败: {failure[0]}")
        for error in result.errors:
            print(f"错误: {error[0]}")
        sys.exit(1)