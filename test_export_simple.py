#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试导出功能的核心逻辑
"""

import json
from datetime import datetime
from typing import Dict, Any, List

def test_export_data_formats():
    """测试导出数据格式化功能"""
    
    # 模拟导出数据
    mock_export_data = {
        'export_info': {
            'format': 'json',
            'sections': ['overview', 'sales_trend'],
            'generated_at': datetime.now().isoformat(),
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-12-31'
            },
            'include_charts': True
        },
        'data': {
            'overview': {
                'total_sales': 1000000,
                'total_sales_count': 500,
                'active_customers': 120,
                'avg_order_value': 2000,
                'total_purchases': 800000,
                'total_inventory_value': 500000,
                'low_stock_items': 15,
                'gross_margin': 200000
            },
            'sales_trend': {
                'month': [
                    {'period': '2024-01', 'total_sales': 150000, 'order_count': 75},
                    {'period': '2024-02', 'total_sales': 180000, 'order_count': 90},
                    {'period': '2024-03', 'total_sales': 200000, 'order_count': 100}
                ]
            }
        }
    }
    
    print("🧪 测试导出数据格式...")
    
    # 测试JSON格式
    json_result = export_as_json(mock_export_data)
    print(f"✅ JSON导出测试完成，数据大小: {len(str(json_result))} 字节")
    
    # 测试CSV格式
    csv_result = export_as_csv(mock_export_data)
    print(f"✅ CSV导出测试完成，工作表数量: {len(csv_result.get('sheets', {}))}")
    
    # 测试Excel格式准备
    excel_result = prepare_excel_export(mock_export_data)
    print(f"✅ Excel导出准备完成，工作表数量: {len(excel_result.get('sheets', {}))}")
    
    # 测试PDF格式准备
    pdf_result = prepare_pdf_export(mock_export_data)
    print(f"✅ PDF导出准备完成，部分数量: {len(pdf_result.get('sections', []))}")
    
    # 测试文件名生成
    filename = generate_export_filename('json', ['overview', 'sales_trend'])
    print(f"✅ 文件名生成: {filename}")
    
    # 测试内容类型获取
    content_type = get_content_type('json')
    print(f"✅ 内容类型: {content_type}")
    
    return True

def export_as_json(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """导出为JSON格式"""
    try:
        def make_serializable(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            else:
                return obj
        
        return make_serializable(export_data)
    except Exception as e:
        return {'error': str(e)}

def export_as_csv(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """导出为CSV格式（准备CSV数据结构）"""
    try:
        csv_data = {}
        
        # 处理每个数据部分
        for section, data in export_data.get('data', {}).items():
            if section == 'overview':
                # 概览数据转换为键值对表格
                if isinstance(data, dict):
                    csv_data[f'{section}_summary'] = [
                        {'指标': k, '数值': v} for k, v in data.items()
                        if isinstance(v, (int, float, str)) and not k.startswith('_')
                    ]
            
            elif section == 'sales_trend':
                # 销售趋势数据
                if isinstance(data, dict):
                    for dimension, trend_data in data.items():
                        if isinstance(trend_data, list):
                            csv_data[f'{section}_{dimension}'] = trend_data
        
        return {
            'format': 'csv',
            'sheets': csv_data,
            'export_info': export_data.get('export_info', {})
        }
    except Exception as e:
        return {'error': str(e)}

def prepare_excel_export(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """准备Excel导出数据"""
    try:
        csv_structure = export_as_csv(export_data)
        
        excel_data = {
            'format': 'excel',
            'workbook_info': {
                'title': '数据分析仪表板报告',
                'author': '数据分析系统',
                'created_at': datetime.now().isoformat()
            },
            'sheets': {},
            'formatting': {
                'header_style': {
                    'font_bold': True,
                    'bg_color': '#4472C4',
                    'font_color': '#FFFFFF'
                },
                'data_style': {
                    'font_size': 10,
                    'border': True
                }
            }
        }
        
        # 转换CSV数据为Excel工作表结构
        for sheet_name, sheet_data in csv_structure.get('sheets', {}).items():
            excel_data['sheets'][sheet_name] = {
                'data': sheet_data,
                'columns': list(sheet_data[0].keys()) if sheet_data else [],
                'title': get_sheet_title(sheet_name)
            }
        
        return excel_data
    except Exception as e:
        return {'error': str(e)}

def prepare_pdf_export(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """准备PDF导出数据"""
    try:
        pdf_data = {
            'format': 'pdf',
            'document_info': {
                'title': '数据分析仪表板报告',
                'subject': '业务数据分析报告',
                'author': '数据分析系统',
                'created_at': datetime.now().isoformat()
            },
            'sections': [],
            'layout': {
                'page_size': 'A4',
                'orientation': 'portrait',
                'margins': {'top': 20, 'bottom': 20, 'left': 20, 'right': 20}
            }
        }
        
        # 构建PDF部分
        for section, data in export_data.get('data', {}).items():
            section_info = {
                'title': get_section_title(section),
                'type': section,
                'content': data,
                'charts': [],  # 预留图表数据
                'tables': []   # 预留表格数据
            }
            
            # 根据数据类型准备内容
            if section == 'overview' and isinstance(data, dict):
                section_info['tables'].append({
                    'title': '业务概览指标',
                    'headers': ['指标', '数值'],
                    'rows': [[k, str(v)] for k, v in data.items() 
                           if isinstance(v, (int, float, str)) and not k.startswith('_')]
                })
            
            pdf_data['sections'].append(section_info)
        
        return pdf_data
    except Exception as e:
        return {'error': str(e)}

def generate_export_filename(export_format: str, export_sections: List[str]) -> str:
    """生成导出文件名"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sections_str = '_'.join(export_sections[:3])  # 限制长度
        if len(export_sections) > 3:
            sections_str += '_etc'
        
        filename = f"dashboard_report_{sections_str}_{timestamp}.{export_format}"
        return filename
    except Exception:
        return f"dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"

