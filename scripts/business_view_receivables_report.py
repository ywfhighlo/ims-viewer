#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应收账款统计业务视图脚本
根据销售出库和收款记录生成应收账款统计报表
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from enhanced_logger import EnhancedLogger
from db_connection import get_database_connection

# 数据库连接函数已移至 db_connection 模块

def generate_receivables_report(start_date: Optional[str] = None, 
                              end_date: Optional[str] = None,
                              customer_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    生成应收账款统计报表（优化版本 - 使用聚合查询提升性能）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        customer_name: 客户名称
        
    Returns:
        应收账款统计报表数据列表
    """
    logger = EnhancedLogger("receivables_report")
    
    try:
        db = get_database_connection()
        logger.info("开始生成应收账款报表（优化版本）")
        
        # 获取销售出库数据
        sales_collection = db['sales_outbound']
        # 获取收款记录数据
        receipt_collection = db['receipt_details']
        
        # 构建销售数据聚合管道
        sales_pipeline = []
        
        # 1. 销售数据匹配阶段
        sales_match_conditions = {}
        
        # 日期范围筛选
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            sales_match_conditions['日期'] = date_query
            
        # 客户名称筛选
        if customer_name:
            sales_match_conditions['客户单位'] = {'$regex': customer_name, '$options': 'i'}
            
        if sales_match_conditions:
            sales_pipeline.append({'$match': sales_match_conditions})
            
        # 2. 销售数据分组聚合
        sales_pipeline.append({
            '$group': {
                '_id': '$客户单位',
                'total_sales': {'$sum': '$金额'},
                'sales_count': {'$sum': 1},
                'latest_sale_date': {'$max': '$日期'},
                'earliest_sale_date': {'$min': '$日期'}
            }
        })
        
        # 构建收款数据聚合管道
        receipt_pipeline = []
        
        # 1. 收款数据匹配阶段
        receipt_match_conditions = {}
        
        if customer_name:
            receipt_match_conditions['客户名称'] = {'$regex': customer_name, '$options': 'i'}
        if start_date or end_date:
            receipt_date_query = {}
            if start_date:
                receipt_date_query['$gte'] = start_date
            if end_date:
                receipt_date_query['$lte'] = end_date
            receipt_match_conditions['日期'] = receipt_date_query
            
        if receipt_match_conditions:
            receipt_pipeline.append({'$match': receipt_match_conditions})
            
        # 2. 收款数据分组聚合
        receipt_pipeline.append({
            '$group': {
                '_id': '$客户名称',
                'total_receipts': {'$sum': '$收款金额'},
                'receipt_count': {'$sum': 1},
                'latest_receipt_date': {'$max': '$日期'}
            }
        })
        
        logger.info(f"销售查询条件: {sales_match_conditions}")
        logger.info(f"收款查询条件: {receipt_match_conditions}")
        
        # 执行聚合查询
        sales_summary = {item['_id']: item for item in sales_collection.aggregate(sales_pipeline)}
        receipt_summary = {item['_id']: item for item in receipt_collection.aggregate(receipt_pipeline)}
        
        logger.info(f"聚合查询完成，销售客户数: {len(sales_summary)}，收款客户数: {len(receipt_summary)}")
        
        # 合并销售和收款数据
        all_customers = set(sales_summary.keys()) | set(receipt_summary.keys())
        customer_sales = {}
        for customer in all_customers:
            sales_info = sales_summary.get(customer, {})
            receipt_info = receipt_summary.get(customer, {})
            
            customer_sales[customer] = {
                'total_sales': sales_info.get('total_sales', 0),
                'sales_count': sales_info.get('sales_count', 0),
                'latest_sale_date': sales_info.get('latest_sale_date'),
                'earliest_sale_date': sales_info.get('earliest_sale_date')
            }
        
        # 按客户汇总收款金额
        customer_receipts = {}
        for customer in all_customers:
            receipt_info = receipt_summary.get(customer, {})
            
            customer_receipts[customer] = {
                'total_receipts': receipt_info.get('total_receipts', 0),
                'receipt_count': receipt_info.get('receipt_count', 0),
                'latest_receipt_date': receipt_info.get('latest_receipt_date')
            }
        
        # 合并数据生成应收账款报表
        all_customers = set(customer_sales.keys()) | set(customer_receipts.keys())
        
        report_data = []
        for customer in all_customers:
            sales_info = customer_sales.get(customer, {'total_sales': 0, 'sales_count': 0, 'latest_sale_date': None})
            receipt_info = customer_receipts.get(customer, {'total_receipts': 0, 'receipt_count': 0, 'latest_receipt_date': None})
            
            total_sales = sales_info['total_sales']
            total_receipts = receipt_info['total_receipts']
            balance = total_sales - total_receipts
            
            # 账龄分析（简化版，基于最新销售日期）
            aging_category = "未知"
            if sales_info['latest_sale_date']:
                try:
                    sale_date = datetime.strptime(sales_info['latest_sale_date'], '%Y-%m-%d')
                    current_date = datetime.now()
                    days_diff = (current_date - sale_date).days
                    
                    if days_diff <= 30:
                        aging_category = "30天内"
                    elif days_diff <= 60:
                        aging_category = "31-60天"
                    elif days_diff <= 90:
                        aging_category = "61-90天"
                    else:
                        aging_category = "90天以上"
                except:
                    aging_category = "未知"
            
            # 风险等级评估
            if balance <= 0:
                risk_level = "无风险"
            elif balance <= 10000:
                risk_level = "低风险"
            elif balance <= 50000:
                risk_level = "中风险"
            else:
                risk_level = "高风险"
            
            # 收款率
            collection_rate = (total_receipts / total_sales * 100) if total_sales > 0 else 0
            
            report_item = {
                'customer_name': customer,
                'total_sales_amount': total_sales,
                'total_receipt_amount': total_receipts,
                'receivable_balance': balance,
                'sales_count': sales_info['sales_count'],
                'receipt_count': receipt_info['receipt_count'],
                'collection_rate': collection_rate,
                'latest_sale_date': sales_info['latest_sale_date'],
                'latest_receipt_date': receipt_info['latest_receipt_date'],
                'aging_category': aging_category,
                'risk_level': risk_level,
                'generated_date': datetime.now().isoformat()
            }
            
            report_data.append(report_item)
        
        # 按应收余额降序排序
        report_data.sort(key=lambda x: x['receivable_balance'], reverse=True)
        
        logger.info(f"生成应收账款统计报表完成，共 {len(report_data)} 个客户")
        return report_data
        
    except Exception as e:
        logger.error(f"生成应收账款统计报表失败: {str(e)}")
        raise

def format_table_output(data: List[Dict[str, Any]]) -> str:
    """格式化表格输出"""
    if not data:
        return "暂无应收账款数据"
    
    # 表头
    headers = ['客户名称', '销售金额', '收款金额', '应收余额', '收款率(%)', '销售次数', '收款次数', '账龄', '风险等级', '最近销售', '最近收款']
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for item in data:
        col_widths[0] = max(col_widths[0], len(str(item.get('customer_name', ''))))
        col_widths[1] = max(col_widths[1], len(f"{item.get('total_sales_amount', 0):.2f}"))
        col_widths[2] = max(col_widths[2], len(f"{item.get('total_receipt_amount', 0):.2f}"))
        col_widths[3] = max(col_widths[3], len(f"{item.get('receivable_balance', 0):.2f}"))
        col_widths[4] = max(col_widths[4], len(f"{item.get('collection_rate', 0):.1f}"))
        col_widths[5] = max(col_widths[5], len(str(item.get('sales_count', ''))))
        col_widths[6] = max(col_widths[6], len(str(item.get('receipt_count', ''))))
        col_widths[7] = max(col_widths[7], len(str(item.get('aging_category', ''))))
        col_widths[8] = max(col_widths[8], len(str(item.get('risk_level', ''))))
        col_widths[9] = max(col_widths[9], len(str(item.get('latest_sale_date', ''))))
        col_widths[10] = max(col_widths[10], len(str(item.get('latest_receipt_date', ''))))
    
    # 构建表格
    result = []
    
    # 表头
    header_row = '|'.join(h.ljust(w) for h, w in zip(headers, col_widths))
    result.append(header_row)
    result.append('-' * len(header_row))
    
    # 数据行
    for item in data:
        row = [
            str(item.get('customer_name', '')).ljust(col_widths[0]),
            f"{item.get('total_sales_amount', 0):.2f}".ljust(col_widths[1]),
            f"{item.get('total_receipt_amount', 0):.2f}".ljust(col_widths[2]),
            f"{item.get('receivable_balance', 0):.2f}".ljust(col_widths[3]),
            f"{item.get('collection_rate', 0):.1f}".ljust(col_widths[4]),
            str(item.get('sales_count', '')).ljust(col_widths[5]),
            str(item.get('receipt_count', '')).ljust(col_widths[6]),
            str(item.get('aging_category', '')).ljust(col_widths[7]),
            str(item.get('risk_level', '')).ljust(col_widths[8]),
            str(item.get('latest_sale_date', '')).ljust(col_widths[9]),
            str(item.get('latest_receipt_date', '')).ljust(col_widths[10])
        ]
        result.append('|'.join(row))
    
    # 统计信息
    total_customers = len(data)
    total_sales = sum(item.get('total_sales_amount', 0) for item in data)
    total_receipts = sum(item.get('total_receipt_amount', 0) for item in data)
    total_receivables = sum(item.get('receivable_balance', 0) for item in data)
    high_risk_customers = sum(1 for item in data if item.get('risk_level') == '高风险')
    overdue_customers = sum(1 for item in data if item.get('aging_category') == '90天以上')
    
    result.append('')
    result.append(f"总计: {total_customers} 个客户")
    result.append(f"销售总金额: ¥{total_sales:.2f}")
    result.append(f"收款总金额: ¥{total_receipts:.2f}")
    result.append(f"应收账款总额: ¥{total_receivables:.2f}")
    result.append(f"高风险客户: {high_risk_customers} 个")
    result.append(f"超期客户: {overdue_customers} 个")
    
    return '\n'.join(result)

def main():
    """主函数"""
    logger = EnhancedLogger("receivables_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成应收账款统计报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--customer_name', type=str, help='客户名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        customer_name = args.customer_name
        output_format = args.format
        
        # 生成应收账款统计报表
        report_data = generate_receivables_report(start_date, end_date, customer_name)
        
        # 输出结果
        if output_format == 'table':
            print(format_table_output(report_data))
        else:
            print(json.dumps(report_data, ensure_ascii=False, indent=2))
            
    except Exception as e:
        logger.error(f"应收账款统计报表生成失败: {str(e)}")
        if output_format == 'json':
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()