#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应收账款报表业务视图脚本
根据销售出库和收款记录生成应收账款报表，包括客户应收余额、账龄分析等
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
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
            # 复用客户对账单查询，然后进行应收账款分析
            reconciliation_data = optimizer.optimize_customer_reconciliation_query(params)
            return analyze_receivables_aging(reconciliation_data, logger)
        
        # 使用缓存系统，TTL设置为3分钟（180秒），应收账款数据变化较快
        receivables_data = cache_report_data(
            view_name='receivables_report',
            params=params,
            data_generator=data_generator,
            ttl=180
        )
        
        logger.info(f"应收账款报表生成完成，共 {len(receivables_data)} 条记录")
        return receivables_data
        
    except Exception as e:
        logger.error(f"生成应收账款报表失败: {str(e)}")
        raise

def analyze_receivables_aging(reconciliation_data: List[Dict[str, Any]], 
                            logger: EnhancedLogger) -> List[Dict[str, Any]]:
    """
    分析应收账款账龄
    
    Args:
        reconciliation_data: 客户对账单数据
        logger: 日志记录器
        
    Returns:
        应收账款账龄分析数据
    """
    try:
        logger.info("开始进行应收账款账龄分析")
        
        receivables_data = []
        current_date = datetime.now()
        
        for record in reconciliation_data:
            balance = record.get('balance', 0)
            
            # 只处理有应收余额的客户
            if balance <= 0:
                continue
            
            # 获取最后销售日期
            latest_sales_date_str = record.get('latest_sales_date')
            if not latest_sales_date_str:
                continue
            
            try:
                # 解析最后销售日期
                if isinstance(latest_sales_date_str, str):
                    if 'T' in latest_sales_date_str:
                        latest_sales_date = datetime.fromisoformat(latest_sales_date_str.replace('T', ' ').replace('Z', ''))
                    else:
                        latest_sales_date = datetime.strptime(latest_sales_date_str, '%Y-%m-%d')
                else:
                    continue
                
                # 计算账龄（天数）
                aging_days = (current_date - latest_sales_date).days
                
                # 账龄分类
                aging_category = categorize_aging(aging_days)
                
                # 风险等级评估
                risk_level = assess_risk_level(aging_days, balance)
                
                # 构建应收账款记录
                receivables_record = {
                    'customer_name': record.get('customer_name', ''),
                    'customer_credit_code': record.get('customer_credit_code', ''),
                    'customer_contact': record.get('customer_contact', ''),
                    'customer_phone': record.get('customer_phone', ''),
                    'customer_address': record.get('customer_address', ''),
                    'receivable_amount': round(balance, 2),
                    'total_sales_amount': record.get('total_sales_amount', 0),
                    'total_receipt_amount': record.get('total_receipt_amount', 0),
                    'sales_count': record.get('sales_count', 0),
                    'receipt_count': record.get('receipt_count', 0),
                    'latest_sales_date': latest_sales_date_str,
                    'latest_receipt_date': record.get('latest_receipt_date', ''),
                    'aging_days': aging_days,
                    'aging_category': aging_category,
                    'risk_level': risk_level,
                    'collection_priority': calculate_collection_priority(aging_days, balance),
                    'estimated_collection_date': estimate_collection_date(aging_days, latest_sales_date),
                    'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                receivables_data.append(receivables_record)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"解析客户 {record.get('customer_name', '')} 的日期失败: {str(e)}")
                continue
        
        # 按应收金额降序排序
        receivables_data.sort(key=lambda x: x['receivable_amount'], reverse=True)
        
        logger.info(f"应收账款账龄分析完成，共 {len(receivables_data)} 个客户有应收余额")
        return receivables_data
        
    except Exception as e:
        logger.error(f"应收账款账龄分析失败: {str(e)}")
        raise

def categorize_aging(aging_days: int) -> str:
    """
    账龄分类
    
    Args:
        aging_days: 账龄天数
        
    Returns:
        账龄分类
    """
    if aging_days <= 30:
        return '30天以内'
    elif aging_days <= 60:
        return '31-60天'
    elif aging_days <= 90:
        return '61-90天'
    elif aging_days <= 180:
        return '91-180天'
    elif aging_days <= 365:
        return '181-365天'
    else:
        return '365天以上'

def assess_risk_level(aging_days: int, amount: float) -> str:
    """
    评估风险等级
    
    Args:
        aging_days: 账龄天数
        amount: 应收金额
        
    Returns:
        风险等级
    """
    # 基于账龄和金额的风险评估
    if aging_days <= 30:
        return '低风险'
    elif aging_days <= 90:
        if amount > 50000:
            return '中风险'
        else:
            return '低风险'
    elif aging_days <= 180:
        if amount > 20000:
            return '高风险'
        else:
            return '中风险'
    else:
        return '高风险'

def calculate_collection_priority(aging_days: int, amount: float) -> int:
    """
    计算催收优先级（1-10，10为最高优先级）
    
    Args:
        aging_days: 账龄天数
        amount: 应收金额
        
    Returns:
        优先级分数
    """
    # 基础分数（基于账龄）
    if aging_days <= 30:
        base_score = 2
    elif aging_days <= 60:
        base_score = 4
    elif aging_days <= 90:
        base_score = 6
    elif aging_days <= 180:
        base_score = 8
    else:
        base_score = 10
    
    # 金额调整
    if amount > 100000:
        amount_bonus = 2
    elif amount > 50000:
        amount_bonus = 1
    else:
        amount_bonus = 0
    
    return min(10, base_score + amount_bonus)

def estimate_collection_date(aging_days: int, latest_sales_date: datetime) -> str:
    """
    预估回款日期
    
    Args:
        aging_days: 账龄天数
        latest_sales_date: 最后销售日期
        
    Returns:
        预估回款日期
    """
    try:
        # 基于历史数据和行业经验的简单预估
        if aging_days <= 30:
            # 新账款，预估30天内回款
            estimated_date = latest_sales_date + timedelta(days=30)
        elif aging_days <= 90:
            # 中期账款，预估60天内回款
            estimated_date = datetime.now() + timedelta(days=60)
        else:
            # 长期账款，预估90天内回款
            estimated_date = datetime.now() + timedelta(days=90)
        
        return estimated_date.strftime('%Y-%m-%d')
        
    except Exception:
        return ''

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
                'total_receivable_amount': 0,
                'customer_count': 0,
                'aging_distribution': {},
                'risk_distribution': {},
                'top_customers': [],
                'collection_forecast': {}
            }
        
        # 计算汇总统计
        total_receivable_amount = sum(item.get('receivable_amount', 0) for item in receivables_data)
        customer_count = len(receivables_data)
        
        # 账龄分布统计
        aging_distribution = {}
        for item in receivables_data:
            aging_category = item.get('aging_category', '未知')
            if aging_category not in aging_distribution:
                aging_distribution[aging_category] = {
                    'count': 0,
                    'amount': 0
                }
            aging_distribution[aging_category]['count'] += 1
            aging_distribution[aging_category]['amount'] += item.get('receivable_amount', 0)
        
        # 风险分布统计
        risk_distribution = {}
        for item in receivables_data:
            risk_level = item.get('risk_level', '未知')
            if risk_level not in risk_distribution:
                risk_distribution[risk_level] = {
                    'count': 0,
                    'amount': 0
                }
            risk_distribution[risk_level]['count'] += 1
            risk_distribution[risk_level]['amount'] += item.get('receivable_amount', 0)
        
        # 前10大应收客户
        top_customers = receivables_data[:10]
        
        # 回款预测
        collection_forecast = generate_collection_forecast(receivables_data)
        
        summary = {
            'total_receivable_amount': round(total_receivable_amount, 2),
            'customer_count': customer_count,
            'average_receivable_per_customer': round(total_receivable_amount / customer_count, 2) if customer_count > 0 else 0,
            'aging_distribution': {
                category: {
                    'count': data['count'],
                    'amount': round(data['amount'], 2),
                    'percentage': round(data['amount'] / total_receivable_amount * 100, 2) if total_receivable_amount > 0 else 0
                }
                for category, data in aging_distribution.items()
            },
            'risk_distribution': {
                risk: {
                    'count': data['count'],
                    'amount': round(data['amount'], 2),
                    'percentage': round(data['amount'] / total_receivable_amount * 100, 2) if total_receivable_amount > 0 else 0
                }
                for risk, data in risk_distribution.items()
            },
            'top_customers': [{
                'customer_name': item.get('customer_name', ''),
                'receivable_amount': item.get('receivable_amount', 0),
                'aging_days': item.get('aging_days', 0),
                'risk_level': item.get('risk_level', ''),
                'collection_priority': item.get('collection_priority', 0)
            } for item in top_customers],
            'collection_forecast': collection_forecast,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"应收账款汇总统计生成完成，总应收: {total_receivable_amount}, 客户数: {customer_count}")
        return summary
        
    except Exception as e:
        logger.error(f"生成应收账款汇总统计失败: {str(e)}")
        raise

