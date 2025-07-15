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
    生成采购统计报表（优化版本 - 使用聚合查询提升性能）
    
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
        logger.info("开始生成采购统计报表（优化版本）")
        
        # 构建聚合管道
        pipeline = []
        
        # 1. 匹配阶段 - 构建过滤条件
        match_conditions = {}
        
        # 日期范围筛选
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            match_conditions['inbound_date'] = date_query
            
        # 供应商名称筛选
        if supplier_name:
            match_conditions['supplier_name'] = {'$regex': supplier_name, '$options': 'i'}
            
        # 产品名称筛选
        if product_name:
            match_conditions['material_name'] = {'$regex': product_name, '$options': 'i'}
            
        if match_conditions:
            pipeline.append({'$match': match_conditions})
            
        logger.info(f"查询条件: {match_conditions}")
        
        # 2. 分组聚合阶段
        pipeline.append({
            '$group': {
                '_id': {
                    'material_code': '$material_code',
                    'material_name': '$material_name'
                },
                'product_model': {'$first': '$specification'},
                'unit': {'$first': '$unit'},
                'total_quantity': {'$sum': '$quantity'},
                'total_amount': {'$sum': '$amount'},
                'purchase_count': {'$sum': 1},
                'suppliers': {'$addToSet': '$supplier_name'},
                'latest_purchase_date': {'$max': '$inbound_date'},
                'min_unit_price': {'$min': '$purchase_unit_price'},
                'max_unit_price': {'$max': '$purchase_unit_price'},
                'unit_prices': {'$push': '$purchase_unit_price'}
            }
        })
        
        # 3. 投影阶段 - 计算衍生字段
        pipeline.append({
            '$project': {
                'product_code': '$_id.material_code',
                'product_name': '$_id.material_name',
                'product_model': 1,
                'unit': 1,
                'total_quantity': 1,
                'total_amount': 1,
                'purchase_count': 1,
                'supplier_count': {'$size': '$suppliers'},
                'latest_purchase_date': 1,
                'min_unit_price': 1,
                'max_unit_price': 1,
                'avg_unit_price': {
                    '$cond': {
                        'if': {'$gt': ['$total_quantity', 0]},
                        'then': {'$divide': ['$total_amount', '$total_quantity']},
                        'else': 0
                    }
                },
                'purchase_frequency': {
                    '$switch': {
                        'branches': [
                            {'case': {'$gte': ['$purchase_count', 10]}, 'then': '高频'},
                            {'case': {'$gte': ['$purchase_count', 5]}, 'then': '正常'}
                        ],
                        'default': '低频'
                    }
                },
                'price_stability': {
                    '$switch': {
                        'branches': [
                            {
                                'case': {
                                    '$and': [
                                        {'$gt': ['$min_unit_price', 0]},
                                        {'$lte': [{'$divide': [{'$subtract': ['$max_unit_price', '$min_unit_price']}, '$min_unit_price']}, 0.05]}
                                    ]
                                },
                                'then': '稳定'
                            },
                            {
                                'case': {
                                    '$and': [
                                        {'$gt': ['$min_unit_price', 0]},
                                        {'$lte': [{'$divide': [{'$subtract': ['$max_unit_price', '$min_unit_price']}, '$min_unit_price']}, 0.15]}
                                    ]
                                },
                                'then': '一般'
                            }
                        ],
                        'default': '波动大'
                    }
                },
                'generated_date': {'$literal': datetime.now().isoformat()},
                '_id': 0
            }
        })
        
        # 4. 排序阶段 - 按采购金额降序
        pipeline.append({'$sort': {'total_amount': -1}})
        
        # 执行聚合查询
        purchase_collection = db['purchase_inbound']
        report_data = list(purchase_collection.aggregate(pipeline))
        
        logger.info(f"聚合查询完成，生成采购统计报表，共 {len(report_data)} 个产品")
        return report_data
        
        # 聚合查询已经完成了所有计算，直接返回结果
        
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