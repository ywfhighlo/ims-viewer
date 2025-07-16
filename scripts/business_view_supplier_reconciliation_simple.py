#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
供应商对账表业务视图脚本（简化版）
直接查询数据库，不使用复杂的优化器，用于性能测试
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

def generate_supplier_reconciliation_simple(start_date: Optional[str] = None, 
                                          end_date: Optional[str] = None,
                                          supplier_name: Optional[str] = None,
                                          logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成供应商对账表（简化版，直接查询）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        supplier_name: 指定供应商名称，为空则查询所有供应商
        logger: 日志记录器
    
    Returns:
        供应商对账表数据列表
    """
    if logger is None:
        logger = EnhancedLogger("supplier_reconciliation_simple")
    
    try:
        logger.info("开始生成供应商对账表（简化版）")
        start_time = datetime.now()
        
        # 获取数据库连接
        db = get_database_connection()
        
        # 构建日期过滤条件
        date_filter = {}
        if start_date:
            date_filter['$gte'] = start_date
        if end_date:
            date_filter['$lte'] = end_date
        
        # 1. 获取采购数据
        purchase_filter = {}
        if date_filter:
            purchase_filter['inbound_date'] = date_filter
        if supplier_name:
            purchase_filter['supplier_name'] = supplier_name
        
        logger.info("开始查询采购数据")
        purchase_data = list(db['purchase_inbound'].find(purchase_filter, {
            'supplier_name': 1, 
            'inbound_amount': 1, 
            'inbound_date': 1,
            '_id': 0
        }))
        logger.info(f"采购数据查询完成，共 {len(purchase_data)} 条记录")
        
        # 2. 获取付款数据
        payment_filter = {}
        if date_filter:
            payment_filter['payment_date'] = date_filter
        if supplier_name:
            payment_filter['supplier_name'] = supplier_name
        
        logger.info("开始查询付款数据")
        payment_data = list(db['payment_details'].find(payment_filter, {
            'supplier_name': 1, 
            'amount': 1, 
            'payment_date': 1,
            '_id': 0
        }))
        logger.info(f"付款数据查询完成，共 {len(payment_data)} 条记录")
        
        # 3. 汇总数据
        logger.info("开始汇总数据")
        supplier_summary = {}
        
        # 汇总采购数据
        for purchase in purchase_data:
            supplier = purchase.get('supplier_name', '')
            if not supplier:
                continue
                
            if supplier not in supplier_summary:
                supplier_summary[supplier] = {
                    'supplier_name': supplier,
                    'total_purchase_amount': 0,
                    'total_payment_amount': 0,
                    'purchase_count': 0,
                    'payment_count': 0,
                    'latest_purchase_date': None,
                    'latest_payment_date': None
                }
            
            amount = purchase.get('inbound_amount', 0) or 0
            supplier_summary[supplier]['total_purchase_amount'] += amount
            supplier_summary[supplier]['purchase_count'] += 1
            
            # 更新最新采购日期
            purchase_date = purchase.get('inbound_date')
            if purchase_date:
                if (supplier_summary[supplier]['latest_purchase_date'] is None or 
                    purchase_date > supplier_summary[supplier]['latest_purchase_date']):
                    supplier_summary[supplier]['latest_purchase_date'] = purchase_date
        
        # 汇总付款数据
        for payment in payment_data:
            supplier = payment.get('supplier_name', '')
            if not supplier:
                continue
                
            if supplier not in supplier_summary:
                supplier_summary[supplier] = {
                    'supplier_name': supplier,
                    'total_purchase_amount': 0,
                    'total_payment_amount': 0,
                    'purchase_count': 0,
                    'payment_count': 0,
                    'latest_purchase_date': None,
                    'latest_payment_date': None
                }
            
            amount = payment.get('amount', 0) or 0
            supplier_summary[supplier]['total_payment_amount'] += amount
            supplier_summary[supplier]['payment_count'] += 1
            
            # 更新最新付款日期
            payment_date = payment.get('payment_date')
            if payment_date:
                if (supplier_summary[supplier]['latest_payment_date'] is None or 
                    payment_date > supplier_summary[supplier]['latest_payment_date']):
                    supplier_summary[supplier]['latest_payment_date'] = payment_date
        
        # 4. 构建最终结果
        reconciliation_data = []
        for supplier_data in supplier_summary.values():
            balance = supplier_data['total_purchase_amount'] - supplier_data['total_payment_amount']
            
            # 格式化日期
            latest_purchase_str = None
            if supplier_data['latest_purchase_date']:
                if isinstance(supplier_data['latest_purchase_date'], datetime):
                    latest_purchase_str = supplier_data['latest_purchase_date'].strftime('%Y-%m-%d')
                else:
                    latest_purchase_str = str(supplier_data['latest_purchase_date'])[:10]
            
            latest_payment_str = None
            if supplier_data['latest_payment_date']:
                if isinstance(supplier_data['latest_payment_date'], datetime):
                    latest_payment_str = supplier_data['latest_payment_date'].strftime('%Y-%m-%d')
                else:
                    latest_payment_str = str(supplier_data['latest_payment_date'])[:10]
            
            reconciliation_record = {
                'supplier_name': supplier_data['supplier_name'],
                'total_purchase_amount': round(supplier_data['total_purchase_amount'], 2),
                'total_payment_amount': round(supplier_data['total_payment_amount'], 2),
                'balance': round(balance, 2),
                'purchase_count': supplier_data['purchase_count'],
                'payment_count': supplier_data['payment_count'],
                'latest_purchase_date': latest_purchase_str,
                'latest_payment_date': latest_payment_str,
                'status': '正常' if balance >= 0 else '超付',
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            reconciliation_data.append(reconciliation_record)
        
        # 按余额降序排序
        reconciliation_data.sort(key=lambda x: x['balance'], reverse=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"供应商对账表生成完成（简化版），共 {len(reconciliation_data)} 条记录，耗时 {duration:.2f} 秒")
        return reconciliation_data
        
    except Exception as e:
        logger.error(f"生成供应商对账表失败: {str(e)}")
        raise

def main():
    """主函数"""
    logger = EnhancedLogger("supplier_reconciliation_simple")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成供应商对账表（简化版）')
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
        reconciliation_data = generate_supplier_reconciliation_simple(
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
            print("\n=== 供应商对账表（简化版） ===")
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