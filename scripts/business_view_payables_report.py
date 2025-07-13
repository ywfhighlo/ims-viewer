#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应付账款统计业务视图脚本
根据进货入库和付款记录生成应付账款统计报表
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from enhanced_logger import EnhancedLogger
from db_connection import get_database_connection

# 数据库连接函数已移至 db_connection 模块

def generate_payables_report(start_date: Optional[str] = None, 
                           end_date: Optional[str] = None,
                           supplier_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    生成应付账款统计报表
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        supplier_name: 供应商名称
        
    Returns:
        应付账款统计报表数据列表
    """
    logger = EnhancedLogger("payables_report")
    
    try:
        db = get_database_connection()
        
        # 获取进货入库数据
        purchase_collection = db['purchase_inbound']
        # 获取付款记录数据
        payment_collection = db['payment_details']
        
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
            
        logger.info(f"查询条件: {query}")
        
        # 查询采购数据
        purchase_query = query.copy()
        if '供货单位' in purchase_query:
            # 采购表中的字段名
            purchase_query['供货单位'] = query['供货单位']
        
        purchase_data = list(purchase_collection.find(purchase_query, {'_id': 0}))
        logger.info(f"查询到 {len(purchase_data)} 条采购记录")
        
        # 查询付款数据
        payment_query = query.copy()
        if '供货单位' in payment_query:
            # 付款表中的字段名可能不同
            payment_query['供应商名称'] = query['供货单位']
            del payment_query['供货单位']
        
        payment_data = list(payment_collection.find(payment_query, {'_id': 0}))
        logger.info(f"查询到 {len(payment_data)} 条付款记录")
        
        # 按供应商汇总采购金额
        supplier_purchases = {}
        for purchase in purchase_data:
            try:
                supplier = purchase.get('供货单位', '')
                if not supplier:
                    continue
                    
                amount = float(purchase.get('金额', 0) or 0)
                date = purchase.get('日期', '')
                
                if supplier not in supplier_purchases:
                    supplier_purchases[supplier] = {
                        'total_purchases': 0,
                        'purchase_count': 0,
                        'latest_purchase_date': None
                    }
                
                supplier_purchases[supplier]['total_purchases'] += amount
                supplier_purchases[supplier]['purchase_count'] += 1
                
                # 更新最新采购日期
                if date:
                    if (not supplier_purchases[supplier]['latest_purchase_date'] or 
                        date > supplier_purchases[supplier]['latest_purchase_date']):
                        supplier_purchases[supplier]['latest_purchase_date'] = date
                        
            except (ValueError, TypeError) as e:
                logger.warning(f"处理采购记录时出错: {e}, 记录: {purchase}")
                continue
        
        # 按供应商汇总付款金额
        supplier_payments = {}
        for payment in payment_data:
            try:
                supplier = payment.get('供应商名称', '')
                if not supplier:
                    continue
                    
                amount = float(payment.get('付款金额', 0) or 0)
                date = payment.get('日期', '')
                
                if supplier not in supplier_payments:
                    supplier_payments[supplier] = {
                        'total_payments': 0,
                        'payment_count': 0,
                        'latest_payment_date': None
                    }
                
                supplier_payments[supplier]['total_payments'] += amount
                supplier_payments[supplier]['payment_count'] += 1
                
                # 更新最新付款日期
                if date:
                    if (not supplier_payments[supplier]['latest_payment_date'] or 
                        date > supplier_payments[supplier]['latest_payment_date']):
                        supplier_payments[supplier]['latest_payment_date'] = date
                        
            except (ValueError, TypeError) as e:
                logger.warning(f"处理付款记录时出错: {e}, 记录: {payment}")
                continue
        
        # 合并数据生成应付账款报表
        all_suppliers = set(supplier_purchases.keys()) | set(supplier_payments.keys())
        
        report_data = []
        for supplier in all_suppliers:
            purchase_info = supplier_purchases.get(supplier, {'total_purchases': 0, 'purchase_count': 0, 'latest_purchase_date': None})
            payment_info = supplier_payments.get(supplier, {'total_payments': 0, 'payment_count': 0, 'latest_payment_date': None})
            
            total_purchases = purchase_info['total_purchases']
            total_payments = payment_info['total_payments']
            balance = total_purchases - total_payments
            
            # 账龄分析（简化版，基于最新采购日期）
            aging_category = "未知"
            if purchase_info['latest_purchase_date']:
                try:
                    purchase_date = datetime.strptime(purchase_info['latest_purchase_date'], '%Y-%m-%d')
                    current_date = datetime.now()
                    days_diff = (current_date - purchase_date).days
                    
                    if days_diff <= 30:
                        aging_category = "30天内"
                    elif days_diff <= 60:
                        aging_category = "31-60天"
                    elif days_diff <= 90:
                        aging_category = "61-90天"
                    else:
                        aging_category = "90天以上"
                except:
                    aging_category = "未知"
            
            # 风险等级评估
            if balance <= 0:
                risk_level = "无风险"
            elif balance <= 10000:
                risk_level = "低风险"
            elif balance <= 50000:
                risk_level = "中风险"
            else:
                risk_level = "高风险"
            
            # 付款率
            payment_rate = (total_payments / total_purchases * 100) if total_purchases > 0 else 0
            
            # 供应商重要性评级（基于采购金额）
            if total_purchases >= 100000:
                importance_level = "重要"
            elif total_purchases >= 50000:
                importance_level = "一般"
            else:
                importance_level = "普通"
            
            report_item = {
                'supplier_name': supplier,
                'total_purchase_amount': total_purchases,
                'total_payment_amount': total_payments,
                'payable_balance': balance,
                'purchase_count': purchase_info['purchase_count'],
                'payment_count': payment_info['payment_count'],
                'payment_rate': payment_rate,
                'latest_purchase_date': purchase_info['latest_purchase_date'],
                'latest_payment_date': payment_info['latest_payment_date'],
                'aging_category': aging_category,
                'risk_level': risk_level,
                'importance_level': importance_level,
                'generated_date': datetime.now().isoformat()
            }
            
            report_data.append(report_item)
        
        # 按应付余额降序排序
        report_data.sort(key=lambda x: x['payable_balance'], reverse=True)
        
        logger.info(f"生成应付账款统计报表完成，共 {len(report_data)} 个供应商")
        return report_data
        
    except Exception as e:
        logger.error(f"生成应付账款统计报表失败: {str(e)}")
        raise

def format_table_output(data: List[Dict[str, Any]]) -> str:
    """格式化表格输出"""
    if not data:
        return "暂无应付账款数据"
    
    # 表头
    headers = ['供应商名称', '采购金额', '付款金额', '应付余额', '付款率(%)', '采购次数', '付款次数', '账龄', '风险等级', '重要性', '最近采购', '最近付款']
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for item in data:
        col_widths[0] = max(col_widths[0], len(str(item.get('supplier_name', ''))))
        col_widths[1] = max(col_widths[1], len(f"{item.get('total_purchase_amount', 0):.2f}"))
        col_widths[2] = max(col_widths[2], len(f"{item.get('total_payment_amount', 0):.2f}"))
        col_widths[3] = max(col_widths[3], len(f"{item.get('payable_balance', 0):.2f}"))
        col_widths[4] = max(col_widths[4], len(f"{item.get('payment_rate', 0):.1f}"))
        col_widths[5] = max(col_widths[5], len(str(item.get('purchase_count', ''))))
        col_widths[6] = max(col_widths[6], len(str(item.get('payment_count', ''))))
        col_widths[7] = max(col_widths[7], len(str(item.get('aging_category', ''))))
        col_widths[8] = max(col_widths[8], len(str(item.get('risk_level', ''))))
        col_widths[9] = max(col_widths[9], len(str(item.get('importance_level', ''))))
        col_widths[10] = max(col_widths[10], len(str(item.get('latest_purchase_date', ''))))
        col_widths[11] = max(col_widths[11], len(str(item.get('latest_payment_date', ''))))
    
    # 构建表格
    result = []
    
    # 表头
    header_row = '|'.join(h.ljust(w) for h, w in zip(headers, col_widths))
    result.append(header_row)
    result.append('-' * len(header_row))
    
    # 数据行
    for item in data:
        row = [
            str(item.get('supplier_name', '')).ljust(col_widths[0]),
            f"{item.get('total_purchase_amount', 0):.2f}".ljust(col_widths[1]),
            f"{item.get('total_payment_amount', 0):.2f}".ljust(col_widths[2]),
            f"{item.get('payable_balance', 0):.2f}".ljust(col_widths[3]),
            f"{item.get('payment_rate', 0):.1f}".ljust(col_widths[4]),
            str(item.get('purchase_count', '')).ljust(col_widths[5]),
            str(item.get('payment_count', '')).ljust(col_widths[6]),
            str(item.get('aging_category', '')).ljust(col_widths[7]),
            str(item.get('risk_level', '')).ljust(col_widths[8]),
            str(item.get('importance_level', '')).ljust(col_widths[9]),
            str(item.get('latest_purchase_date', '')).ljust(col_widths[10]),
            str(item.get('latest_payment_date', '')).ljust(col_widths[11])
        ]
        result.append('|'.join(row))
    
    # 统计信息
    total_suppliers = len(data)
    total_purchases = sum(item.get('total_purchase_amount', 0) for item in data)
    total_payments = sum(item.get('total_payment_amount', 0) for item in data)
    total_payables = sum(item.get('payable_balance', 0) for item in data)
    high_risk_suppliers = sum(1 for item in data if item.get('risk_level') == '高风险')
    important_suppliers = sum(1 for item in data if item.get('importance_level') == '重要')
    overdue_suppliers = sum(1 for item in data if item.get('aging_category') == '90天以上')
    
    result.append('')
    result.append(f"总计: {total_suppliers} 个供应商")
    result.append(f"采购总金额: ¥{total_purchases:.2f}")
    result.append(f"付款总金额: ¥{total_payments:.2f}")
    result.append(f"应付账款总额: ¥{total_payables:.2f}")
    result.append(f"高风险供应商: {high_risk_suppliers} 个")
    result.append(f"重要供应商: {important_suppliers} 个")
    result.append(f"超期供应商: {overdue_suppliers} 个")
    
    return '\n'.join(result)

def main():
    """主函数"""
    logger = EnhancedLogger("payables_report")
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='生成应付账款统计报表')
        parser.add_argument('--start_date', type=str, help='开始日期 (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='结束日期 (YYYY-MM-DD)')
        parser.add_argument('--supplier_name', type=str, help='供应商名称')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'table'], help='输出格式')
        
        args = parser.parse_args()
        
        start_date = args.start_date
        end_date = args.end_date
        supplier_name = args.supplier_name
        output_format = args.format
        
        # 生成应付账款统计报表
        report_data = generate_payables_report(start_date, end_date, supplier_name)
        
        # 输出结果
        if output_format == 'table':
            print(format_table_output(report_data))
        else:
            print(json.dumps(report_data, ensure_ascii=False, indent=2))
            
    except Exception as e:
        logger.error(f"应付账款统计报表生成失败: {str(e)}")
        if output_format == 'json':
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()