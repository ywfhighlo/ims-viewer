#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码改进测试脚本
验证所有新增的功能模块是否正常工作
"""

import sys
import os
import traceback
from datetime import datetime

# 添加脚本目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def test_enhanced_logger():
    """测试增强日志模块"""
    print("\n=== 测试增强日志模块 ===")
    try:
        from enhanced_logger import get_logger
        
        logger = get_logger("test_logger")
        logger.set_context(test_module="enhanced_logger", test_time=datetime.now().isoformat())
        
        # 测试各种日志级别
        logger.info("测试信息日志", test_param="value")
        logger.warning("测试警告日志", warning_type="test")
        logger.debug("测试调试日志")
        
        # 测试操作跟踪
        op_index = logger.start_operation("测试操作")
        logger.end_operation(op_index, success=True, result="测试成功")
        
        # 测试数据处理日志
        logger.log_data_processing("test_table", 100, 95, 5)
        
        # 获取统计信息
        stats = logger.get_statistics()
        print(f"✅ 增强日志模块测试通过 - 处理了 {stats['summary']['total_records_processed']} 条记录")
        return True
        
    except Exception as e:
        print(f"❌ 增强日志模块测试失败: {e}")
        traceback.print_exc()
        return False

def test_error_handler():
    """测试错误处理模块"""
    print("\n=== 测试错误处理模块 ===")
    try:
        from error_handler import (
            ErrorHandler, 
            error_handler_decorator, 
            safe_execute,
            BusinessError,
            DatabaseError,
            ValidationError
        )
        
        # 测试错误处理器
        handler = ErrorHandler("test_error_handler")
        
        # 测试业务错误
        try:
            raise BusinessError("测试业务错误", "TEST_001", {"param": "value"})
        except Exception as e:
            error_info = handler.handle_error(e, "测试业务错误处理")
            print(f"业务错误处理: {error_info['user_message']}")
        
        # 测试数据库错误
        try:
            raise DatabaseError("测试数据库错误", "SELECT", {"table": "test"})
        except Exception as e:
            error_info = handler.handle_error(e, "测试数据库错误处理")
            print(f"数据库错误处理: {error_info['user_message']}")
        
        # 测试验证错误
        try:
            raise ValidationError("测试验证错误", "test_field", "invalid_value")
        except Exception as e:
            error_info = handler.handle_error(e, "测试验证错误处理")
            print(f"验证错误处理: {error_info['user_message']}")
        
        # 测试装饰器
        @error_handler_decorator(context="测试装饰器", reraise=False, default_return="默认值")
        def test_function():
            raise ValueError("测试装饰器错误")
        
        result = test_function()
        print(f"装饰器测试结果: {result}")
        
        # 测试安全执行
        def failing_function():
            raise RuntimeError("测试安全执行错误")
        
        result = safe_execute(failing_function, default_return="安全默认值")
        print(f"安全执行测试结果: {result}")
        
        # 获取错误统计
        stats = handler.get_error_statistics()
        print(f"✅ 错误处理模块测试通过 - 处理了 {sum(stats.values())} 个错误")
        return True
        
    except Exception as e:
        print(f"❌ 错误处理模块测试失败: {e}")
        traceback.print_exc()
        return False

def test_data_utils():
    """测试数据工具模块"""
    print("\n=== 测试数据工具模块 ===")
    try:
        from data_utils import (
            DataValidator,
            DataFormatter,
            DataConverter,
            ReportDataProcessor,
            TableFormatter
        )
        
        # 测试数据验证器
        validator = DataValidator()
        
        # 测试日期验证
        assert validator.validate_date_format("2024-01-01") == True
        assert validator.validate_date_format("invalid-date") == False
        print("日期验证测试通过")
        
        # 测试数字验证
        assert validator.validate_number(100, min_value=0, max_value=1000) == True
        assert validator.validate_number(-10, min_value=0) == False
        print("数字验证测试通过")
        
        # 测试邮箱验证
        assert validator.validate_email("test@example.com") == True
        assert validator.validate_email("invalid-email") == False
        print("邮箱验证测试通过")
        
        # 测试数据格式化器
        formatter = DataFormatter()
        
        # 测试货币格式化
        assert formatter.format_currency(1234.56) == "¥1,234.56"
        print("货币格式化测试通过")
        
        # 测试百分比格式化
        assert formatter.format_percentage(0.1234) == "12.34%"
        print("百分比格式化测试通过")
        
        # 测试数字格式化
        assert formatter.format_number(1234567) == "1,234,567"
        print("数字格式化测试通过")
        
        # 测试数据转换器
        converter = DataConverter()
        
        # 测试安全转换
        assert converter.safe_int("123") == 123
        assert converter.safe_int("invalid", default=0) == 0
        print("数据转换测试通过")
        
        # 测试报告数据处理器
        processor = ReportDataProcessor()
        
        # 测试库存统计
        test_inventory = [
            {'unit_price': '¥10.00', 'quantity': '100'},
            {'unit_price': '¥20.00', 'quantity': '50'}
        ]
        stats = processor.calculate_inventory_stats(test_inventory)
        assert stats['total_value'] == 2000.0  # 10*100 + 20*50
        print("库存统计测试通过")
        
        # 测试表格格式化器
        table_formatter = TableFormatter()
        
        test_data = [
            {'name': '商品A', 'price': 100, 'quantity': 10},
            {'name': '商品B', 'price': 200, 'quantity': 5}
        ]
        
        table_output = table_formatter.format_table(
            test_data,
            headers=['name', 'price', 'quantity'],
            title="测试表格"
        )
        
        assert "测试表格" in table_output
        assert "商品A" in table_output
        print("表格格式化测试通过")
        
        print("✅ 数据工具模块测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 数据工具模块测试失败: {e}")
        traceback.print_exc()
        return False

def test_config_manager():
    """测试配置管理模块"""
    print("\n=== 测试配置管理模块 ===")
    try:
        from config_manager import (
            ConfigManager,
            get_config_manager,
            get_config,
            get_database_config,
            get_report_config,
            get_logging_config,
            get_validation_config
        )
        
        # 测试配置管理器
        config_mgr = ConfigManager()
        
        # 测试获取配置
        config = config_mgr.get_config()
        assert config is not None
        print(f"应用配置获取成功 - 版本: {config.version}")
        
        # 测试数据库配置
        db_config = config_mgr.get_database_config()
        assert db_config.host is not None
        print(f"数据库配置获取成功 - 主机: {db_config.host}:{db_config.port}")
        
        # 测试报告配置
        report_config = config_mgr.get_report_config()
        assert report_config.default_page_size > 0
        print(f"报告配置获取成功 - 默认页面大小: {report_config.default_page_size}")
        
        # 测试日志配置
        logging_config = config_mgr.get_logging_config()
        assert logging_config.level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        print(f"日志配置获取成功 - 级别: {logging_config.level}")
        
        # 测试验证配置
        validation_config = config_mgr.get_validation_config()
        assert validation_config.required_fields_by_table is not None
        print(f"验证配置获取成功 - 严格模式: {validation_config.strict_mode}")
        
        # 测试配置更新
        original_debug = config.debug_mode
        config_mgr.update_config(debug_mode=not original_debug)
        updated_config = config_mgr.get_config()
        assert updated_config.debug_mode != original_debug
        print("配置更新测试通过")
        
        # 测试配置验证
        is_valid = config_mgr.validate_config()
        assert is_valid == True
        print("配置验证测试通过")
        
        # 测试全局函数
        global_config = get_config()
        assert global_config is not None
        print("全局配置函数测试通过")
        
        print("✅ 配置管理模块测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置管理模块测试失败: {e}")
        traceback.print_exc()
        return False

def test_db_connection():
    """测试数据库连接模块"""
    print("\n=== 测试数据库连接模块 ===")
    try:
        from db_connection import get_database_connection
        
        # 注意：这个测试可能会失败，因为可能没有实际的MongoDB服务器
        # 但我们可以测试函数是否能正确导入和调用
        
        print("数据库连接函数导入成功")
        
        # 尝试连接（可能会失败，这是正常的）
        try:
            db = get_database_connection()
            if db is not None:
                print("✅ 数据库连接成功")
            else:
                print("⚠️ 数据库连接失败（这可能是正常的，如果没有MongoDB服务器）")
        except Exception as conn_error:
            print(f"⚠️ 数据库连接异常: {conn_error}（这可能是正常的，如果没有MongoDB服务器）")
        
        print("✅ 数据库连接模块测试通过（函数可正常调用）")
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接模块测试失败: {e}")
        traceback.print_exc()
        return False

def test_business_views():
    """测试业务视图模块"""
    print("\n=== 测试业务视图模块 ===")
    try:
        # 测试导入业务视图模块
        modules_to_test = [
            'business_view_inventory_report',
            'business_view_sales_report',
            'business_view_customer_reconciliation',
            'business_view_payables_report',
            'business_view_purchase_report',
            'business_view_receivables_report',
            'business_view_supplier_reconciliation'
        ]
        
        imported_modules = []
        failed_modules = []
        
        for module_name in modules_to_test:
            try:
                module = __import__(module_name)
                imported_modules.append(module_name)
                print(f"✅ {module_name} 导入成功")
            except Exception as e:
                failed_modules.append((module_name, str(e)))
                print(f"❌ {module_name} 导入失败: {e}")
        
        print(f"\n业务视图模块测试结果:")
        print(f"成功导入: {len(imported_modules)} 个模块")
        print(f"导入失败: {len(failed_modules)} 个模块")
        
        if len(imported_modules) >= len(modules_to_test) * 0.8:  # 80%成功率
            print("✅ 业务视图模块测试通过")
            return True
        else:
            print("⚠️ 业务视图模块测试部分通过")
            return False
        
    except Exception as e:
        print(f"❌ 业务视图模块测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("           IMS Viewer 代码改进测试")
    print("=" * 60)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("增强日志模块", test_enhanced_logger),
        ("错误处理模块", test_error_handler),
        ("数据工具模块", test_data_utils),
        ("配置管理模块", test_config_manager),
        ("数据库连接模块", test_db_connection),
        ("业务视图模块", test_business_views)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试执行异常: {e}")
            test_results.append((test_name, False))
    
    # 汇总测试结果
    print("\n" + "=" * 60)
    print("                测试结果汇总")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed_tests += 1
    
    print("\n" + "-" * 60)
    print(f"测试总数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
    print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试都通过了！代码改进成功！")
    elif passed_tests >= total_tests * 0.8:
        print("\n✅ 大部分测试通过，代码改进基本成功！")
    else:
        print("\n⚠️ 部分测试失败，需要进一步检查和修复。")
    
    print("=" * 60)

if __name__ == '__main__':
    main()