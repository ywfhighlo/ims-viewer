#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
销售报表业务视图脚本
根据销售出库记录生成销售统计报表，包括销售金额、数量、客户分布等分析
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

def generate_sales_report(start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         customer_name: Optional[str] = None,
                         material_code: Optional[str] = None,
                         logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成销售报表（使用查询优化引擎和缓存系统）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        customer_name: 指定客户名称，为空则查询所有客户
        material_code: 指定物料编码，为空则查询所有物料
        logger: 日志记录器
    
    Returns:
        销售报表数据列表
    """
    if logger is None:
        logger = EnhancedLogger("sales_report")
    
    try:
        logger.info("开始生成销售报表（使用查询优化引擎和缓存系统）")
        
        # 构建查询参数
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'customer_name': customer_name,
            'material_code': material_code
        }
        
        # 使用缓存装饰器，自动处理缓存逻辑
        def data_generator():
            optimizer = QueryOptimizer(logger)
            return optimizer.optimize_sales_report_query(params)
        
        # 使用缓存系统，TTL设置为5分钟（300秒）
        sales_data = cache_report_data(
            view_name='sales_report',
            params=params,
            data_generator=data_generator,
            ttl=300
        )
        
        logger.info(f"销售报表生成完成，共 {len(sales_data)} 条记录")
        return sales_data
        
    except Exception as e:
        logger.error(f"生成销售报表失败: {str(e)}")
        raise

def generate_sales_summary(start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          logger: Optional[EnhancedLogger] = None) -> Dict[str, Any]:
    """
    生成销售汇总统计
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        logger: 日志记录器
        
    Returns:
        销售汇总统计数据
    """
    if logger is None:
        logger = EnhancedLogger("sales_summary")
    
    try:
        logger.info("开始生成销售汇总统计")
        
        # 获取详细销售数据
        sales_data = generate_sales_report(start_date, end_date, logger=logger)
        
        if not sales_data:
            return {
                'total_amount': 0,
                'total_quantity': 0,
                'order_count': 0,
                'customer_count': 0,
                'product_count': 0,
                'top_customers': [],
                'top_products': [],
                'monthly_trend': []
            }
        
        # 计算汇总统计
        total_amount = sum(item.get('total_amount', 0) for item in sales_data)
        total_quantity = sum(item.get('total_quantity', 0) for item in sales_data)
        order_count = sum(item.get('sales_count', 0) for item in sales_data)
        
        # 客户统计 - 从销售数据中获取客户信息
        all_customers = set()
        for item in sales_data:
            customer_count_in_item = item.get('customer_count', 0)
            if customer_count_in_item > 0:
                all_customers.add(item.get('product_code', ''))  # 使用产品代码作为唯一标识
        customer_count = sum(item.get('customer_count', 0) for item in sales_data)
        
        # 产品统计
        product_count = len(sales_data)
        
        # 客户排名（按销售金额）
        customer_stats = {}
        for item in sales_data:
            customer = item.get('customer_name')
            if customer:
                if customer not in customer_stats:
                    customer_stats[customer] = {
                        'customer_name': customer,
                        'total_amount': 0,
                        'total_quantity': 0,
                        'order_count': 0
                    }
                customer_stats[customer]['total_amount'] += item.get('total_amount', 0)
                customer_stats[customer]['total_quantity'] += item.get('total_quantity', 0)
                customer_stats[customer]['order_count'] += item.get('sales_count', 0)
        
        top_customers = sorted(customer_stats.values(), 
                             key=lambda x: x['total_amount'], 
                             reverse=True)[:10]
        
        # 产品排名（按销售金额）
        product_stats = {}
        for item in sales_data:
            product = item.get('material_code')
            if product:
                if product not in product_stats:
                    product_stats[product] = {
                        'material_code': product,
                        'material_name': item.get('material_name', ''),
                        'total_amount': 0,
                        'total_quantity': 0,
                        'order_count': 0
                    }
                product_stats[product]['total_amount'] += item.get('total_amount', 0)
                product_stats[product]['total_quantity'] += item.get('total_quantity', 0)
                product_stats[product]['order_count'] += item.get('sales_count', 0)
        
        top_products = sorted(product_stats.values(),
                            key=lambda x: x['total_amount'],
                            reverse=True)[:10]
        
        # 月度趋势（如果有日期数据）
        monthly_trend = calculate_monthly_trend(sales_data)
        
        summary = {
            'total_amount': round(total_amount, 2),
            'total_quantity': total_quantity,
            'order_count': order_count,
            'customer_count': customer_count,
            'product_count': product_count,
            'average_order_value': round(total_amount / order_count, 2) if order_count > 0 else 0,
            'top_customers': top_customers,
            'top_products': top_products,
            'monthly_trend': monthly_trend,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"销售汇总统计生成完成，总金额: {total_amount}, 总订单: {order_count}")
        return summary
        
    except Exception as e:
        logger.error(f"生成销售汇总统计失败: {str(e)}")
        raise

def calculate_monthly_trend(sales_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    计算月度销售趋势
    
    Args:
        sales_data: 销售数据列表
        
    Returns:
        月度趋势数据
    """
    try:
        monthly_stats = {}
        
        for item in sales_data:
            # 尝试从不同字段获取日期
            date_str = item.get('period') or item.get('outbound_date') or item.get('sales_date')
            if not date_str:
                continue
                
            try:
                # 解析日期并提取年月
                if isinstance(date_str, str):
                    if 'T' in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace('T', ' ').replace('Z', ''))
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                else:
                    continue
                    
                month_key = date_obj.strftime('%Y-%m')
                
                if month_key not in monthly_stats:
                    monthly_stats[month_key] = {
                        'month': month_key,
                        'total_amount': 0,
                        'total_quantity': 0,
                        'order_count': 0
                    }
                
                monthly_stats[month_key]['total_amount'] += item.get('total_amount', 0)
                monthly_stats[month_key]['total_quantity'] += item.get('total_quantity', 0)
                monthly_stats[month_key]['order_count'] += item.get('sales_count', 0)
                
            except (ValueError, TypeError) as e:
                continue
        
        # 按月份排序
        trend_data = sorted(monthly_stats.values(), key=lambda x: x['month'])
        
        return trend_data
        
    except Exception as e:
        return []

