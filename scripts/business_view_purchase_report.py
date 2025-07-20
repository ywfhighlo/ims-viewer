#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采购报表业务视图脚本
根据采购入库记录生成采购统计报表，包括采购金额、数量、供应商分布等分析
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

def generate_purchase_report(start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           supplier_name: Optional[str] = None,
                           material_code: Optional[str] = None,
                           logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    生成采购报表（使用查询优化引擎和缓存系统）
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        supplier_name: 指定供应商名称，为空则查询所有供应商
        material_code: 指定物料编码，为空则查询所有物料
        logger: 日志记录器
    
    Returns:
        采购报表数据列表
    """
    if logger is None:
        logger = EnhancedLogger("purchase_report")
    
    try:
        logger.info("开始生成采购报表（使用查询优化引擎和缓存系统）")
        
        # 构建查询参数
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'supplier_name': supplier_name,
            'product_name': material_code  # 查询优化器中使用product_name参数
        }
        
        # 使用缓存装饰器，自动处理缓存逻辑
        def data_generator():
            optimizer = QueryOptimizer(logger)
            return optimizer.optimize_purchase_report_query(params)
        
        # 使用缓存系统，TTL设置为5分钟（300秒）
        purchase_data = cache_report_data(
            view_name='purchase_report',
            params=params,
            data_generator=data_generator,
            ttl=300
        )
        
        logger.info(f"采购报表生成完成，共 {len(purchase_data)} 条记录")
        return purchase_data
        
    except Exception as e:
        logger.error(f"生成采购报表失败: {str(e)}")
        raise

def generate_purchase_summary(start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            logger: Optional[EnhancedLogger] = None) -> Dict[str, Any]:
    """
    生成采购汇总统计
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        logger: 日志记录器
        
    Returns:
        采购汇总统计数据
    """
    if logger is None:
        logger = EnhancedLogger("purchase_summary")
    
    try:
        logger.info("开始生成采购汇总统计")
        
        # 获取详细采购数据
        purchase_data = generate_purchase_report(start_date, end_date, logger=logger)
        
        if not purchase_data:
            return {
                'total_amount': 0,
                'total_quantity': 0,
                'order_count': 0,
                'supplier_count': 0,
                'product_count': 0,
                'top_suppliers': [],
                'top_products': [],
                'monthly_trend': [],
                'price_analysis': {}
            }
        
        # 计算汇总统计
        total_amount = sum(item.get('total_amount', 0) for item in purchase_data)
        total_quantity = sum(item.get('total_quantity', 0) for item in purchase_data)
        order_count = sum(item.get('purchase_count', 0) for item in purchase_data)
        
        # 供应商统计
        suppliers = set()
        supplier_stats = {}
        for item in purchase_data:
            # 从采购数据中获取供应商信息（需要额外查询）
            pass
        
        # 产品统计
        product_count = len(purchase_data)
        
        # 产品排名（按采购金额）
        top_products = sorted(purchase_data, 
                            key=lambda x: x.get('total_amount', 0), 
                            reverse=True)[:10]
        
        # 价格分析
        price_analysis = analyze_purchase_prices(purchase_data)
        
        # 月度趋势
        monthly_trend = calculate_purchase_monthly_trend(purchase_data)
        
        summary = {
            'total_amount': round(total_amount, 2),
            'total_quantity': total_quantity,
            'order_count': order_count,
            'supplier_count': 0,  # 需要额外查询获取
            'product_count': product_count,
            'average_order_value': round(total_amount / order_count, 2) if order_count > 0 else 0,
            'top_suppliers': [],  # 需要额外查询获取
            'top_products': [{
                'product_code': item.get('product_code', ''),
                'product_name': item.get('product_name', ''),
                'total_amount': item.get('total_amount', 0),
                'total_quantity': item.get('total_quantity', 0),
                'purchase_count': item.get('purchase_count', 0),
                'avg_unit_price': item.get('avg_unit_price', 0)
            } for item in top_products],
            'monthly_trend': monthly_trend,
            'price_analysis': price_analysis,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"采购汇总统计生成完成，总金额: {total_amount}, 总订单: {order_count}")
        return summary
        
    except Exception as e:
        logger.error(f"生成采购汇总统计失败: {str(e)}")
        raise

def analyze_purchase_prices(purchase_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析采购价格情况
    
    Args:
        purchase_data: 采购数据列表
        
    Returns:
        价格分析结果
    """
    try:
        if not purchase_data:
            return {}
        
        # 价格稳定性统计
        stable_count = sum(1 for item in purchase_data if item.get('price_stability') == '稳定')
        normal_count = sum(1 for item in purchase_data if item.get('price_stability') == '一般')
        volatile_count = sum(1 for item in purchase_data if item.get('price_stability') == '波动大')
        
        # 价格区间分析
        price_ranges = {
            '0-1000': 0,
            '1000-5000': 0,
            '5000-10000': 0,
            '10000+': 0
        }
        
        for item in purchase_data:
            avg_price = item.get('avg_unit_price', 0)
            if avg_price < 1000:
                price_ranges['0-1000'] += 1
            elif avg_price < 5000:
                price_ranges['1000-5000'] += 1
            elif avg_price < 10000:
                price_ranges['5000-10000'] += 1
            else:
                price_ranges['10000+'] += 1
        
        return {
            'stability_distribution': {
                '稳定': stable_count,
                '一般': normal_count,
                '波动大': volatile_count
            },
            'price_range_distribution': price_ranges,
            'high_value_products': [
                {
                    'product_code': item.get('product_code', ''),
                    'product_name': item.get('product_name', ''),
                    'avg_unit_price': item.get('avg_unit_price', 0),
                    'total_amount': item.get('total_amount', 0)
                }
                for item in sorted(purchase_data, 
                                 key=lambda x: x.get('avg_unit_price', 0), 
                                 reverse=True)[:5]
            ]
        }
        
    except Exception as e:
        return {'error': str(e)}

def calculate_purchase_monthly_trend(purchase_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    计算月度采购趋势
    
    Args:
        purchase_data: 采购数据列表
        
    Returns:
        月度趋势数据
    """
    try:
        monthly_stats = {}
        
        for item in purchase_data:
            # 尝试从不同字段获取日期
            date_str = item.get('latest_purchase_date') or item.get('inbound_date') or item.get('purchase_date')
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
                monthly_stats[month_key]['order_count'] += item.get('purchase_count', 0)
                
            except (ValueError, TypeError) as e:
                continue
        
        # 按月份排序
        trend_data = sorted(monthly_stats.values(), key=lambda x: x['month'])
        
        return trend_data
        
    except Exception as e:
        return []

def main():
    """主函数"""
    logger = EnhancedLogger("purchase_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成采购报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--supplier_name', type=str, help='供应商名称')
        parser.add_argument('--material_code', type=str, help='物料编码')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table', 'summary'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        supplier_name = args.supplier_name
        material_code = args.material_code
        output_format = args.format
        
        # 根据格式生成不同类型的报表
        if output_format == 'summary':
            # 生成汇总统计
            summary_data = generate_purchase_summary(
                start_date=start_date,
                end_date=end_date,
                logger=logger
            )
            print(json.dumps(summary_data, ensure_ascii=False, indent=2))
        else:
            # 生成详细报表
            purchase_data = generate_purchase_report(
                start_date=start_date,
                end_date=end_date,
                supplier_name=supplier_name,
                material_code=material_code,
                logger=logger
            )
            
            # 输出结果
            if output_format == 'json':
                # 构建标准的响应结构
                result = {
                    'success': True,
                    'data': purchase_data,
                    'report_type': 'purchase_report',
                    'generated_at': datetime.now().isoformat(),
                    'query_params': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'supplier_name': supplier_name,
                        'material_code': material_code
                    }
                }
                
                # 添加统计信息
                if purchase_data:
                    total_amount = sum(item.get('total_amount', 0) for item in purchase_data)
                    total_quantity = sum(item.get('total_quantity', 0) for item in purchase_data)
                    purchase_count = sum(item.get('purchase_count', 0) for item in purchase_data)
                    
                    result['statistics'] = {
                        'total_products': len(purchase_data),
                        'total_amount': round(total_amount, 2),
                        'total_quantity': round(total_quantity, 2),
                        'total_purchase_count': purchase_count
                    }
                
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                # 表格格式输出
                print("\n=== 采购报表 ===")
                print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if start_date or end_date:
                    print(f"查询期间: {start_date or '开始'} 至 {end_date or '结束'}")
                if supplier_name:
                    print(f"指定供应商: {supplier_name}")
                if material_code:
                    print(f"指定物料: {material_code}")
                print("-" * 140)
                print(f"{'物料编码':<15} {'物料名称':<25} {'采购金额':<12} {'采购数量':<10} {'订单数':<8} {'供应商数':<10} {'平均单价':<12} {'价格稳定性':<12}")
                print("-" * 140)
                
                total_amount = 0
                total_quantity = 0
                total_orders = 0
                
                for record in purchase_data:
                    print(f"{record.get('product_code', ''):<15} "
                          f"{record.get('product_name', ''):<25} "
                          f"{record.get('total_amount', 0):<12.2f} "
                          f"{record.get('total_quantity', 0):<10.0f} "
                          f"{record.get('purchase_count', 0):<8} "
                          f"{record.get('supplier_count', 0):<10} "
                          f"{record.get('avg_unit_price', 0):<12.2f} "
                          f"{record.get('price_stability', ''):<12}")
                    
                    total_amount += record.get('total_amount', 0)
                    total_quantity += record.get('total_quantity', 0)
                    total_orders += record.get('purchase_count', 0)
                
                print("-" * 140)
                print(f"{'合计':<15} {'':<25} {total_amount:<12.2f} {total_quantity:<10.0f} {total_orders:<8}")
                print(f"\n共 {len(purchase_data)} 个产品")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()