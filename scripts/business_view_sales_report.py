#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
销售统计报表业务视图脚本
根据销售出库数据生成销售统计报表
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

def generate_sales_report(start_date: Optional[str] = None, 
                         end_date: Optional[str] = None,
                         customer_name: Optional[str] = None,
                         product_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    生成销售统计报表（优化版本 - 使用聚合查询提升性能）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        customer_name: 客户名称
        product_name: 产品名称
        
    Returns:
        销售统计报表数据列表
    """
    logger = EnhancedLogger("sales_report")
    
    try:
        db = get_database_connection()
        logger.info("开始生成销售统计报表（优化版本）")
        
        # 构建聚合管道
        pipeline = []
        
        # 1. 匹配阶段 - 构建过滤条件
        match_conditions = {}
        
        # 日期范围筛选
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            match_conditions['outbound_date'] = date_query
            
        # 客户名称筛选
        if customer_name:
            match_conditions['customer_name'] = {'$regex': customer_name, '$options': 'i'}
            
        # 产品名称筛选
        if product_name:
            match_conditions['material_name'] = {'$regex': product_name, '$options': 'i'}
            
        if match_conditions:
            pipeline.append({'$match': match_conditions})
            
        logger.info(f"查询条件: {match_conditions}")
        
        # 2. 分组聚合阶段
        pipeline.append({
            '$group': {
                '_id': {
                    'material_code': '$material_code',
                    'material_name': '$material_name'
                },
                'product_model': {'$first': '$specification'},
                'unit': {'$first': '$unit'},
                'total_quantity': {'$sum': '$quantity'},
                'total_amount': {'$sum': '$outbound_amount'},
                'sales_count': {'$sum': 1},
                'customers': {'$addToSet': '$customer_name'},
                'latest_sale_date': {'$max': '$outbound_date'}
            }
        })
        
        # 3. 投影阶段 - 计算衍生字段
        pipeline.append({
            '$project': {
                'product_code': '$_id.material_code',
                'product_name': '$_id.material_name',
                'product_model': 1,
                'unit': 1,
                'total_quantity': 1,
                'total_amount': 1,
                'sales_count': 1,
                'customer_count': {'$size': '$customers'},
                'latest_sale_date': 1,
                'avg_unit_price': {
                    '$cond': {
                        'if': {'$gt': ['$total_quantity', 0]},
                        'then': {'$divide': ['$total_amount', '$total_quantity']},
                        'else': 0
                    }
                },
                'sales_trend': {
                    '$switch': {
                        'branches': [
                            {'case': {'$gte': ['$sales_count', 10]}, 'then': '热销'},
                            {'case': {'$gte': ['$sales_count', 5]}, 'then': '正常'}
                        ],
                        'default': '滞销'
                    }
                },
                'generated_date': {'$literal': datetime.now().isoformat()},
                '_id': 0
            }
        })
        
        # 4. 排序阶段 - 按销售金额降序
        pipeline.append({'$sort': {'total_amount': -1}})
        
        # 执行聚合查询
        sales_collection = db['sales_outbound']
        report_data = list(sales_collection.aggregate(pipeline))
        
        logger.info(f"聚合查询完成，生成销售统计报表，共 {len(report_data)} 个产品")
        return report_data

        
    except Exception as e:
        logger.error(f"生成销售统计报表失败: {str(e)}")
        raise

def format_table_output(data: List[Dict[str, Any]]) -> str:
    """格式化表格输出"""
    if not data:
        return "暂无销售数据"
    
    # 表头
    headers = ['产品编码', '产品名称', '型号', '销售数量', '销售金额', '销售次数', '客户数', '平均单价', '销售趋势', '最近销售日期']
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for item in data:
        col_widths[0] = max(col_widths[0], len(str(item.get('product_code', ''))))
        col_widths[1] = max(col_widths[1], len(str(item.get('product_name', ''))))
        col_widths[2] = max(col_widths[2], len(str(item.get('product_model', ''))))
        col_widths[3] = max(col_widths[3], len(str(item.get('total_quantity', ''))))
        col_widths[4] = max(col_widths[4], len(f"{item.get('total_amount', 0):.2f}"))
        col_widths[5] = max(col_widths[5], len(str(item.get('sales_count', ''))))
        col_widths[6] = max(col_widths[6], len(str(item.get('customer_count', ''))))
        col_widths[7] = max(col_widths[7], len(f"{item.get('avg_unit_price', 0):.2f}"))
        col_widths[8] = max(col_widths[8], len(str(item.get('sales_trend', ''))))
        col_widths[9] = max(col_widths[9], len(str(item.get('latest_sale_date', ''))))
    
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
            str(item.get('total_quantity', '')).ljust(col_widths[3]),
            f"{item.get('total_amount', 0):.2f}".ljust(col_widths[4]),
            str(item.get('sales_count', '')).ljust(col_widths[5]),
            str(item.get('customer_count', '')).ljust(col_widths[6]),
            f"{item.get('avg_unit_price', 0):.2f}".ljust(col_widths[7]),
            str(item.get('sales_trend', '')).ljust(col_widths[8]),
            str(item.get('latest_sale_date', '')).ljust(col_widths[9])
        ]
        result.append('|'.join(row))
    
    # 统计信息
    total_products = len(data)
    total_quantity = sum(item.get('total_quantity', 0) for item in data)
    total_amount = sum(item.get('total_amount', 0) for item in data)
    hot_products = sum(1 for item in data if item.get('sales_trend') == '热销')
    slow_products = sum(1 for item in data if item.get('sales_trend') == '滞销')
    
    result.append('')
    result.append(f"总计: {total_products} 个产品")
    result.append(f"销售总数量: {total_quantity}")
    result.append(f"销售总金额: ¥{total_amount:.2f}")
    result.append(f"热销产品: {hot_products} 个")
    result.append(f"滞销产品: {slow_products} 个")
    
    return '\n'.join(result)

@error_handler_decorator(context="销售报告主函数", reraise=False)
def main():
    """主函数"""
    logger = get_logger("sales_report")
    validator = DataValidator()
    formatter = DataFormatter()
    processor = ReportDataProcessor()
    
    logger.set_context(module="sales_report", operation="main")
    op_index = logger.start_operation("生成销售统计报表")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成销售统计报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--customer_name', type=str, help='客户名称')
        parser.add_argument('--product_name', type=str, help='产品名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        customer_name = args.customer_name
        product_name = args.product_name
        output_format = args.format
        
        # 验证日期格式
        if start_date and not validator.validate_date_format(start_date):
            logger.error("开始日期格式无效", start_date=start_date)
            raise ValueError(f"开始日期格式无效: {start_date}")
            
        if end_date and not validator.validate_date_format(end_date):
            logger.error("结束日期格式无效", end_date=end_date)
            raise ValueError(f"结束日期格式无效: {end_date}")
        
        logger.info("开始生成销售统计报表", 
                   start_date=start_date, 
                   end_date=end_date,
                   customer_name=customer_name,
                   product_name=product_name,
                   output_format=output_format)
        
        # 生成销售统计报表
        report_data = safe_execute(
            generate_sales_report,
            start_date, end_date, customer_name, product_name,
            default_return=[],
            context="生成销售统计报表"
        )
        
        if not report_data:
            logger.warning("未生成任何报表数据")
        
        logger.info(f"销售统计报表生成完成", report_count=len(report_data))
        
        # 输出结果
        if output_format == 'table':
            formatted_output = safe_execute(
                format_table_output,
                report_data,
                default_return="报表格式化失败",
                context="格式化表格输出"
            )
            print(formatted_output)
        else:
            print(json.dumps(report_data, ensure_ascii=False, indent=2))
            
        logger.end_operation(op_index, success=True, report_count=len(report_data))
            
    except Exception as e:
        logger.error(f"销售统计报表生成失败", error=str(e), include_traceback=True)
        logger.end_operation(op_index, success=False, error=str(e))
        
        if 'output_format' in locals() and output_format == 'json':
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()