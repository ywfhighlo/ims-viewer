#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采购统计报表业务视图脚本
根据进货入库数据生成采购统计报表
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from enhanced_logger import EnhancedLogger
from db_connection import get_database_connection

# 数据库连接函数已移至 db_connection 模块

def generate_purchase_report(start_date: Optional[str] = None, 
                           end_date: Optional[str] = None,
                           supplier_name: Optional[str] = None,
                           product_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    生成采购统计报表
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        supplier_name: 供应商名称
        product_name: 产品名称
        
    Returns:
        采购统计报表数据列表
    """
    logger = EnhancedLogger("purchase_report")
    
    try:
        db = get_database_connection()
        
        # 获取进货入库数据
        purchase_collection = db['purchase_inbound']
        
        # 构建查询条件
        query = {}
        
        # 日期范围筛选
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            query['日期'] = date_query
            
        # 供应商名称筛选
        if supplier_name:
            query['供货单位'] = {'$regex': supplier_name, '$options': 'i'}
            
        # 产品名称筛选
        if product_name:
            query['进货物料名称'] = {'$regex': product_name, '$options': 'i'}
            
        logger.info(f"查询条件: {query}")
        
        # 查询采购数据
        purchase_data = list(purchase_collection.find(query, {'_id': 0}))
        logger.info(f"查询到 {len(purchase_data)} 条采购记录")
        
        # 按产品汇总采购数据
        product_summary = {}
        
        for purchase in purchase_data:
            try:
                product_code = purchase.get('进货物料编码', '')
                product_name_val = purchase.get('进货物料名称', '')
                
                if not product_code and not product_name_val:
                    continue
                    
                key = f"{product_code}_{product_name_val}"
                
                if key not in product_summary:
                    product_summary[key] = {
                        'product_code': product_code,
                        'product_name': product_name_val,
                        'product_model': purchase.get('进货物料型号', ''),
                        'unit': purchase.get('单位', ''),
                        'total_quantity': 0,
                        'total_amount': 0,
                        'purchase_count': 0,
                        'suppliers': set(),
                        'latest_purchase_date': None,
                        'avg_unit_price': 0,
                        'min_unit_price': float('inf'),
                        'max_unit_price': 0
                    }
                
                # 累计数量和金额
                quantity = float(purchase.get('数量', 0) or 0)
                amount = float(purchase.get('金额', 0) or 0)
                unit_price = float(purchase.get('单价', 0) or 0)
                
                product_summary[key]['total_quantity'] += quantity
                product_summary[key]['total_amount'] += amount
                product_summary[key]['purchase_count'] += 1
                
                # 记录供应商
                supplier = purchase.get('供货单位', '')
                if supplier:
                    product_summary[key]['suppliers'].add(supplier)
                
                # 更新价格范围
                if unit_price > 0:
                    product_summary[key]['min_unit_price'] = min(product_summary[key]['min_unit_price'], unit_price)
                    product_summary[key]['max_unit_price'] = max(product_summary[key]['max_unit_price'], unit_price)
                
                # 更新最新采购日期
                purchase_date = purchase.get('日期', '')
                if purchase_date:
                    if (not product_summary[key]['latest_purchase_date'] or 
                        purchase_date > product_summary[key]['latest_purchase_date']):
                        product_summary[key]['latest_purchase_date'] = purchase_date
                        
            except (ValueError, TypeError) as e:
                logger.warning(f"处理采购记录时出错: {e}, 记录: {purchase}")
                continue
        
        # 转换为报表格式
        report_data = []
        for key, summary in product_summary.items():
            # 计算平均单价
            avg_price = (summary['total_amount'] / summary['total_quantity'] 
                        if summary['total_quantity'] > 0 else 0)
            
            # 处理价格范围
            min_price = summary['min_unit_price'] if summary['min_unit_price'] != float('inf') else 0
            max_price = summary['max_unit_price']
            
            # 采购频率分析
            if summary['purchase_count'] >= 10:
                purchase_frequency = "高频"
            elif summary['purchase_count'] >= 5:
                purchase_frequency = "正常"
            else:
                purchase_frequency = "低频"
            
            # 价格稳定性分析
            if min_price > 0 and max_price > 0:
                price_variance = ((max_price - min_price) / min_price) * 100
                if price_variance <= 5:
                    price_stability = "稳定"
                elif price_variance <= 15:
                    price_stability = "一般"
                else:
                    price_stability = "波动大"
            else:
                price_stability = "未知"
            
            report_item = {
                'product_code': summary['product_code'],
                'product_name': summary['product_name'],
                'product_model': summary['product_model'],
                'unit': summary['unit'],
                'total_quantity': summary['total_quantity'],
                'total_amount': summary['total_amount'],
                'purchase_count': summary['purchase_count'],
                'supplier_count': len(summary['suppliers']),
                'avg_unit_price': avg_price,
                'min_unit_price': min_price,
                'max_unit_price': max_price,
                'latest_purchase_date': summary['latest_purchase_date'],
                'purchase_frequency': purchase_frequency,
                'price_stability': price_stability,
                'generated_date': datetime.now().isoformat()
            }
            
            report_data.append(report_item)
        
        # 按采购金额降序排序
        report_data.sort(key=lambda x: x['total_amount'], reverse=True)
        
        logger.info(f"生成采购统计报表完成，共 {len(report_data)} 个产品")
        return report_data
        
    except Exception as e:
        logger.error(f"生成采购统计报表失败: {str(e)}")
        raise

def format_table_output(data: List[Dict[str, Any]]) -> str:
    """格式化表格输出"""
    if not data:
        return "暂无采购数据"
    
    # 表头
    headers = ['产品编码', '产品名称', '型号', '采购数量', '采购金额', '采购次数', '供应商数', '平均单价', '最低单价', '最高单价', '采购频率', '价格稳定性', '最近采购日期']
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for item in data:
        col_widths[0] = max(col_widths[0], len(str(item.get('product_code', ''))))
        col_widths[1] = max(col_widths[1], len(str(item.get('product_name', ''))))
        col_widths[2] = max(col_widths[2], len(str(item.get('product_model', ''))))
        col_widths[3] = max(col_widths[3], len(str(item.get('total_quantity', ''))))
        col_widths[4] = max(col_widths[4], len(f"{item.get('total_amount', 0):.2f}"))
        col_widths[5] = max(col_widths[5], len(str(item.get('purchase_count', ''))))
        col_widths[6] = max(col_widths[6], len(str(item.get('supplier_count', ''))))
        col_widths[7] = max(col_widths[7], len(f"{item.get('avg_unit_price', 0):.2f}"))
        col_widths[8] = max(col_widths[8], len(f"{item.get('min_unit_price', 0):.2f}"))
        col_widths[9] = max(col_widths[9], len(f"{item.get('max_unit_price', 0):.2f}"))
        col_widths[10] = max(col_widths[10], len(str(item.get('purchase_frequency', ''))))
        col_widths[11] = max(col_widths[11], len(str(item.get('price_stability', ''))))
        col_widths[12] = max(col_widths[12], len(str(item.get('latest_purchase_date', ''))))
    
    # 构建表格
    result = []
    
    # 表头
    header_row = '|'.join(h.ljust(w) for h, w in zip(headers, col_widths))
    result.append(header_row)
    result.append('-' * len(header_row))
    
    # 数据行
    for item in data:
        row = [
            str(item.get('product_code', '')).ljust(col_widths[0]),
            str(item.get('product_name', '')).ljust(col_widths[1]),
            str(item.get('product_model', '')).ljust(col_widths[2]),
            str(item.get('total_quantity', '')).ljust(col_widths[3]),
            f"{item.get('total_amount', 0):.2f}".ljust(col_widths[4]),
            str(item.get('purchase_count', '')).ljust(col_widths[5]),
            str(item.get('supplier_count', '')).ljust(col_widths[6]),
            f"{item.get('avg_unit_price', 0):.2f}".ljust(col_widths[7]),
            f"{item.get('min_unit_price', 0):.2f}".ljust(col_widths[8]),
            f"{item.get('max_unit_price', 0):.2f}".ljust(col_widths[9]),
            str(item.get('purchase_frequency', '')).ljust(col_widths[10]),
            str(item.get('price_stability', '')).ljust(col_widths[11]),
            str(item.get('latest_purchase_date', '')).ljust(col_widths[12])
        ]
        result.append('|'.join(row))
    
    # 统计信息
    total_products = len(data)
    total_quantity = sum(item.get('total_quantity', 0) for item in data)
    total_amount = sum(item.get('total_amount', 0) for item in data)
    high_freq_products = sum(1 for item in data if item.get('purchase_frequency') == '高频')
    low_freq_products = sum(1 for item in data if item.get('purchase_frequency') == '低频')
    stable_price_products = sum(1 for item in data if item.get('price_stability') == '稳定')
    
    result.append('')
    result.append(f"总计: {total_products} 个产品")
    result.append(f"采购总数量: {total_quantity}")
    result.append(f"采购总金额: ¥{total_amount:.2f}")
    result.append(f"高频采购产品: {high_freq_products} 个")
    result.append(f"低频采购产品: {low_freq_products} 个")
    result.append(f"价格稳定产品: {stable_price_products} 个")
    
    return '\n'.join(result)

def main():
    """主函数"""
    logger = EnhancedLogger("purchase_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成采购统计报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--supplier_name', type=str, help='供应商名称')
        parser.add_argument('--product_name', type=str, help='产品名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        supplier_name = args.supplier_name
        product_name = args.product_name
        output_format = args.format
        
        # 生成采购统计报表
        report_data = generate_purchase_report(start_date, end_date, supplier_name, product_name)
        
        # 输出结果
        if output_format == 'table':
            print(format_table_output(report_data))
        else:
            print(json.dumps(report_data, ensure_ascii=False, indent=2))
            
    except Exception as e:
        logger.error(f"采购统计报表生成失败: {str(e)}")
        if output_format == 'json':
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()