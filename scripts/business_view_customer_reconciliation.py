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
from scripts.query_optimizer import QueryOptimizer
from scripts.cache_manager import cache_report_data, get_cache_manager

# 数据库连接函数已移至 db_connection 模块

def generate_customer_reconciliation(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_name: Optional[str] = None,
    logger: Optional[EnhancedLogger] = None
) -> List[Dict[str, Any]]:
    """
    生成客户对账单（使用查询优化引擎和缓存系统）
    
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
        logger.info("开始生成客户对账单（使用查询优化引擎和缓存系统）")
        logger.info(f"查询参数: 开始日期={start_date}, 结束日期={end_date}, 客户名称={customer_name}")
        
        # 构建查询参数
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'customer_name': customer_name
        }
        
        # 使用缓存装饰器，自动处理缓存逻辑
        def data_generator():
            optimizer = QueryOptimizer(logger)
            return optimizer.optimize_customer_reconciliation_query(params)
        
        # 使用缓存系统，TTL设置为5分钟（300秒）
        reconciliation_data = cache_report_data(
            view_name='customer_reconciliation',
            params=params,
            data_generator=data_generator,
            ttl=300
        )
        
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
            # 构建标准的响应结构
            result = {
                'success': True,
                'data': reconciliation_data,
                'report_type': 'customer_reconciliation',
                'generated_at': datetime.now().isoformat(),
                'query_params': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'customer_name': customer_name
                }
            }
            
            # 添加统计信息
            if reconciliation_data:
                total_sales = sum(record.get('total_sales_amount', 0) for record in reconciliation_data)
                total_receipt = sum(record.get('total_receipt_amount', 0) for record in reconciliation_data)
                total_balance = sum(record.get('balance', 0) for record in reconciliation_data)
                
                result['statistics'] = {
                    'total_customers': len(reconciliation_data),
                    'total_sales_amount': round(total_sales, 2),
                    'total_receipt_amount': round(total_receipt, 2),
                    'total_balance': round(total_balance, 2)
                }
            
            print(json.dumps(result, ensure_ascii=False, indent=2))
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