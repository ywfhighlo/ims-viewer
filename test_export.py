#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试导出功能
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.data_analysis_service import DataAnalysisService
from scripts.enhanced_logger import EnhancedLogger

def test_export_functionality():
    """测试导出功能"""
    logger = EnhancedLogger("test_export")
    service = DataAnalysisService(logger)
    
    # 测试参数
    test_params = {
        'export_format': 'json',
        'export_sections': ['overview'],
        'date_range': {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        },
        'include_charts': True
    }
    
    print("🧪 开始测试导出功能...")
    print(f"测试参数: {json.dumps(test_params, indent=2, ensure_ascii=False)}")
    
    try:
        # 调用导出方法
        result = service.export_dashboard_data(test_params)
        
        print("✅ 导出测试完成")
        print(f"成功状态: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"导出格式: {result.get('export_format')}")
            print(f"导出部分: {result.get('export_sections')}")
            print(f"数据大小: {result.get('data_size')} 字节")
            print(f"文件信息: {result.get('download_info', {})}")
            
            # 显示导出数据的结构（不显示完整内容）
            export_data = result.get('export_data', {})
            if isinstance(export_data, dict):
                print(f"导出数据结构: {list(export_data.keys())}")
                if 'data' in export_data:
                    print(f"数据部分: {list(export_data['data'].keys())}")
        else:
            print(f"导出失败: {result.get('error', {})}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_export_functionality()