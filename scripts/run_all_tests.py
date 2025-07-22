#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析仪表板修复 - 完整测试套件运行器
运行所有单元测试和集成测试
"""

import sys
import os
import unittest
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有测试模块
try:
    from scripts.test_data_analysis_service_unit import TestDataAnalysisService, TestDataAnalysisServiceIntegration
    from scripts.test_frontend_integration import TestFrontendIntegration, TestDataFlowIntegration
    from scripts.test_chart_rendering import TestChartDataFormat, TestDataVisualizationLogic, TestUserInteractionSimulation, TestErrorHandlingInUI
    from scripts.test_data_format_validation import TestDataFormatValidation, TestErrorHandlingLogic, TestDataIntegrityValidation, TestResponseFormatStandardization
    from scripts.enhanced_logger import EnhancedLogger
except ImportError as e:
    print(f"❌ 导入测试模块失败: {str(e)}")
    print("请确保所有测试文件都已创建并且路径正确")
    sys.exit(1)


class TestSuiteRunner:
    """测试套件运行器"""
    
    def __init__(self):
        self.logger = EnhancedLogger("test_suite_runner")
        self.start_time = None
        self.results = {}
    
    def run_test_suite(self, suite_name, test_classes, verbosity=1):
        """运行测试套件"""
        print(f"\n{'='*60}")
        print(f"运行测试套件: {suite_name}")
        print(f"{'='*60}")
        
        suite = unittest.TestSuite()
        
        # 添加测试类到套件
        for test_class in test_classes:
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(test_class))
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # 记录结果
        self.results[suite_name] = {
            'result': result,
            'duration': end_time - start_time,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful()
        }
        
        # 输出套件结果
        print(f"\n{suite_name} 测试结果:")
        print(f"  运行时间: {end_time - start_time:.2f}秒")
        print(f"  测试数量: {result.testsRun}")
        print(f"  失败数量: {len(result.failures)}")
        print(f"  错误数量: {len(result.errors)}")
        print(f"  成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1) * 100):.1f}%")
        
        if result.failures:
            print(f"\n失败的测试:")
            for failure in result.failures:
                print(f"  - {failure[0]}")
        
        if result.errors:
            print(f"\n错误的测试:")
            for error in result.errors:
                print(f"  - {error[0]}")
        
        return result.wasSuccessful()
    
    def run_all_tests(self, verbosity=1):
        """运行所有测试"""
        self.start_time = time.time()
        
        print("🚀 开始运行数据分析仪表板修复测试套件")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 定义测试套件
        test_suites = [
            {
                'name': '单元测试',
                'classes': [TestDataAnalysisService, TestDataAnalysisServiceIntegration],
                'description': '测试数据分析服务的各个方法的单元测试'
            },
            {
                'name': '数据格式验证测试',
                'classes': [TestDataFormatValidation, TestErrorHandlingLogic, TestDataIntegrityValidation, TestResponseFormatStandardization],
                'description': '测试数据格式验证和错误处理逻辑'
            },
            {
                'name': '前后端集成测试',
                'classes': [TestFrontendIntegration, TestDataFlowIntegration],
                'description': '测试前后端数据流和集成功能'
            },
            {
                'name': '图表渲染测试',
                'classes': [TestChartDataFormat, TestDataVisualizationLogic, TestUserInteractionSimulation, TestErrorHandlingInUI],
                'description': '测试图表渲染和用户交互功能'
            }
        ]
        
        # 运行每个测试套件
        all_success = True
        for suite_info in test_suites:
            print(f"\n📋 {suite_info['description']}")
            success = self.run_test_suite(
                suite_info['name'], 
                suite_info['classes'], 
                verbosity
            )
            if not success:
                all_success = False
        
        # 输出总结
        self.print_summary(all_success)
        
        return all_success
    
    def print_summary(self, all_success):
        """打印测试总结"""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        print(f"\n{'='*80}")
        print("📊 测试总结报告")
        print(f"{'='*80}")
        
        total_tests = sum(r['tests_run'] for r in self.results.values())
        total_failures = sum(r['failures'] for r in self.results.values())
        total_errors = sum(r['errors'] for r in self.results.values())
        success_rate = ((total_tests - total_failures - total_errors) / max(total_tests, 1) * 100)
        
        print(f"总运行时间: {total_duration:.2f}秒")
        print(f"总测试数量: {total_tests}")
        print(f"总失败数量: {total_failures}")
        print(f"总错误数量: {total_errors}")
        print(f"总成功率: {success_rate:.1f}%")
        
        print(f"\n各测试套件详情:")
        for suite_name, result_info in self.results.items():
            status = "✅ 通过" if result_info['success'] else "❌ 失败"
            print(f"  {suite_name}: {status} ({result_info['tests_run']}个测试, {result_info['duration']:.2f}秒)")
        
        if all_success:
            print(f"\n🎉 所有测试通过！数据分析仪表板修复功能测试完成。")
            print(f"✅ 验证了以下功能:")
            print(f"   - 数据分析服务的各个方法")
            print(f"   - 数据格式验证和错误处理")
            print(f"   - 前后端数据流集成")
            print(f"   - 图表渲染和用户交互")
        else:
            print(f"\n💥 部分测试失败！请检查失败的测试并修复相关问题。")
            
            # 列出失败的测试套件
            failed_suites = [name for name, info in self.results.items() if not info['success']]
            if failed_suites:
                print(f"失败的测试套件: {', '.join(failed_suites)}")
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
    
    def run_specific_suite(self, suite_name, verbosity=1):
        """运行特定的测试套件"""
        suite_mapping = {
            'unit': [TestDataAnalysisService, TestDataAnalysisServiceIntegration],
            'validation': [TestDataFormatValidation, TestErrorHandlingLogic, TestDataIntegrityValidation, TestResponseFormatStandardization],
            'integration': [TestFrontendIntegration, TestDataFlowIntegration],
            'chart': [TestChartDataFormat, TestDataVisualizationLogic, TestUserInteractionSimulation, TestErrorHandlingInUI]
        }
        
        if suite_name not in suite_mapping:
            print(f"❌ 未知的测试套件: {suite_name}")
            print(f"可用的测试套件: {', '.join(suite_mapping.keys())}")
            return False
        
        self.start_time = time.time()
        success = self.run_test_suite(suite_name, suite_mapping[suite_name], verbosity)
        self.print_summary(success)
        
        return success


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据分析仪表板修复测试套件')
    parser.add_argument('--suite', choices=['unit', 'validation', 'integration', 'chart', 'all'], 
                       default='all', help='要运行的测试套件')
    parser.add_argument('--verbose', '-v', action='count', default=1, 
                       help='详细程度 (使用 -v, -vv 增加详细程度)')
    parser.add_argument('--quiet', '-q', action='store_true', 
                       help='安静模式，只显示结果')
    
    args = parser.parse_args()
    
    # 设置详细程度
    if args.quiet:
        verbosity = 0
    else:
        verbosity = min(args.verbose, 2)
    
    # 创建测试运行器
    runner = TestSuiteRunner()
    
    try:
        if args.suite == 'all':
            success = runner.run_all_tests(verbosity)
        else:
            success = runner.run_specific_suite(args.suite, verbosity)
        
        # 根据测试结果设置退出代码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 测试运行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()