def main():
    """主函数"""
    logger = EnhancedLogger("sales_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成销售报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--customer_name', type=str, help='客户名称')
        parser.add_argument('--material_code', type=str, help='物料编码')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table', 'summary'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        customer_name = args.customer_name
        material_code = args.material_code
        output_format = args.format
        
        # 根据格式生成不同类型的报表
        if output_format == 'summary':
            # 生成汇总统计
            summary_data = generate_sales_summary(
                start_date=start_date,
                end_date=end_date,
                logger=logger
            )
            print(json.dumps(summary_data, ensure_ascii=False, indent=2))
        else:
            # 生成详细报表
            sales_data = generate_sales_report(
                start_date=start_date,
                end_date=end_date,
                customer_name=customer_name,
                material_code=material_code,
                logger=logger
            )
            
            # 输出结果
            if output_format == 'json':
                print(json.dumps(sales_data, ensure_ascii=False, indent=2))
            else:
                # 表格格式输出
                print("\n=== 销售报表 ===")
                print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if start_date or end_date:
                    print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
                if customer_name:
                    print(f"指定客户: {customer_name}")
                if material_code:
                    print(f"指定物料: {material_code}")
                print("-" * 120)
                print(f"{'客户名称':<25} {'物料编码':<15} {'销售金额':<12} {'销售数量':<10} {'订单数':<8} {'平均单价':<12}")
                print("-" * 120)
                
                total_amount = 0
                total_quantity = 0
                total_orders = 0
                
                for record in sales_data:
                    avg_price = (record.get('total_sales_amount', 0) / 
                               record.get('total_quantity', 1)) if record.get('total_quantity', 0) > 0 else 0
                    
                    print(f"{record.get('customer_name', ''):<25} "
                          f"{record.get('material_code', ''):<15} "
                          f"{record.get('total_sales_amount', 0):<12.2f} "
                          f"{record.get('total_quantity', 0):<10.0f} "
                          f"{record.get('order_count', 0):<8} "
                          f"{avg_price:<12.2f}")
                    
                    total_amount += record.get('total_sales_amount', 0)
                    total_quantity += record.get('total_quantity', 0)
                    total_orders += record.get('order_count', 0)
                
                print("-" * 120)
                print(f"{'合计':<25} {'':<15} {total_amount:<12.2f} {total_quantity:<10.0f} {total_orders:<8}")
                print(f"\n共 {len(sales_data)} 条记录")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()