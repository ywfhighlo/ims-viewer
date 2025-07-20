#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应付账款报表业务视图脚本
根据采购入库和付款记录生成应付账款报表，包括供应商应付余额、账龄分析等
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.db_connection import get_database_connection
from scripts.query_optimizer import QueryOptimizer
from scripts.cache_manager import cache_report_data, get_cache_manager

def generate_payables_report(start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           supplier_name: Optional[str] = None,
                           logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成应付账款报表（使用查询优化引擎和缓存系统）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        supplier_name: 指定供应商名称，为空则查询所有供应商
        logger: 日志记录器
    
    Returns:
        应付账款报表数据列表
    """
    if logger is None:
        logger = EnhancedLogger("payables_report")
    
    try:
        logger.info("开始生成应付账款报表（使用查询优化引擎和缓存系统）")
        
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
        payables_data = cache_report_data(
            view_name='payables_report',
            params=params,
            data_generator=data_generator,
            ttl=300
        )
        
        # 转换为应付账款报表格式
        report_data = []
        for item in payables_data:
            # 计算账龄
            age_days = calculate_age_days(item.get('latest_purchase_date'))
            age_range = get_age_range(age_days)
            
            report_record = {
                'supplier_name': item.get('supplier_name', ''),
                'supplier_credit_code': item.get('supplier_credit_code', ''),
                'supplier_contact': item.get('supplier_contact', ''),
                'supplier_phone': item.get('supplier_phone', ''),
                'total_purchase_amount': item.get('total_purchase_amount', 0),
                'total_payment_amount': item.get('total_payment_amount', 0),
                'payable_balance': item.get('balance', 0),
                'purchase_count': item.get('purchase_count', 0),
                'payment_count': item.get('payment_count', 0),
                'latest_purchase_date': item.get('latest_purchase_date'),
                'latest_payment_date': item.get('latest_payment_date'),
                'age_days': age_days,
                'age_range': age_range,
                'priority_level': get_priority_level(item.get('balance', 0), age_days),
                'generated_date': datetime.now().isoformat()
            }
            report_data.append(report_record)
        
        # 按应付余额降序排序
        report_data.sort(key=lambda x: x['payable_balance'], reverse=True)
        
        logger.info(f"应付账款报表生成完成，共 {len(report_data)} 条记录")
        return report_data
        
    except Exception as e:
        logger.error(f"生成应付账款报表失败: {str(e)}")
        raise

def calculate_age_days(latest_purchase_date: Optional[str]) -> int:
    """
    计算账龄天数
    
    Args:
        latest_purchase_date: 最近采购日期
        
    Returns:
        账龄天数
    """
    if not latest_purchase_date:
        return 0
    
    try:
        if isinstance(latest_purchase_date, str):
            if 'T' in latest_purchase_date:
                purchase_date = datetime.fromisoformat(latest_purchase_date.replace('T', ' ').replace('Z', ''))
            else:
                purchase_date = datetime.strptime(latest_purchase_date, '%Y-%m-%d')
        else:
            return 0
        
        today = datetime.now()
        age_days = (today - purchase_date).days
        return max(0, age_days)
        
    except (ValueError, TypeError):
        return 0

def get_age_range(age_days: int) -> str:
    """
    获取账龄区间
    
    Args:
        age_days: 账龄天数
        
    Returns:
        账龄区间描述
    """
    if age_days <= 30:
        return '30天以内'
    elif age_days <= 60:
        return '31-60天'
    elif age_days <= 90:
        return '61-90天'
    elif age_days <= 180:
        return '91-180天'
    else:
        return '180天以上'

def get_priority_level(balance: float, age_days: int) -> str:
    """
    获取付款优先级
    
    Args:
        balance: 应付余额
        age_days: 账龄天数
        
    Returns:
        优先级等级
    """
    if balance <= 0:
        return '无需付款'
    elif age_days > 90:
        return '紧急'
    elif age_days > 60:
        return '高优先级'
    elif age_days > 30:
        return '中优先级'
    else:
        return '低优先级'

def generate_payables_summary(start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            logger: Optional[EnhancedLogger] = None) -> Dict[str, Any]:
    """
    生成应付账款汇总统计
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        logger: 日志记录器
        
    Returns:
        应付账款汇总统计数据
    """
    if logger is None:
        logger = EnhancedLogger("payables_summary")
    
    try:
        logger.info("开始生成应付账款汇总统计")
        
        # 获取详细应付账款数据
        payables_data = generate_payables_report(start_date, end_date, logger=logger)
        
        if not payables_data:
            return {
                'total_payables': 0,
                'supplier_count': 0,
                'overdue_amount': 0,
                'overdue_count': 0,
                'age_distribution': {},
                'priority_distribution': {},
                'top_payables': []
            }
        
        # 计算汇总统计
        total_payables = sum(item.get('payable_balance', 0) for item in payables_data)
        supplier_count = len([item for item in payables_data if item.get('payable_balance', 0) > 0])
        overdue_amount = sum(item.get('payable_balance', 0) for item in payables_data if item.get('age_days', 0) > 30)
        overdue_count = len([item for item in payables_data if item.get('age_days', 0) > 30 and item.get('payable_balance', 0) > 0])
        
        # 账龄分布统计
        age_distribution = {}
        for item in payables_data:
            if item.get('payable_balance', 0) > 0:
                age_range = item.get('age_range', '未知')
                age_distribution[age_range] = age_distribution.get(age_range, 0) + item.get('payable_balance', 0)
        
        # 优先级分布统计
        priority_distribution = {}
        for item in payables_data:
            if item.get('payable_balance', 0) > 0:
                priority_level = item.get('priority_level', '未知')
                priority_distribution[priority_level] = priority_distribution.get(priority_level, 0) + item.get('payable_balance', 0)
        
        # 应付账款排名（前10名）
        top_payables = sorted([item for item in payables_data if item.get('payable_balance', 0) > 0],
                             key=lambda x: x.get('payable_balance', 0),
                             reverse=True)[:10]
        
        summary = {
            'total_payables': round(total_payables, 2),
            'supplier_count': supplier_count,
            'overdue_amount': round(overdue_amount, 2),
            'overdue_count': overdue_count,
            'overdue_rate': round((overdue_amount / total_payables * 100), 2) if total_payables > 0 else 0,
            'age_distribution': {k: round(v, 2) for k, v in age_distribution.items()},
            'priority_distribution': {k: round(v, 2) for k, v in priority_distribution.items()},
            'top_payables': [{
                'supplier_name': item.get('supplier_name', ''),
                'payable_balance': item.get('payable_balance', 0),
                'age_days': item.get('age_days', 0),
                'age_range': item.get('age_range', ''),
                'priority_level': item.get('priority_level', '')
            } for item in top_payables],
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"应付账款汇总统计生成完成，总应付: {total_payables}, 供应商数: {supplier_count}")
        return summary
        
    except Exception as e:
        logger.error(f"生成应付账款汇总统计失败: {str(e)}")
        raise

def main():
    """主函数"""
    logger = EnhancedLogger("payables_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成应付账款报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--supplier_name', type=str, help='供应商名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table', 'summary'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        supplier_name = args.supplier_name
        output_format = args.format
        
        # 根据格式生成不同类型的报表
        if output_format == 'summary':
            # 生成汇总统计
            summary_data = generate_payables_summary(
                start_date=start_date,
                end_date=end_date,
                logger=logger
            )
            print(json.dumps(summary_data, ensure_ascii=False, indent=2))
        else:
            # 生成详细报表
            payables_data = generate_payables_report(
                start_date=start_date,
                end_date=end_date,
                supplier_name=supplier_name,
                logger=logger
            )
            
            # 输出结果
            if output_format == 'json':
                # 构建标准的响应结构
                result = {
                    'success': True,
                    'data': payables_data,
                    'report_type': 'payables_report',
                    'generated_at': datetime.now().isoformat(),
                    'query_params': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'supplier_name': supplier_name
                    }
                }
                
                # 添加统计信息
                if payables_data:
                    total_payables = sum(record.get('payable_balance', 0) for record in payables_data)
                    total_purchases = sum(record.get('purchase_amount', 0) for record in payables_data)
                    total_payments = sum(record.get('payment_amount', 0) for record in payables_data)
                    
                    result['statistics'] = {
                        'total_suppliers': len(payables_data),
                        'total_payables': round(total_payables, 2),
                        'total_purchase_amount': round(total_purchases, 2),
                        'total_payment_amount': round(total_payments, 2)
                    }
                
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 表格格式输出
                print("\n=== 应付账款报表 ===")
                print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if start_date or end_date:
                    print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
                if supplier_name:
                    print(f"指定供应商: {supplier_name}")
                print("-" * 140)
                print(f"{'供应商名称':<25} {'应付余额':<12} {'采购金额':<12} {'付款金额':<12} {'账龄天数':<10} {'账龄区间':<12} {'优先级':<10}")
                print("-" * 140)
                
                total_payables = 0
                
                for record in payables_data:
                    # 显示所有有交易记录的供应商（包括已付清的）
                    if record.get('total_purchase_amount', 0) > 0:
                        print(f"{record.get('supplier_name', ''):<25} "
                              f"{record.get('payable_balance', 0):<12.2f} "
                              f"{record.get('total_purchase_amount', 0):<12.2f} "
                              f"{record.get('total_payment_amount', 0):<12.2f} "
                              f"{record.get('age_days', 0):<10} "
                              f"{record.get('age_range', ''):<12} "
                              f"{record.get('priority_level', ''):<10}")
                        
                        total_payables += record.get('payable_balance', 0)
                
                print("-" * 140)
                print(f"{'合计':<25} {total_payables:<12.2f}")
                print(f"\n共 {len([r for r in payables_data if r.get('payable_balance', 0) > 0])} 个供应商有应付账款")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()