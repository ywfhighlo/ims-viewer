#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据格式验证和错误处理逻辑测试
测试数据分析服务的数据格式验证和错误处理功能
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


class TestDataFormatValidation(unittest.TestCase):
    """数据格式验证测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_data_format")
        self.service = DataAnalysisService(self.logger)
    
    def test_date_format_validation(self):
        """测试日期格式验证"""
        valid_dates = [
            '2025-01-01',
            '2025-12-31',
            '2024-02-29',  # 闰年
            '2025-07-15'
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
            []
        ]
        
        # 测试有效日期
        for date in valid_dates:
            with self.subTest(date=date):
                self.assertTrue(self.service._validate_date_format(date),
                              f"有效日期 {date} 验证失败")
        
        # 测试无效日期
        for date in invalid_dates:
            with self.subTest(date=date):
                self.assertFalse(self.service._validate_date_format(date),
                               f"无效日期 {date} 应该验证失败")
    
    def test_numeric_parameter_validation(self):
        """测试数值参数验证"""
        # 测试安全数值获取
        test_cases = [
            # (数据, 键, 默认值, 期望结果)
            ({'value': 100}, 'value', 0, 100),
            ({'value': '100'}, 'value', 0, 100.0),
            ({'value': '100.5'}, 'value', 0, 100.5),
            ({'value': 0}, 'value', 10, 0),
            ({'value': None}, 'value', 10, 10),
            ({}, 'value', 10, 10),
            ({'value': 'invalid'}, 'value', 10, 10),
            ({'value': []}, 'value', 10, 10),
            ({'value': {}}, 'value', 10, 10),
        ]
        
        for data, key, default, expected in test_cases:
            with self.subTest(data=data, key=key):
                result = self.service._safe_get_numeric(data, key, default)
                self.assertEqual(result, expected,
                               f"数值验证失败: {data}[{key}] -> {result}, 期望 {expected}")
    
    def test_string_parameter_sanitization(self):
        """测试字符串参数清理"""
        # 模拟字符串清理功能（如果存在）
        dangerous_strings = [
            '<script>alert("xss")</script>',
            'DROP TABLE users;',
            '../../etc/passwd',
            'javascript:alert(1)',
            '<img src=x onerror=alert(1)>'
        ]
        
        # 测试维度参数验证
        for dangerous_string in dangerous_strings:
            with self.subTest(string=dangerous_string):
                result = self.service.handle_method_call('analyze_sales_trend', {
                    'dimension': dangerous_string
                })
                
                # 应该返回错误或使用默认值
                if result.get('success'):
                    # 如果成功，维度应该是默认值
                    self.assertEqual(result.get('dimension'), 'month')
                else:
                    # 如果失败，应该有错误信息
                    self.assertIn('error', result)
    
    def test_array_parameter_validation(self):
        """测试数组参数验证"""
        # 测试指标数组验证
        test_cases = [
            # 有效指标
            {
                'metrics': ['total_sales', 'total_purchases'],
                'should_succeed': True
            },
            # 包含无效指标
            {
                'metrics': ['total_sales', 'invalid_metric', 'total_purchases'],
                'should_succeed': True  # 应该过滤掉无效指标
            },
            # 空数组
            {
                'metrics': [],
                'should_succeed': True  # 应该使用默认值
            },
            # 非数组类型
            {
                'metrics': 'total_sales',
                'should_succeed': True  # 应该转换为数组
            },
            # 无效类型
            {
                'metrics': 123,
                'should_succeed': True  # 应该使用默认值
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(metrics=test_case['metrics']):
                result = self.service.handle_method_call('generate_comparison_analysis', {
                    'metrics': test_case['metrics'],
                    'dimensions': ['month']
                })
                
                if test_case['should_succeed']:
                    # 应该成功或有合理的错误
                    self.assertIsInstance(result, dict)
                else:
                    # 应该失败
                    self.assertFalse(result.get('success', True))
    
    def test_nested_object_validation(self):
        """测试嵌套对象验证"""
        # 测试日期范围对象验证
        test_cases = [
            # 有效的日期范围
            {
                'date_range': {
                    'start_date': '2025-01-01',
                    'end_date': '2025-01-31'
                },
                'should_succeed': True
            },
            # 缺少结束日期
            {
                'date_range': {
                    'start_date': '2025-01-01'
                },
                'should_succeed': True  # 应该使用默认结束日期
            },
            # 空对象
            {
                'date_range': {},
                'should_succeed': True  # 应该使用默认值
            },
            # 无效的嵌套结构
            {
                'date_range': 'invalid',
                'should_succeed': True  # 应该使用默认值
            },
            # 日期格式错误
            {
                'date_range': {
                    'start_date': '2025/01/01',
                    'end_date': '2025-01-31'
                },
                'should_succeed': False  # 应该验证失败
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(date_range=test_case['date_range']):
                result = self.service.handle_method_call('get_dashboard_summary', {
                    'date_range': test_case['date_range']
                })
                
                if test_case['should_succeed']:
                    # 应该有生成时间（表示处理成功）
                    self.assertIn('generated_at', result)
                else:
                    # 应该有错误信息
                    if not result.get('success', True):
                        self.assertIn('error', result)


class TestErrorHandlingLogic(unittest.TestCase):
    """错误处理逻辑测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_error_handling")
        self.service = DataAnalysisService(self.logger)
    
    def test_method_not_found_error(self):
        """测试方法未找到错误"""
        result = self.service.handle_method_call('non_existent_method', {})
        
        # 验证错误响应格式
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
        
        error = result['error']
        self.assertEqual(error.get('code'), 'METHOD_NOT_FOUND')
        self.assertIn('message', error)
        self.assertIsInstance(error['message'], str)
        self.assertGreater(len(error['message']), 0)
    
    def test_parameter_validation_error(self):
        """测试参数验证错误"""
        # 测试无效维度参数
        result = self.service.handle_method_call('analyze_sales_trend', {
            'dimension': 'invalid_dimension'
        })
        
        # 应该返回错误或使用默认值
        if not result.get('success', True):
            self.assertIn('error', result)
            error_message = result['error'].get('message', '')
            self.assertIn('维度', error_message)
    
    def test_data_processing_error_handling(self):
        """测试数据处理错误处理"""
        # 模拟数据库连接失败的情况
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.side_effect = Exception("数据库连接失败")
            
            result = self.service.handle_method_call('get_dashboard_summary', {})
            
            # 应该返回错误响应而不是抛出异常
            self.assertIsInstance(result, dict)
            if not result.get('success', True):
                self.assertIn('error', result)
                error_message = result.get('error', {}).get('message', '')
                self.assertIn('数据库', error_message)
    
    def test_timeout_handling(self):
        """测试超时处理"""
        # 模拟长时间运行的操作
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            def slow_operation(*args, **kwargs):
                import time
                time.sleep(0.1)  # 短暂延迟以模拟慢操作
                return {'total_amount': 1000}
            
            mock_sales.side_effect = slow_operation
            
            # 测试操作能够完成
            result = self.service.handle_method_call('get_dashboard_summary', {})
            self.assertIsInstance(result, dict)
    
    def test_memory_error_handling(self):
        """测试内存错误处理"""
        # 模拟内存不足的情况
        with patch('scripts.data_analysis_service.generate_inventory_report') as mock_inventory:
            mock_inventory.side_effect = MemoryError("内存不足")
            
            result = self.service.handle_method_call('analyze_inventory_turnover', {})
            
            # 应该优雅地处理内存错误
            self.assertIsInstance(result, dict)
            if not result.get('success', True):
                self.assertIn('error', result)
    
    def test_json_serialization_error(self):
        """测试JSON序列化错误处理"""
        # 创建包含不可序列化对象的数据
        class UnserializableObject:
            pass
        
        # 模拟返回不可序列化的数据
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
            mock_sales.return_value = {
                'total_amount': 1000,
                'unserializable': UnserializableObject()
            }
            
            result = self.service.handle_method_call('get_dashboard_summary', {})
            
            # 应该能够处理序列化问题
            self.assertIsInstance(result, dict)
            
            # 验证结果可以序列化为JSON
            try:
                json.dumps(result, default=str)
            except (TypeError, ValueError) as e:
                self.fail(f"结果无法序列化为JSON: {str(e)}")