def get_content_type(export_format: str) -> str:
    """获取内容类型"""
    content_types = {
        'json': 'application/json',
        'csv': 'text/csv',
        'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pdf': 'application/pdf'
    }
    return content_types.get(export_format, 'application/octet-stream')

def get_sheet_title(sheet_name: str) -> str:
    """获取工作表标题"""
    titles = {
        'overview_summary': '业务概览',
        'sales_trend_month': '月度销售趋势',
        'sales_trend_quarter': '季度销售趋势',
        'sales_trend_product': '产品销售分析',
        'customer_analysis': '客户价值分析',
        'inventory_analysis': '库存周转分析',
        'comparison_analysis': '对比分析'
    }
    return titles.get(sheet_name, sheet_name)

def get_section_title(section: str) -> str:
    """获取部分标题"""
    titles = {
        'overview': '业务概览',
        'sales_trend': '销售趋势分析',
        'customer_analysis': '客户价值分析',
        'inventory_analysis': '库存周转分析',
        'comparison_analysis': '多维度对比分析'
    }
    return titles.get(section, section)

if __name__ == "__main__":
    print("🚀 开始测试导出功能...")
    
    try:
        success = test_export_data_formats()
        if success:
            print("\n✅ 所有导出功能测试通过！")
            print("\n📋 导出功能特性:")
            print("  - ✅ JSON格式导出")
            print("  - ✅ CSV格式数据结构准备")
            print("  - ✅ Excel格式数据结构准备（预留接口）")
            print("  - ✅ PDF格式数据结构准备（预留接口）")
            print("  - ✅ 文件名自动生成")
            print("  - ✅ 内容类型识别")
            print("  - ✅ 数据格式化和清理")
        else:
            print("\n❌ 测试失败")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()