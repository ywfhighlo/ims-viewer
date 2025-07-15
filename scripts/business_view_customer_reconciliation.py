#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户对账单业务视图脚本
根据客户信息、销售出库记录和收款记录生成客户对账单
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.db_connection import get_database_connection

# 数据库连接函数已移至 db_connection 模块

def generate_customer_reconciliation(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_name: Optional[str] = None,
    logger: Optional[EnhancedLogger] = None
) -> List[Dict[str, Any]]:
    """
    生成客户对账单（优化版本 - 使用聚合查询提升性能）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        customer_name: 指定客户名称
        logger: 日志记录器
    
    Returns:
        客户对账单数据列表
    """
    if logger is None:
        logger = EnhancedLogger("customer_reconciliation")
    
    try:
        logger.info("开始生成客户对账单（优化版本）")
        logger.info(f"查询参数: 开始日期={start_date}, 结束日期={end_date}, 客户名称={customer_name}")
        
        # 获取数据库连接
        db = get_database_connection()
        
        # 构建日期过滤条件
        date_filter = {}
        if start_date:
            date_filter['$gte'] = start_date
        if end_date:
            date_filter['$lte'] = end_date
        
        # 构建客户过滤条件
        customer_filter = {}
        if customer_name:
            customer_filter = {'customer_name': customer_name}
        
        # 1. 获取所有客户基础信息
        customers_collection = db['customers']
        customers_query = customer_filter.copy()
        customers = list(customers_collection.find(customers_query, {'_id': 0}))
        logger.info(f"找到 {len(customers)} 个客户")
        
        # 提取客户名称列表
        customer_names = [customer.get('customer_name', '') for customer in customers if customer.get('customer_name')]
        
        if not customer_names:
            logger.info("没有找到有效的客户名称")
            return []
        
        # 2. 使用聚合查询批量获取销售数据
        sales_pipeline = [
            {
                '$match': {
                    'customer_name': {'$in': customer_names}
                }
            }
        ]
        
        # 添加日期过滤
        if date_filter:
            sales_pipeline[0]['$match']['outbound_date'] = date_filter
        
        # 聚合销售数据
        sales_pipeline.extend([
            {
                '$group': {
                    '_id': '$customer_name',
                    'total_sales_amount': {'$sum': '$outbound_amount'},
                    'sales_count': {'$sum': 1},
                    'latest_sales_date': {'$max': '$outbound_date'}
                }
            }
        ])
        
        sales_outbound = db['sales_outbound']
        sales_aggregated = list(sales_outbound.aggregate(sales_pipeline))
        sales_dict = {item['_id']: item for item in sales_aggregated}
        
        # 3. 使用聚合查询批量获取收款数据
        receipt_pipeline = [
            {
                '$match': {
                    'customer_name': {'$in': customer_names}
                }
            }
        ]
        
        # 添加日期过滤
        if date_filter:
            receipt_pipeline[0]['$match']['receipt_date'] = date_filter
        
        # 聚合收款数据
        receipt_pipeline.extend([
            {
                '$group': {
                    '_id': '$customer_name',
                    'total_receipt_amount': {'$sum': '$amount'},
                    'receipt_count': {'$sum': 1},
                    'latest_receipt_date': {'$max': '$receipt_date'}
                }
            }
        ])
        
        receipt_details = db['receipt_details']
        receipt_aggregated = list(receipt_details.aggregate(receipt_pipeline))
        receipt_dict = {item['_id']: item for item in receipt_aggregated}
        
        logger.info(f"聚合查询完成: 销售数据 {len(sales_dict)} 条, 收款数据 {len(receipt_dict)} 条")
        
        # 4. 构建对账单数据
        reconciliation_data = []
        
        for customer in customers:
            customer_name_key = customer.get('customer_name', '')
            if not customer_name_key:
                continue
            
            # 获取聚合后的销售数据
            sales_data = sales_dict.get(customer_name_key, {})
            total_sales_amount = sales_data.get('total_sales_amount', 0) or 0
            sales_count = sales_data.get('sales_count', 0) or 0
            latest_sales_date = sales_data.get('latest_sales_date')
            
            # 获取聚合后的收款数据
            receipt_data = receipt_dict.get(customer_name_key, {})
            total_receipt_amount = receipt_data.get('total_receipt_amount', 0) or 0
            receipt_count = receipt_data.get('receipt_count', 0) or 0
            latest_receipt_date = receipt_data.get('latest_receipt_date')
            
            # 计算应收账款余额
            balance = total_sales_amount - total_receipt_amount
            
            # 处理日期字段，确保可以JSON序列化
            latest_sales_str = None
            if latest_sales_date:
                if isinstance(latest_sales_date, datetime):
                    latest_sales_str = latest_sales_date.strftime('%Y-%m-%d')
                else:
                    latest_sales_str = str(latest_sales_date)[:10]
            
            latest_receipt_str = None
            if latest_receipt_date:
                if isinstance(latest_receipt_date, datetime):
                    latest_receipt_str = latest_receipt_date.strftime('%Y-%m-%d')
                else:
                    latest_receipt_str = str(latest_receipt_date)[:10]
            
            reconciliation_record = {
                'customer_name': customer_name_key,
                'customer_credit_code': customer.get('credit_code', ''),
                'customer_contact': customer.get('contact_person', ''),
                'customer_phone': customer.get('phone', ''),
                'customer_address': customer.get('address', ''),
                'total_sales_amount': round(total_sales_amount, 2),
                'total_receipt_amount': round(total_receipt_amount, 2),
                'balance': round(balance, 2),
                'sales_count': sales_count,
                'receipt_count': receipt_count,
                'latest_sales_date': latest_sales_str,
                'latest_receipt_date': latest_receipt_str,
                'status': '正常' if balance >= 0 else '超收',
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            reconciliation_data.append(reconciliation_record)
        
        # 按余额降序排序
        reconciliation_data.sort(key=lambda x: x['balance'], reverse=True)
        
        logger.info(f"客户对账单生成完成，共 {len(reconciliation_data)} 条记录")
        return reconciliation_data
        
    except Exception as e:
        logger.error(f"生成客户对账单失败: {str(e)}")
        raise

def main():
    """主函数"""
    logger = EnhancedLogger("customer_reconciliation")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成客户对账单')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--customer_name', type=str, help='客户名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        customer_name = args.customer_name
        output_format = args.format
        
        # 生成对账单
        reconciliation_data = generate_customer_reconciliation(
            start_date=start_date,
            end_date=end_date,
            customer_name=customer_name,
            logger=logger
        )
        
        # 输出结果
        if output_format.lower() == 'json':
            print(json.dumps(reconciliation_data, ensure_ascii=False, indent=2))
        else:
            # 表格格式输出
            print("\n=== 客户对账单 ===")
            print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if start_date or end_date:
                print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
            if customer_name:
                print(f"指定客户: {customer_name}")
            print("-" * 120)
            print(f"{'客户名称':<20} {'销售金额':<12} {'收款金额':<12} {'应收余额':<12} {'销售笔数':<8} {'收款笔数':<8} {'状态':<8}")
            print("-" * 120)
            
            total_sales = 0
            total_receipt = 0
            total_balance = 0
            
            for record in reconciliation_data:
                print(f"{record['customer_name']:<20} "
                      f"{record['total_sales_amount']:<12.2f} "
                      f"{record['total_receipt_amount']:<12.2f} "
                      f"{record['balance']:<12.2f} "
                      f"{record['sales_count']:<8} "
                      f"{record['receipt_count']:<8} "
                      f"{record['status']:<8}")
                
                total_sales += record['total_sales_amount']
                total_receipt += record['total_receipt_amount']
                total_balance += record['balance']
            
            print("-" * 120)
            print(f"{'合计':<20} {total_sales:<12.2f} {total_receipt:<12.2f} {total_balance:<12.2f}")
            print(f"\n共 {len(reconciliation_data)} 个客户")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()