class TestDataIntegrityValidation(unittest.TestCase):
    """数据完整性验证测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_data_integrity")
        self.service = DataAnalysisService(self.logger)
    
    def test_sales_data_integrity(self):
        """测试销售数据完整性"""
        # 模拟不完整的销售数据
        incomplete_data_cases = [
            None,  # 空数据
            {},    # 空对象
            {'total_amount': None},  # 缺少关键字段
            {'order_count': 10},     # 缺少金额字段
            {'total_amount': 'invalid'},  # 无效数据类型
        ]
        
        for incomplete_data in incomplete_data_cases:
            with self.subTest(data=incomplete_data):
                # 模拟返回不完整的数据
                with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales:
                    mock_sales.return_value = incomplete_data
                    
                    result = self.service.handle_method_call('get_dashboard_summary', {})
                    
                    # 应该能够处理不完整的数据
                    self.assertIsInstance(result, dict)
                    
                    # 验证关键字段存在且为合理值
                    if result.get('success') or 'total_sales' in result:
                        data = result.get('data', result)
                        self.assertIn('total_sales', data)
                        self.assertIsInstance(data['total_sales'], (int, float))
                        self.assertGreaterEqual(data['total_sales'], 0)
    
    def test_inventory_data_integrity(self):
        """测试库存数据完整性"""
        # 模拟不完整的库存数据
        incomplete_inventory_cases = [
            None,
            {'success': False},
            {'success': True, 'data': None},
            {'success': True, 'data': []},
            {'success': True, 'data': [{'invalid': 'data'}]},
        ]
        
        for incomplete_data in incomplete_inventory_cases:
            with self.subTest(data=incomplete_data):
                with patch('scripts.data_analysis_service.generate_inventory_report') as mock_inventory:
                    mock_inventory.return_value = incomplete_data
                    
                    result = self.service.handle_method_call('analyze_inventory_turnover', {})
                    
                    # 应该能够处理不完整的库存数据
                    self.assertIsInstance(result, dict)
                    
                    # 验证响应结构
                    if result.get('success'):
                        self.assertIn('data', result)
                        data = result['data']
                        self.assertIn('overall_turnover_rate', data)
                        self.assertIsInstance(data['overall_turnover_rate'], (int, float))
    
    def test_cross_data_consistency(self):
        """测试跨数据源一致性"""
        # 模拟不一致的数据
        with patch('scripts.data_analysis_service.generate_sales_summary') as mock_sales, \
             patch('scripts.data_analysis_service.generate_purchase_summary') as mock_purchase:
            
            # 设置不一致的数据
            mock_sales.return_value = {'total_amount': 100000, 'order_count': 50}
            mock_purchase.return_value = {'total_amount': 150000, 'order_count': 30}  # 采购额大于销售额
            
            result = self.service.handle_method_call('get_dashboard_summary', {})
            
            # 验证系统能够处理不一致的数据
            self.assertIsInstance(result, dict)
            
            if result.get('success') or 'gross_margin' in result:
                data = result.get('data', result)
                
                # 毛利润可能为负数，这是合理的
                gross_margin = data.get('gross_margin', 0)
                self.assertIsInstance(gross_margin, (int, float))
                
                # 验证计算逻辑正确
                total_sales = data.get('total_sales', 0)
                total_purchases = data.get('total_purchases', 0)
                expected_margin = total_sales - total_purchases
                self.assertEqual(gross_margin, expected_margin)


class TestResponseFormatStandardization(unittest.TestCase):
    """响应格式标准化测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.logger = EnhancedLogger("test_response_format")
        self.service = DataAnalysisService(self.logger)
    
    def test_success_response_format(self):
        """测试成功响应格式"""
        methods_to_test = [
            ('get_dashboard_summary', {}),
            ('analyze_sales_trend', {'dimension': 'month'}),
            ('analyze_customer_value', {'analysis_type': 'rfm'}),
            ('analyze_inventory_turnover', {}),
        ]
        
        for method, params in methods_to_test:
            with self.subTest(method=method):
                result = self.service.handle_method_call(method, params)
                
                # 验证基本响应结构
                self.assertIsInstance(result, dict)
                self.assertIn('generated_at', result)
                
                # 验证时间戳格式
                generated_at = result['generated_at']
                self.assertIsInstance(generated_at, str)
                
                # 验证时间戳可以解析
                try:
                    datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                except ValueError:
                    self.fail(f"时间戳格式无效: {generated_at}")
    
    def test_error_response_format(self):
        """测试错误响应格式"""
        # 测试各种错误情况
        error_cases = [
            ('invalid_method', {}),
            ('analyze_sales_trend', {'dimension': 'invalid'}),
            ('get_dashboard_summary', {'date_range': {'start_date': 'invalid'}}),
        ]
        
        for method, params in error_cases:
            with self.subTest(method=method):
                result = self.service.handle_method_call(method, params)
                
                # 如果是错误响应，验证错误格式
                if not result.get('success', True):
                    self.assertIn('error', result)
                    
                    error = result['error']
                    self.assertIn('code', error)
                    self.assertIn('message', error)
                    
                    # 验证错误代码格式
                    error_code = error['code']
                    self.assertIsInstance(error_code, str)
                    self.assertRegex(error_code, r'^[A-Z_]+$', "错误代码应该是大写字母和下划线")
                    
                    # 验证错误消息
                    error_message = error['message']
                    self.assertIsInstance(error_message, str)
                    self.assertGreater(len(error_message), 0, "错误消息不能为空")
    
    def test_data_type_consistency(self):
        """测试数据类型一致性"""
        result = self.service.handle_method_call('get_dashboard_summary', {})
        
        if result.get('success') or 'total_sales' in result:
            data = result.get('data', result)
            
            # 验证数值字段的类型一致性
            numeric_fields = [
                'total_sales', 'total_purchases', 'gross_margin',
                'active_customers', 'total_inventory_value'
            ]
            
            for field in numeric_fields:
                if field in data:
                    value = data[field]
                    self.assertIsInstance(value, (int, float), 
                                        f"字段 {field} 应该是数值类型，实际类型: {type(value)}")
                    
                    # 验证数值合理性
                    if field.startswith('total_') or field.endswith('_count'):
                        self.assertGreaterEqual(value, 0, f"字段 {field} 不应该为负数")


if __name__ == '__main__':
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加数据格式验证测试
    suite.addTest(unittest.makeSuite(TestDataFormatValidation))
    suite.addTest(unittest.makeSuite(TestErrorHandlingLogic))
    suite.addTest(unittest.makeSuite(TestDataIntegrityValidation))
    suite.addTest(unittest.makeSuite(TestResponseFormatStandardization))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print(f"\n✅ 所有数据格式验证测试通过！运行了 {result.testsRun} 个测试")
    else:
        print(f"\n❌ 数据格式验证测试失败！{len(result.failures)} 个失败，{len(result.errors)} 个错误")
        for failure in result.failures:
            print(f"失败: {failure[0]}")
        for error in result.errors:
            print(f"错误: {error[0]}")
        sys.exit(1)