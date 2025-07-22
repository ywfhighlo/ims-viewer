#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析仪表板测试运行器
运行所有数据分析相关的单元测试和集成测试
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
    from scripts.test_data_analysis_comprehensive import (
        TestDataAnalysisServiceCore, TestDashboardSummary, TestSalesTrendAnalysis,
        TestCustomerValueAnalysis, TestInventoryTurnoverAnalysis, TestErrorHandling
    )
    from scripts.test_chart_rendering_comprehensive import (
        TestChartDataFormat, TestFrontendMessageHandling, TestUserInteractionHandling,
        TestChartRenderingCompatibility
    )
    from scripts.test_integration_comprehensive import (
        TestEndToEndDataFlow, TestDataConsistency, TestUserExperienceFlow
    )
    from scripts.test_data_analysis_caching import test_caching_functionality
    from scripts.test_frontend_integration import TestFrontendIntegration, TestDataFlowIntegration
except ImportError as e:
    print(f"警告: 无法导入某些测试模块: {e}")
    print("将跳过相关测试...")


class TestRunner:
    """测试运行器类"""
    
    def __init__(self):
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.start_time = None
        self.test_results = []
    
    def run_test_suite(self, test_classes, suite_name):
        """运行测试套件"""
        print(f"\n{'='*60}")
        print(f"运行 {suite_name}")
        print(f"{'='*60}")
        
        suite = unittest.TestSuite()
        for test_class in test_classes:
            try:
                tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
                suite.addTests(tests)
            except Exception as e:
                print(f"警告: 无法加载测试类 {test_class.__name__}: {e}")
                continue
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # 记录结果
        suite_result = {
            'name': suite_name,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful(),
            'duration': end_time - start_time
        }
        
        self.test_results.append(suite_result)
        self.total_tests += result.testsRun
        self.total_failures += len(result.failures)
        self.total_errors += len(result.errors)
        
        # 输出套件结果
        if result.wasSuccessful():
            print(f"\n✅ {suite_name} 全部通过!")
            print(f"运行了 {result.testsRun} 个测试，耗时 {suite_result['duration']:.2f} 秒")
        else:
            print(f"\n❌ {suite_name} 有失败!")
            print(f"运行了 {result.testsRun} 个测试")
            print(f"{len(result.failures)} 个失败，{len(result.errors)} 个错误")
            print(f"耗时 {suite_result['duration']:.2f} 秒")
            
            # 显示失败详情
            if result.failures:
                print(f"\n失败的测试:")
                for test, traceback in result.failures[:3]:  # 只显示前3个
                    print(f"- {test}")
                    # 提取关键错误信息
                    error_lines = traceback.split('\n')
                    for line in error_lines:
                        if 'AssertionError:' in line:
                            print(f"  {line.strip()}")
                            break
                if len(result.failures) > 3:
                    print(f"  ... 还有 {len(result.failures) - 3} 个失败")
            
            if result.errors:
                print(f"\n错误的测试:")
                for test, traceback in result.errors[:3]:  # 只显示前3个
                    print(f"- {test}")
                    # 提取关键错误信息
                    error_lines = traceback.split('\n')
                    for line in error_lines:
                        if any(keyword in line for keyword in ['Error:', 'Exception:']):
                            print(f"  {line.strip()}")
                            break
                if len(result.errors) > 3:
                    print(f"  ... 还有 {len(result.errors) - 3} 个错误")
        
        return result.wasSuccessful()
    
    def run_all_tests(self):
        """运行所有测试"""
        self.start_time = time.time()
        
        print("开始运行数据分析仪表板测试套件")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_success = True
        
        # 1. 核心功能单元测试
        try:
            core_test_classes = [
                TestDataAnalysisServiceCore,
                TestDashboardSummary,
                TestSalesTrendAnalysis,
                TestCustomerValueAnalysis,
                TestInventoryTurnoverAnalysis,
                TestErrorHandling
            ]
            success = self.run_test_suite(core_test_classes, "核心功能单元测试")
            all_success = all_success and success
        except NameError:
            print("跳过核心功能单元测试 (模块未找到)")
        
        # 2. 原有单元测试
        try:
            unit_test_classes = [
                TestDataAnalysisService,
                TestDataAnalysisServiceIntegration
            ]
            success = self.run_test_suite(unit_test_classes, "原有单元测试")
            all_success = all_success and success
        except NameError:
            print("跳过原有单元测试 (模块未找到)")
        
        # 3. 图表渲染测试
        try:
            chart_test_classes = [
                TestChartDataFormat,
                TestFrontendMessageHandling,
                TestUserInteractionHandling,
                TestChartRenderingCompatibility
            ]
            success = self.run_test_suite(chart_test_classes, "图表渲染和前端集成测试")
            all_success = all_success and success
        except NameError:
            print("跳过图表渲染测试 (模块未找到)")
        
        # 4. 前后端集成测试
        try:
            integration_test_classes = [
                TestFrontendIntegration,
                TestDataFlowIntegration
            ]
            success = self.run_test_suite(integration_test_classes, "前后端集成测试")
            all_success = all_success and success
        except NameError:
            print("跳过前后端集成测试 (模块未找到)")
        
        # 5. 端到端集成测试
        try:
            e2e_test_classes = [
                TestEndToEndDataFlow,
                TestDataConsistency,
                TestUserExperienceFlow
            ]
            success = self.run_test_suite(e2e_test_classes, "端到端集成测试")
            all_success = all_success and success
        except NameError:
            print("跳过端到端集成测试 (模块未找到)")
        
        # 6. 缓存功能测试 (函数式测试)
        try:
            print(f"\n{'='*60}")
            print("运行缓存功能测试")
            print(f"{'='*60}")
            
            start_time = time.time()
            test_caching_functionality()
            end_time = time.time()
            
            print(f"\n✅ 缓存功能测试完成，耗时 {end_time - start_time:.2f} 秒")
        except Exception as e:
            print(f"\n❌ 缓存功能测试失败: {e}")
            all_success = False
        
        # 输出总结
        self.print_summary(all_success)
        
        return all_success
    
    def print_summary(self, all_success):
        """打印测试总结"""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        print(f"\n{'='*60}")
        print("测试总结")
        print(f"{'='*60}")
        
        print(f"总测试数: {self.total_tests}")
        print(f"总失败数: {self.total_failures}")
        print(f"总错误数: {self.total_errors}")
        print(f"总耗时: {total_duration:.2f} 秒")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 按测试套件显示结果
        print(f"\n各测试套件结果:")
        for result in self.test_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"  {result['name']}: {status}")
            print(f"    测试数: {result['tests_run']}, 失败: {result['failures']}, 错误: {result['errors']}")
            print(f"    耗时: {result['duration']:.2f} 秒")
        
        # 总体结果
        if all_success:
            print(f"\n🎉 所有测试通过！数据分析仪表板功能正常！")
        else:
            print(f"\n⚠️  有测试失败，请检查上述错误信息")
            
            # 提供故障排除建议
            print(f"\n故障排除建议:")
            print(f"1. 检查数据库连接是否正常")
            print(f"2. 确认所有依赖模块已正确安装")
            print(f"3. 验证测试数据是否完整")
            print(f"4. 检查系统资源是否充足")
        
        print(f"{'='*60}")


def main():
    """主函数"""
    try:
        runner = TestRunner()
        success = runner.run_all_tests()
        
        # 根据测试结果设置退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试运行器发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()