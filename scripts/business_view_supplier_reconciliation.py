#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
供应商对账表业务视图脚本
汇总供应商的采购、付款信息，计算应付账款余额
"""

import sys
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.db_connection import get_database_connection

def generate_supplier_reconciliation(start_date: Optional[str] = None, 
                                   end_date: Optional[str] = None,
                                   supplier_name: Optional[str] = None,
                                   logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成供应商对账表（优化版本 - 使用聚合查询提升性能）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        supplier_name: 指定供应商名称，为空则查询所有供应商
        logger: 日志记录器
    
    Returns:
        供应商对账表数据列表
    """
    if logger is None:
        logger = EnhancedLogger("supplier_reconciliation")
    
    try:
        db = get_database_connection()
        logger.info("开始生成供应商对账表（优化版本）")
        
        # 构建日期过滤条件
        date_filter = {}
        if start_date:
            date_filter['$gte'] = start_date
        if end_date:
            date_filter['$lte'] = end_date
        
        # 构建供应商过滤条件
        supplier_filter = {}
        if supplier_name:
            supplier_filter = {'supplier_name': supplier_name}
        
        # 1. 获取所有供应商基础信息
        suppliers_collection = db['suppliers']
        suppliers_query = supplier_filter.copy()
        suppliers = list(suppliers_collection.find(suppliers_query, {'_id': 0}))
        logger.info(f"找到 {len(suppliers)} 个供应商")
        
        # 提取供应商名称列表
        supplier_names = [supplier.get('supplier_name', '') for supplier in suppliers if supplier.get('supplier_name')]
        
        if not supplier_names:
            logger.info("没有找到有效的供应商名称")
            return []
        
        # 2. 使用聚合查询批量获取采购数据
        purchase_pipeline = [
            {
                '$match': {
                    'supplier_name': {'$in': supplier_names}
                }
            }
        ]
        
        # 添加日期过滤
        if date_filter:
            purchase_pipeline[0]['$match']['inbound_date'] = date_filter
        
        # 聚合采购数据
        purchase_pipeline.extend([
            {
                '$group': {
                    '_id': '$supplier_name',
                    'total_purchase_amount': {'$sum': '$amount'},
                    'purchase_count': {'$sum': 1},
                    'latest_purchase_date': {'$max': '$inbound_date'}
                }
            }
        ])
        
        purchase_inbound = db['purchase_inbound']
        purchase_aggregated = list(purchase_inbound.aggregate(purchase_pipeline))
        purchase_dict = {item['_id']: item for item in purchase_aggregated}
        
        # 3. 使用聚合查询批量获取付款数据
        payment_pipeline = [
            {
                '$match': {
                    'supplier_name': {'$in': supplier_names}
                }
            }
        ]
        
        # 添加日期过滤
        if date_filter:
            payment_pipeline[0]['$match']['payment_date'] = date_filter
        
        # 聚合付款数据
        payment_pipeline.extend([
            {
                '$group': {
                    '_id': '$supplier_name',
                    'total_payment_amount': {'$sum': '$amount'},
                    'payment_count': {'$sum': 1},
                    'latest_payment_date': {'$max': '$payment_date'}
                }
            }
        ])
        
        payment_details = db['payment_details']
        payment_aggregated = list(payment_details.aggregate(payment_pipeline))
        payment_dict = {item['_id']: item for item in payment_aggregated}
        
        logger.info(f"聚合查询完成: 采购数据 {len(purchase_dict)} 条, 付款数据 {len(payment_dict)} 条")
        
        # 4. 构建对账表数据
        reconciliation_data = []
        
        for supplier in suppliers:
            supplier_name_key = supplier.get('supplier_name', '')
            if not supplier_name_key:
                continue
            
            # 获取聚合后的采购数据
            purchase_data = purchase_dict.get(supplier_name_key, {})
            total_purchase_amount = purchase_data.get('total_purchase_amount', 0) or 0
            purchase_count = purchase_data.get('purchase_count', 0) or 0
            latest_purchase_date = purchase_data.get('latest_purchase_date')
            
            # 获取聚合后的付款数据
            payment_data = payment_dict.get(supplier_name_key, {})
            total_payment_amount = payment_data.get('total_payment_amount', 0) or 0
            payment_count = payment_data.get('payment_count', 0) or 0
            latest_payment_date = payment_data.get('latest_payment_date')
            
            # 计算应付账款余额
            balance = total_purchase_amount - total_payment_amount
            
            # 处理日期字段，确保可以JSON序列化
            latest_purchase_str = None
            if latest_purchase_date:
                if isinstance(latest_purchase_date, datetime):
                    latest_purchase_str = latest_purchase_date.strftime('%Y-%m-%d')
                else:
                    latest_purchase_str = str(latest_purchase_date)[:10]
            
            latest_payment_str = None
            if latest_payment_date:
                if isinstance(latest_payment_date, datetime):
                    latest_payment_str = latest_payment_date.strftime('%Y-%m-%d')
                else:
                    latest_payment_str = str(latest_payment_date)[:10]
            
            reconciliation_record = {
                'supplier_name': supplier_name_key,
                'supplier_credit_code': supplier.get('credit_code', ''),
                'supplier_contact': supplier.get('contact_person', ''),
                'supplier_phone': supplier.get('phone', ''),
                'total_purchase_amount': round(total_purchase_amount, 2),
                'total_payment_amount': round(total_payment_amount, 2),
                'balance': round(balance, 2),
                'purchase_count': purchase_count,
                'payment_count': payment_count,
                'latest_purchase_date': latest_purchase_str,
                'latest_payment_date': latest_payment_str,
                'status': '正常' if balance >= 0 else '超付',
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            reconciliation_data.append(reconciliation_record)
        
        # 按余额降序排序
        reconciliation_data.sort(key=lambda x: x['balance'], reverse=True)
        
        logger.info(f"供应商对账表生成完成，共 {len(reconciliation_data)} 条记录")
        return reconciliation_data
        
    except Exception as e:
        logger.error(f"生成供应商对账表失败: {str(e)}")
        raise

def main():
    """主函数"""
    logger = EnhancedLogger("supplier_reconciliation")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成供应商对账表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--supplier_name', type=str, help='供应商名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        supplier_name = args.supplier_name
        output_format = args.format
        
        # 生成对账表
        reconciliation_data = generate_supplier_reconciliation(
            start_date=start_date,
            end_date=end_date,
            supplier_name=supplier_name,
            logger=logger
        )
        
        # 输出结果
        if output_format.lower() == 'json':
            print(json.dumps(reconciliation_data, ensure_ascii=False, indent=2))
        else:
            # 表格格式输出
            print("\n=== 供应商对账表 ===")
            print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if start_date or end_date:
                print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
            if supplier_name:
                print(f"指定供应商: {supplier_name}")
            print("-" * 120)
            print(f"{'供应商名称':<20} {'采购金额':<12} {'付款金额':<12} {'应付余额':<12} {'采购笔数':<8} {'付款笔数':<8} {'状态':<8}")
            print("-" * 120)
            
            total_purchase = 0
            total_payment = 0
            total_balance = 0
            
            for record in reconciliation_data:
                print(f"{record['supplier_name']:<20} "
                      f"{record['total_purchase_amount']:<12.2f} "
                      f"{record['total_payment_amount']:<12.2f} "
                      f"{record['balance']:<12.2f} "
                      f"{record['purchase_count']:<8} "
                      f"{record['payment_count']:<8} "
                      f"{record['status']:<8}")
                
                total_purchase += record['total_purchase_amount']
                total_payment += record['total_payment_amount']
                total_balance += record['balance']
            
            print("-" * 120)
            print(f"{'合计':<20} {total_purchase:<12.2f} {total_payment:<12.2f} {total_balance:<12.2f}")
            print(f"\n共 {len(reconciliation_data)} 个供应商")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()