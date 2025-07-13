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
    生成库存盘点报表
    
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
        
        # 获取库存统计数据
        inventory_collection = db['inventory_stats']
        
        # 构建查询条件
        query = {}
        if product_name:
            query['进货物料名称'] = {'$regex': product_name, '$options': 'i'}
            
        logger.info(f"查询条件: {query}")
        
        # 查询库存数据
        inventory_data = list(inventory_collection.find(query, {'_id': 0}))
        logger.info(f"查询到 {len(inventory_data)} 条库存记录")
        
        # 处理库存数据
        report_data = []
        for item in inventory_data:
            try:
                # 计算库存价值
                current_stock = float(item.get('当前库存', 0) or 0)
                unit_price = float(item.get('单价', 0) or 0)
                stock_value = current_stock * unit_price
                
                # 库存状态判断
                if current_stock <= 0:
                    stock_status = "缺货"
                elif current_stock <= 10:  # 可配置的低库存阈值
                    stock_status = "低库存"
                else:
                    stock_status = "正常"
                
                report_item = {
                    'product_code': item.get('进货物料编码', ''),
                    'product_name': item.get('进货物料名称', ''),
                    'product_model': item.get('进货物料型号', ''),
                    'unit': item.get('单位', ''),
                    'current_stock': current_stock,
                    'unit_price': unit_price,
                    'stock_value': stock_value,
                    'stock_status': stock_status,
                    'supplier_name': item.get('供应商名称', ''),
                    'last_update_date': item.get('最后更新日期', ''),
                    'generated_date': datetime.now().isoformat()
                }
                
                report_data.append(report_item)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"处理库存记录时出错: {e}, 记录: {item}")
                continue
        
        logger.info(f"生成库存盘点报表完成，共 {len(report_data)} 条记录")
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
            args=(start_date, end_date, product_name),
            default_return=[],
            context="生成库存盘点报表"
        )
        
        if not report_data:
            logger.warning("未生成任何报表数据")
        
        logger.info(f"库存盘点报表生成完成", record_count=len(report_data))
        
        # 输出结果
        if output_format == 'table':
            formatted_output = safe_execute(
                format_table_output,
                args=(report_data,),
                default_return="报表格式化失败",
                context="格式化表格输出"
            )
            print(formatted_output)
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