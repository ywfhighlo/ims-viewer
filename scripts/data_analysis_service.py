#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据统计分析组件
提供业务数据的统计分析和趋势预测
"""

import sys
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_database

class DataAnalysisService:
    def __init__(self):
        self.db = get_database()
        if self.db is None:
            raise Exception("无法连接到数据库")

    def get_business_overview(self, date_range: Dict) -> Dict:
        """获取业务概览"""
        try:
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            # 定义聚合查询
            sales_pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
                {'$group': {'_id': None, 'total_sales': {'$sum': '$amount'}}}
            ]
            purchase_pipeline = [
                {'$match': {'inbound_date': {'$gte': start_date, '$lte': end_date}}},
                {'$group': {'_id': None, 'total_purchases': {'$sum': '$amount'}}}
            ]

            # 执行聚合查询
            total_sales_result = list(self.db['sales_outbound'].aggregate(sales_pipeline))
            total_purchases_result = list(self.db['purchase_inbound'].aggregate(purchase_pipeline))

            # 获取客户和供应商总数
            total_customers = self.db['customers'].count_documents({})
            total_suppliers = self.db['suppliers'].count_documents({})

            overview_data = {
                'total_sales': total_sales_result[0]['total_sales'] if total_sales_result else 0,
                'total_purchases': total_purchases_result[0]['total_purchases'] if total_purchases_result else 0,
                'total_customers': total_customers,
                'total_suppliers': total_suppliers
            }

            return {'success': True, 'data': overview_data}
        except Exception as e:
            return {'success': False, 'message': f'获取业务概览失败: {str(e)}'}

    def analyze_sales_trend(self, dimension: str, date_range: Dict) -> Dict:
        """分析销售趋势"""
        try:
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}}
            ]

            if dimension == 'product':
                group_id = '$sales_product_name'
                sort_field = 'total_sales'
            elif dimension == 'customer':
                group_id = '$customer_name'
                sort_field = 'total_sales'
            elif dimension == 'month':
                group_id = {'$dateToString': {'format': '%Y-%m', 'date': '$outbound_date'}}
                sort_field = '_id'
            else:
                return {'success': False, 'message': '不支持的分析维度'}

            pipeline.extend([
                {'$group': {
                    '_id': group_id,
                    'total_sales': {'$sum': '$amount'},
                    'count': {'$sum': 1}
                }},
                {'$sort': {sort_field: -1 if sort_field == 'total_sales' else 1}}
            ])

            trend_data = list(self.db['sales_outbound'].aggregate(pipeline))
            return {'success': True, 'data': trend_data}
        except Exception as e:
            return {'success': False, 'message': f'分析销售趋势失败: {str(e)}'}

    def analyze_customer_value(self, analysis_type: str = 'rfm') -> Dict:
        """分析客户价值，目前支持RFM模型"""
        if analysis_type != 'rfm':
            return {'success': False, 'message': '不支持的客户价值分析类型'}

        try:
            now = datetime.now()
            pipeline = [
                {
                    '$group': {
                        '_id': '$customer_name',
                        'last_purchase_date': {'$max': '$outbound_date'},
                        'frequency': {'$sum': 1},
                        'monetary': {'$sum': '$amount'}
                    }
                },
                {
                    '$project': {
                        'customer_name': '$_id',
                        '_id': 0,
                        'last_purchase_date': '$last_purchase_date',
                        'frequency': '$frequency',
                        'monetary': '$monetary'
                    }
                },
                {
                    '$sort': {
                        'monetary': -1
                    }
                }
            ]

            results = list(self.db['sales_outbound'].aggregate(pipeline))

            # 计算Recency
            for item in results:
                recency_days = (now - item['last_purchase_date']).days
                item['recency'] = recency_days

            return {'success': True, 'data': results}
        except Exception as e:
            return {'success': False, 'message': f'分析客户价值失败: {str(e)}'}

    def analyze_inventory_turnover(self, date_range: Dict) -> Dict:
        """分析库存周转率"""
        try:
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            # 1. 计算销售成本 (时间段内的出库总额)
            sales_pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
                {'$group': {'_id': None, 'total_cost_of_goods_sold': {'$sum': '$amount'}}}
            ]
            sales_result = list(self.db['sales_outbound'].aggregate(sales_pipeline))
            cost_of_goods_sold = sales_result[0]['total_cost_of_goods_sold'] if sales_result else 0

            # 2. 计算平均库存价值 (简化模型)
            # 在实际应用中，这应该基于每日库存快照计算。这里我们使用一个简化的平均值。
            inventory_pipeline = [
                {'$group': {'_id': None, 'average_inventory_value': {'$avg': '$total_value'}}}
            ]
            inventory_result = list(self.db['inventory_stats'].aggregate(inventory_pipeline))
            average_inventory = inventory_result[0]['average_inventory_value'] if inventory_result else 0

            # 3. 计算库存周转率
            if average_inventory > 0:
                turnover_rate = cost_of_goods_sold / average_inventory
            else:
                turnover_rate = 0

            turnover_data = {
                'cost_of_goods_sold': cost_of_goods_sold,
                'average_inventory': average_inventory,
                'turnover_rate': turnover_rate
            }

            return {'success': True, 'data': turnover_data}
        except Exception as e:
            return {'success': False, 'message': f'分析库存周转率失败: {str(e)}'}

    def generate_comparison_analysis(self, metrics: List[str], dimensions: List[str], date_range: Dict) -> Dict:
        """生成多维度、多指标的对比分析"""
        try:
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            if not metrics or not dimensions:
                return {'success': False, 'message': '必须提供至少一个指标和维度'}

            # 维度映射
            dimension_map = {
                'product': '$sales_product_name',
                'customer': '$customer_name',
                'supplier': '$supplier_name',
                'month': {'$dateToString': {'format': '%Y-%m', 'date': '$outbound_date'}}
            }
            
            # 构建group_id
            group_id = {dim: dimension_map[dim] for dim in dimensions if dim in dimension_map}
            if not group_id:
                return {'success': False, 'message': '提供的维度无效'}

            # 构建group stage
            group_stage = {'_id': group_id}
            for metric in metrics:
                if metric == 'total_sales':
                    group_stage['total_sales'] = {'$sum': '$amount'}
                elif metric == 'sales_count':
                    group_stage['sales_count'] = {'$sum': 1}

            # 目前仅支持销售数据分析
            pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
                {'$group': group_stage},
                {'$sort': {'_id': 1}}
            ]

            results = list(self.db['sales_outbound'].aggregate(pipeline))
            return {'success': True, 'data': results}
        except Exception as e:
            return {'success': False, 'message': f'生成对比分析失败: {str(e)}'}

if __name__ == '__main__':
    # 这是一个示例，展示如何使用DataAnalysisService
    service = DataAnalysisService()
    print("DataAnalysisService 初始化成功")
