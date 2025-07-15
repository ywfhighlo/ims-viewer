#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库存盘点报表业务视图脚本
根据库存统计数据生成库存盘点报表
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from enhanced_logger import EnhancedLogger
from db_connection import get_database_connection
from error_handler import error_handler_decorator, safe_execute, global_error_handler
from enhanced_logger import get_logger
from data_utils import DataValidator, DataFormatter, ReportDataProcessor

# 数据库连接函数已移至 db_connection 模块

def generate_inventory_report(start_date: Optional[str] = None, 
                            end_date: Optional[str] = None,
                            product_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    生成库存盘点报表（优化版本 - 使用聚合查询提升性能）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期  
        product_name: 产品名称
        
    Returns:
        库存盘点报表数据列表
    """
    logger = EnhancedLogger("inventory_report")
    
    try:
        db = get_database_connection()
        logger.info("开始生成库存盘点报表（优化版本）")
        
        # 构建聚合管道
        pipeline = []
        
        # 1. 匹配阶段 - 构建过滤条件
        match_conditions = {}
        
        # 产品名称筛选
        if product_name:
            match_conditions['material_name'] = {'$regex': product_name, '$options': 'i'}
            
        if match_conditions:
            pipeline.append({'$match': match_conditions})
            
        logger.info(f"查询条件: {match_conditions}")
        
        # 2. 投影阶段 - 计算衍生字段
        pipeline.append({
            '$project': {
                'product_code': '$material_code',
                'product_name': '$material_name',
                'product_model': '$specification',
                'unit': '$unit',
                'current_stock': {
                    '$toDouble': {
                        '$ifNull': ['$stock_quantity', 0]
                    }
                },
                'inbound_amount': {
                    '$toDouble': {
                        '$ifNull': ['$inbound_amount', 0]
                    }
                },
                'inbound_quantity': {
                    '$toDouble': {
                        '$ifNull': ['$inbound_quantity', 1]
                    }
                },
                'safety_stock': {
                    '$toDouble': {
                        '$ifNull': ['$safety_stock', 0]
                    }
                },
                'last_update_date': '$code_mapping_time',
                'unit_price': {
                    '$cond': {
                        'if': {'$gt': [{'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}, 0]},
                        'then': {
                            '$divide': [
                                {'$toDouble': {'$ifNull': ['$inbound_amount', 0]}},
                                {'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}
                            ]
                        },
                        'else': 0
                    }
                },
                'stock_value': {
                    '$multiply': [
                        {'$toDouble': {'$ifNull': ['$stock_quantity', 0]}},
                        {
                            '$cond': {
                                'if': {'$gt': [{'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}, 0]},
                                'then': {
                                    '$divide': [
                                        {'$toDouble': {'$ifNull': ['$inbound_amount', 0]}},
                                        {'$toDouble': {'$ifNull': ['$inbound_quantity', 1]}}
                                    ]
                                },
                                'else': 0
                            }
                        }
                    ]
                },
                'stock_status': {
                    '$switch': {
                        'branches': [
                            {
                                'case': {'$lte': [{'$toDouble': {'$ifNull': ['$stock_quantity', 0]}}, 0]},
                                'then': '缺货'
                            },
                            {
                                'case': {
                                    '$lte': [
                                        {'$toDouble': {'$ifNull': ['$stock_quantity', 0]}},
                                        {'$toDouble': {'$ifNull': ['$safety_stock', 0]}}
                                    ]
                                },
                                'then': '低库存'
                            }
                        ],
                        'default': '正常'
                    }
                },
                'supplier_name': {'$literal': ''},  # inventory_stats中没有供应商信息
                'generated_date': {'$literal': datetime.now().isoformat()},
                '_id': 0
            }
        })
        
        # 3. 排序阶段 - 按库存价值降序
        pipeline.append({'$sort': {'stock_value': -1}})
        
        # 执行聚合查询
        inventory_collection = db['inventory_stats']
        report_data = list(inventory_collection.aggregate(pipeline))
        
        logger.info(f"聚合查询完成，生成库存盘点报表，共 {len(report_data)} 条记录")
        return report_data
        
    except Exception as e:
        logger.error(f"生成库存盘点报表失败: {str(e)}")
        raise

def format_table_output(data: List[Dict[str, Any]]) -> str:
    """格式化表格输出"""
    if not data:
        return "暂无库存数据"
    
    # 表头
    headers = ['产品编码', '产品名称', '型号', '单位', '当前库存', '单价', '库存价值', '库存状态', '供应商']
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for item in data:
        col_widths[0] = max(col_widths[0], len(str(item.get('product_code', ''))))
        col_widths[1] = max(col_widths[1], len(str(item.get('product_name', ''))))
        col_widths[2] = max(col_widths[2], len(str(item.get('product_model', ''))))
        col_widths[3] = max(col_widths[3], len(str(item.get('unit', ''))))
        col_widths[4] = max(col_widths[4], len(str(item.get('current_stock', ''))))
        col_widths[5] = max(col_widths[5], len(f"{item.get('unit_price', 0):.2f}"))
        col_widths[6] = max(col_widths[6], len(f"{item.get('stock_value', 0):.2f}"))
        col_widths[7] = max(col_widths[7], len(str(item.get('stock_status', ''))))
        col_widths[8] = max(col_widths[8], len(str(item.get('supplier_name', ''))))
    
    # 构建表格
    result = []
    
    # 表头
    header_row = '|'.join(h.ljust(w) for h, w in zip(headers, col_widths))
    result.append(header_row)
    result.append('-' * len(header_row))
    
    # 数据行
    for item in data:
        row = [
            str(item.get('product_code', '')).ljust(col_widths[0]),
            str(item.get('product_name', '')).ljust(col_widths[1]),
            str(item.get('product_model', '')).ljust(col_widths[2]),
            str(item.get('unit', '')).ljust(col_widths[3]),
            str(item.get('current_stock', '')).ljust(col_widths[4]),
            f"{item.get('unit_price', 0):.2f}".ljust(col_widths[5]),
            f"{item.get('stock_value', 0):.2f}".ljust(col_widths[6]),
            str(item.get('stock_status', '')).ljust(col_widths[7]),
            str(item.get('supplier_name', '')).ljust(col_widths[8])
        ]
        result.append('|'.join(row))
    
    # 统计信息
    total_items = len(data)
    total_value = sum(item.get('stock_value', 0) for item in data)
    normal_count = sum(1 for item in data if item.get('stock_status') == '正常')
    low_stock_count = sum(1 for item in data if item.get('stock_status') == '低库存')
    out_of_stock_count = sum(1 for item in data if item.get('stock_status') == '缺货')
    
    result.append('')
    result.append(f"总计: {total_items} 个产品")
    result.append(f"库存总价值: ¥{total_value:.2f}")
    result.append(f"正常库存: {normal_count} 个")
    result.append(f"低库存: {low_stock_count} 个")
    result.append(f"缺货: {out_of_stock_count} 个")
    
    return '\n'.join(result)

@error_handler_decorator(context="库存盘点报表主函数", reraise=False)
def main():
    """主函数"""
    logger = get_logger("inventory_report")
    validator = DataValidator()
    formatter = DataFormatter()
    processor = ReportDataProcessor()
    
    logger.set_context(module="inventory_report", operation="main")
    op_index = logger.start_operation("生成库存盘点报表")
    
    output_format = 'json'  # 默认格式
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成库存盘点报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--product_name', type=str, help='产品名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        product_name = args.product_name
        output_format = args.format
        
        logger.info("开始生成库存盘点报表", 
                   start_date=start_date,
                   end_date=end_date,
                   product_name=product_name,
                   output_format=output_format)
        
        # 验证输入参数
        if start_date and not validator.validate_date_format(start_date):
            raise ValueError(f"开始日期格式无效: {start_date}")
        
        if end_date and not validator.validate_date_format(end_date):
            raise ValueError(f"结束日期格式无效: {end_date}")
        
        # 生成库存盘点报表
        report_data = safe_execute(
            generate_inventory_report,
            (start_date, end_date, product_name),
            default_return=[],
            context="生成库存盘点报表"
        )
        
        if not report_data:
            logger.warning("未生成任何报表数据")
        
        logger.info(f"库存盘点报表生成完成", record_count=len(report_data))
        
        # 输出结果
        if output_format == 'table':
            try:
                formatted_output = format_table_output(report_data)
                print(formatted_output)
            except Exception as e:
                logger.error(f"格式化表格输出失败: {e}")
                print("报表格式化失败")
        else:
            print(json.dumps(report_data, ensure_ascii=False, indent=2))
        
        logger.end_operation(op_index, success=True, record_count=len(report_data))
            
    except Exception as e:
        logger.error(f"库存盘点报表生成失败", error=str(e), include_traceback=True)
        logger.end_operation(op_index, success=False, error=str(e))
        
        if output_format == 'json':
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()