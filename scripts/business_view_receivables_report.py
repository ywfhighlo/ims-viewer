#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应收账款报表业务视图脚本
根据销售出库和收款记录生成应收账款报表，包括客户应收余额、账龄分析等
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

def generate_receivables_report(start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              customer_name: Optional[str] = None,
                              logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成应收账款报表（使用查询优化引擎和缓存系统）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        customer_name: 指定客户名称，为空则查询所有客户
        logger: 日志记录器
    
    Returns:
        应收账款报表数据列表
    """
    if logger is None:
        logger = EnhancedLogger("receivables_report")
    
    try:
        logger.info("开始生成应收账款报表（使用查询优化引擎和缓存系统）")
        
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
        receivables_data = cache_report_data(
            view_name='receivables_report',
            params=params,
            data_generator=data_generator,
            ttl=300
        )
        
        # 转换为应收账款报表格式
        report_data = []
        for item in receivables_data:
            # 计算账龄
            age_days = calculate_age_days(item.get('latest_sales_date'))
            age_range = get_age_range(age_days)
            
            report_record = {
                'customer_name': item.get('customer_name', ''),
                'customer_credit_code': item.get('customer_credit_code', ''),
                'customer_contact': item.get('customer_contact', ''),
                'customer_phone': item.get('customer_phone', ''),
                'customer_address': item.get('customer_address', ''),
                'total_sales_amount': item.get('total_sales_amount', 0),
                'total_receipt_amount': item.get('total_receipt_amount', 0),
                'receivable_balance': item.get('balance', 0),
                'sales_count': item.get('sales_count', 0),
                'receipt_count': item.get('receipt_count', 0),
                'latest_sales_date': item.get('latest_sales_date'),
                'latest_receipt_date': item.get('latest_receipt_date'),
                'age_days': age_days,
                'age_range': age_range,
                'risk_level': get_risk_level(item.get('balance', 0), age_days),
                'generated_date': datetime.now().isoformat()
            }
            report_data.append(report_record)
        
        # 按应收余额降序排序
        report_data.sort(key=lambda x: x['receivable_balance'], reverse=True)
        
        logger.info(f"应收账款报表生成完成，共 {len(report_data)} 条记录")
        return report_data
        
    except Exception as e:
        logger.error(f"生成应收账款报表失败: {str(e)}")
        raise

def calculate_age_days(latest_sales_date: Optional[str]) -> int:
    """
    计算账龄天数
    
    Args:
        latest_sales_date: 最近销售日期
        
    Returns:
        账龄天数
    """
    if not latest_sales_date:
        return 0
    
    try:
        if isinstance(latest_sales_date, str):
            if 'T' in latest_sales_date:
                sales_date = datetime.fromisoformat(latest_sales_date.replace('T', ' ').replace('Z', ''))
            else:
                sales_date = datetime.strptime(latest_sales_date, '%Y-%m-%d')
        else:
            return 0
        
        today = datetime.now()
        age_days = (today - sales_date).days
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

def get_risk_level(balance: float, age_days: int) -> str:
    """
    获取风险等级
    
    Args:
        balance: 应收余额
        age_days: 账龄天数
        
    Returns:
        风险等级
    """
    if balance <= 0:
        return '无风险'
    elif age_days <= 30:
        return '低风险'
    elif age_days <= 90:
        return '中风险'
    else:
        return '高风险'

def generate_receivables_summary(start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               logger: Optional[EnhancedLogger] = None) -> Dict[str, Any]:
    """
    生成应收账款汇总统计
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        logger: 日志记录器
        
    Returns:
        应收账款汇总统计数据
    """
    if logger is None:
        logger = EnhancedLogger("receivables_summary")
    
    try:
        logger.info("开始生成应收账款汇总统计")
        
        # 获取详细应收账款数据
        receivables_data = generate_receivables_report(start_date, end_date, logger=logger)
        
        if not receivables_data:
            return {
                'total_receivables': 0,
                'customer_count': 0,
                'overdue_amount': 0,
                'overdue_count': 0,
                'age_distribution': {},
                'risk_distribution': {},
                'top_receivables': []
            }
        
        # 计算汇总统计
        total_receivables = sum(item.get('receivable_balance', 0) for item in receivables_data)
        customer_count = len([item for item in receivables_data if item.get('receivable_balance', 0) > 0])
        overdue_amount = sum(item.get('receivable_balance', 0) for item in receivables_data if item.get('age_days', 0) > 30)
        overdue_count = len([item for item in receivables_data if item.get('age_days', 0) > 30 and item.get('receivable_balance', 0) > 0])
        
        # 账龄分布统计
        age_distribution = {}
        for item in receivables_data:
            if item.get('receivable_balance', 0) > 0:
                age_range = item.get('age_range', '未知')
                age_distribution[age_range] = age_distribution.get(age_range, 0) + item.get('receivable_balance', 0)
        
        # 风险分布统计
        risk_distribution = {}
        for item in receivables_data:
            if item.get('receivable_balance', 0) > 0:
                risk_level = item.get('risk_level', '未知')
                risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + item.get('receivable_balance', 0)
        
        # 应收账款排名（前10名）
        top_receivables = sorted([item for item in receivables_data if item.get('receivable_balance', 0) > 0],
                                key=lambda x: x.get('receivable_balance', 0),
                                reverse=True)[:10]
        
        summary = {
            'total_receivables': round(total_receivables, 2),
            'customer_count': customer_count,
            'overdue_amount': round(overdue_amount, 2),
            'overdue_count': overdue_count,
            'overdue_rate': round((overdue_amount / total_receivables * 100), 2) if total_receivables > 0 else 0,
            'age_distribution': {k: round(v, 2) for k, v in age_distribution.items()},
            'risk_distribution': {k: round(v, 2) for k, v in risk_distribution.items()},
            'top_receivables': [{
                'customer_name': item.get('customer_name', ''),
                'receivable_balance': item.get('receivable_balance', 0),
                'age_days': item.get('age_days', 0),
                'age_range': item.get('age_range', ''),
                'risk_level': item.get('risk_level', '')
            } for item in top_receivables],
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"应收账款汇总统计生成完成，总应收: {total_receivables}, 客户数: {customer_count}")
        return summary
        
    except Exception as e:
        logger.error(f"生成应收账款汇总统计失败: {str(e)}")
        raise

def main():
    """主函数"""
    logger = EnhancedLogger("receivables_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成应收账款报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--customer_name', type=str, help='客户名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table', 'summary'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        customer_name = args.customer_name
        output_format = args.format
        
        # 根据格式生成不同类型的报表
        if output_format == 'summary':
            # 生成汇总统计
            summary_data = generate_receivables_summary(
                start_date=start_date,
                end_date=end_date,
                logger=logger
            )
            print(json.dumps(summary_data, ensure_ascii=False, indent=2))
        else:
            # 生成详细报表
            receivables_data = generate_receivables_report(
                start_date=start_date,
                end_date=end_date,
                customer_name=customer_name,
                logger=logger
            )
            
            # 输出结果
            if output_format == 'json':
                # 构建标准的响应结构
                result = {
                    'success': True,
                    'data': receivables_data,
                    'report_type': 'receivables_report',
                    'generated_at': datetime.now().isoformat(),
                    'query_params': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'customer_name': customer_name
                    }
                }
                
                # 添加统计信息
                if receivables_data:
                    total_receivables = sum(record.get('receivable_balance', 0) for record in receivables_data)
                    total_sales = sum(record.get('sales_amount', 0) for record in receivables_data)
                    total_receipts = sum(record.get('receipt_amount', 0) for record in receivables_data)
                    
                    result['statistics'] = {
                        'total_customers': len(receivables_data),
                        'total_receivables': round(total_receivables, 2),
                        'total_sales_amount': round(total_sales, 2),
                        'total_receipt_amount': round(total_receipts, 2)
                    }
                
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 表格格式输出
                print("\n=== 应收账款报表 ===")
                print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if start_date or end_date:
                    print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
                if customer_name:
                    print(f"指定客户: {customer_name}")
                print("-" * 140)
                print(f"{'客户名称':<25} {'应收余额':<12} {'销售金额':<12} {'收款金额':<12} {'账龄天数':<10} {'账龄区间':<12} {'风险等级':<10}")
                print("-" * 140)
                
                total_receivables = 0
                
                for record in receivables_data:
                    # 显示所有有交易记录的客户（包括已付清的）
                    if record.get('total_sales_amount', 0) > 0:
                        print(f"{record.get('customer_name', ''):<25} "
                              f"{record.get('receivable_balance', 0):<12.2f} "
                              f"{record.get('total_sales_amount', 0):<12.2f} "
                              f"{record.get('total_receipt_amount', 0):<12.2f} "
                              f"{record.get('age_days', 0):<10} "
                              f"{record.get('age_range', ''):<12} "
                              f"{record.get('risk_level', ''):<10}")
                        
                        total_receivables += record.get('receivable_balance', 0)
                
                print("-" * 140)
                print(f"{'合计':<25} {total_receivables:<12.2f}")
                print(f"\n共 {len([r for r in receivables_data if r.get('receivable_balance', 0) > 0])} 个客户有应收账款")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr, encoding='utf-8', errors='ignore')
        sys.exit(1)

if __name__ == "__main__":
    main()