def generate_collection_forecast(receivables_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成回款预测
    
    Args:
        receivables_data: 应收账款数据
        
    Returns:
        回款预测数据
    """
    try:
        forecast = {
            'next_30_days': 0,
            'next_60_days': 0,
            'next_90_days': 0,
            'beyond_90_days': 0
        }
        
        current_date = datetime.now()
        
        for item in receivables_data:
            estimated_date_str = item.get('estimated_collection_date', '')
            if not estimated_date_str:
                continue
            
            try:
                estimated_date = datetime.strptime(estimated_date_str, '%Y-%m-%d')
                days_to_collection = (estimated_date - current_date).days
                amount = item.get('receivable_amount', 0)
                
                if days_to_collection <= 30:
                    forecast['next_30_days'] += amount
                elif days_to_collection <= 60:
                    forecast['next_60_days'] += amount
                elif days_to_collection <= 90:
                    forecast['next_90_days'] += amount
                else:
                    forecast['beyond_90_days'] += amount
                    
            except (ValueError, TypeError):
                continue
        
        # 四舍五入
        for key in forecast:
            forecast[key] = round(forecast[key], 2)
        
        return forecast
        
    except Exception as e:
        return {'error': str(e)}

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
                print(json.dumps(receivables_data, ensure_ascii=False, indent=2))
            else:
                # 表格格式输出
                print("\n=== 应收账款报表 ===")
                print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if start_date or end_date:
                    print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
                if customer_name:
                    print(f"指定客户: {customer_name}")
                print("-" * 150)
                print(f"{'客户名称':<25} {'应收金额':<12} {'账龄天数':<10} {'账龄分类':<12} {'风险等级':<10} {'催收优先级':<12} {'预估回款日期':<15}")
                print("-" * 150)
                
                total_receivable = 0
                
                for record in receivables_data:
                    print(f"{record.get('customer_name', ''):<25} "
                          f"{record.get('receivable_amount', 0):<12.2f} "
                          f"{record.get('aging_days', 0):<10} "
                          f"{record.get('aging_category', ''):<12} "
                          f"{record.get('risk_level', ''):<10} "
                          f"{record.get('collection_priority', 0):<12} "
                          f"{record.get('estimated_collection_date', ''):<15}")
                    
                    total_receivable += record.get('receivable_amount', 0)
                
                print("-" * 150)
                print(f"{'合计':<25} {total_receivable:<12.2f}")
                print(f"\n共 {len(receivables_data)} 个客户有应收余额")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()