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
from scripts.query_optimizer import QueryOptimizer
from scripts.cache_manager import cache_report_data, get_cache_manager

def generate_supplier_reconciliation(start_date: Optional[str] = None, 
                                   end_date: Optional[str] = None,
                                   supplier_name: Optional[str] = None,
                                   logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成供应商对账表（使用查询优化引擎和缓存系统）
    
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
        logger.info("开始生成供应商对账表（使用查询优化引擎和缓存系统）")
        
        # 构建查询参数
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'supplier_name': supplier_name
        }
        
        # 使用缓存装饰器，自动处理缓存逻辑
        def data_generator():
            optimizer = QueryOptimizer(logger)
            return optimizer.optimize_supplier_reconciliation_query(params)
        
        # 使用缓存系统，TTL设置为5分钟（300秒）
        reconciliation_data = cache_report_data(
            view_name='supplier_reconciliation',
            params=params,
            data_generator=data_generator,
            ttl=300
        )
        
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
            # 构建标准的响应结构
            result = {
                'success': True,
                'data': reconciliation_data,
                'report_type': 'supplier_reconciliation',
                'generated_at': datetime.now().isoformat(),
                'query_params': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'supplier_name': supplier_name
                }
            }
            
            # 添加统计信息
            if reconciliation_data:
                total_purchase = sum(record.get('total_purchase_amount', 0) for record in reconciliation_data)
                total_payment = sum(record.get('total_payment_amount', 0) for record in reconciliation_data)
                total_balance = sum(record.get('balance', 0) for record in reconciliation_data)
                
                result['statistics'] = {
                    'total_suppliers': len(reconciliation_data),
                    'total_purchase_amount': round(total_purchase, 2),
                    'total_payment_amount': round(total_payment, 2),
                    'total_balance': round(total_balance, 2)
                }
            
            print(json.dumps(result, ensure_ascii=False, indent=2))
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