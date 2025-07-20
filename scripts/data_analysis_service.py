#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据统计分析组件
提供业务数据的统计分析和趋势预测
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import math

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_database
from enhanced_logger import EnhancedLogger

class DataAnalysisService:
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        self.db = get_database()
        if self.db is None:
            raise Exception("无法连接到数据库")
        self.logger = logger or EnhancedLogger("data_analysis_service")

    def get_business_overview(self, date_range: Dict) -> Dict:
        """获取业务概览（增强版）"""
        try:
            self.logger.info("开始生成业务概览")
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            # 销售数据聚合
            sales_pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
                {
                    '$group': {
                        '_id': None,
                        'total_sales': {'$sum': '$amount'},
                        'total_sales_count': {'$sum': 1},
                        'avg_order_value': {'$avg': '$amount'},
                        'max_order_value': {'$max': '$amount'},
                        'min_order_value': {'$min': '$amount'}
                    }
                }
            ]

            # 采购数据聚合
            purchase_pipeline = [
                {'$match': {'inbound_date': {'$gte': start_date, '$lte': end_date}}},
                {
                    '$group': {
                        '_id': None,
                        'total_purchases': {'$sum': '$amount'},
                        'total_purchase_count': {'$sum': 1},
                        'avg_purchase_value': {'$avg': '$amount'}
                    }
                }
            ]

            # 执行聚合查询
            sales_result = list(self.db['sales_outbound'].aggregate(sales_pipeline))
            purchase_result = list(self.db['purchase_inbound'].aggregate(purchase_pipeline))

            # 客户统计
            customer_pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
                {'$group': {'_id': '$customer_name'}},
                {'$count': 'active_customers'}
            ]
            customer_result = list(self.db['sales_outbound'].aggregate(customer_pipeline))

            # 供应商统计
            supplier_pipeline = [
                {'$match': {'inbound_date': {'$gte': start_date, '$lte': end_date}}},
                {'$group': {'_id': '$supplier_name'}},
                {'$count': 'active_suppliers'}
            ]
            supplier_result = list(self.db['purchase_inbound'].aggregate(supplier_pipeline))

            # 库存价值统计
            inventory_pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_inventory_value': {'$sum': {'$multiply': ['$current_stock', '$unit_price']}},
                        'total_items': {'$sum': 1},
                        'low_stock_items': {
                            '$sum': {'$cond': [{'$lt': ['$current_stock', '$safety_stock']}, 1, 0]}
                        }
                    }
                }
            ]
            inventory_result = list(self.db['inventory_summary'].aggregate(inventory_pipeline))

            # 构建概览数据
            sales_data = sales_result[0] if sales_result else {}
            purchase_data = purchase_result[0] if purchase_result else {}
            inventory_data = inventory_result[0] if inventory_result else {}

            overview_data = {
                # 销售指标
                'total_sales': sales_data.get('total_sales', 0),
                'total_sales_count': sales_data.get('total_sales_count', 0),
                'avg_order_value': sales_data.get('avg_order_value', 0),
                'max_order_value': sales_data.get('max_order_value', 0),
                'min_order_value': sales_data.get('min_order_value', 0),
                
                # 采购指标
                'total_purchases': purchase_data.get('total_purchases', 0),
                'total_purchase_count': purchase_data.get('total_purchase_count', 0),
                'avg_purchase_value': purchase_data.get('avg_purchase_value', 0),
                
                # 客户供应商指标
                'active_customers': customer_result[0]['active_customers'] if customer_result else 0,
                'active_suppliers': supplier_result[0]['active_suppliers'] if supplier_result else 0,
                'total_customers': self.db['customers'].count_documents({}),
                'total_suppliers': self.db['suppliers'].count_documents({}),
                
                # 库存指标
                'total_inventory_value': inventory_data.get('total_inventory_value', 0),
                'total_inventory_items': inventory_data.get('total_items', 0),
                'low_stock_items': inventory_data.get('low_stock_items', 0),
                
                # 计算指标
                'gross_margin': sales_data.get('total_sales', 0) - purchase_data.get('total_purchases', 0),
                'customer_activity_rate': (customer_result[0]['active_customers'] / max(self.db['customers'].count_documents({}), 1)) * 100 if customer_result else 0,
                'supplier_activity_rate': (supplier_result[0]['active_suppliers'] / max(self.db['suppliers'].count_documents({}), 1)) * 100 if supplier_result else 0,
                
                # 时间信息
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'generated_at': datetime.now().isoformat()
            }

            self.logger.info(f"业务概览生成完成，销售总额: {overview_data['total_sales']}")
            return {'success': True, 'data': overview_data}
            
        except Exception as e:
            self.logger.error(f"获取业务概览失败: {str(e)}")
            return {'success': False, 'message': f'获取业务概览失败: {str(e)}'}

    def analyze_sales_trend(self, dimension: str, date_range: Dict, top_n: int = 20) -> Dict:
        """分析销售趋势（增强版）"""
        try:
            self.logger.info(f"开始分析销售趋势，维度: {dimension}")
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}}
            ]

            if dimension == 'product':
                group_id = '$sales_product_name'
                sort_field = 'total_sales'
                trend_data = self._analyze_product_trend(pipeline, top_n)
            elif dimension == 'customer':
                group_id = '$customer_name'
                sort_field = 'total_sales'
                trend_data = self._analyze_customer_trend(pipeline, top_n)
            elif dimension == 'month':
                trend_data = self._analyze_monthly_trend(pipeline)
            elif dimension == 'week':
                trend_data = self._analyze_weekly_trend(pipeline)
            elif dimension == 'quarter':
                trend_data = self._analyze_quarterly_trend(pipeline)
            else:
                return {'success': False, 'message': '不支持的分析维度'}

            self.logger.info(f"销售趋势分析完成，数据点: {len(trend_data)}")
            return {'success': True, 'data': trend_data, 'dimension': dimension}
            
        except Exception as e:
            self.logger.error(f"分析销售趋势失败: {str(e)}")
            return {'success': False, 'message': f'分析销售趋势失败: {str(e)}'}

    def _analyze_product_trend(self, base_pipeline: List[Dict], top_n: int) -> List[Dict]:
        """分析产品销售趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': '$sales_product_name',
                    'total_sales': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'order_count': {'$sum': 1},
                    'avg_unit_price': {'$avg': {'$divide': ['$amount', '$quantity']}},
                    'max_order_value': {'$max': '$amount'},
                    'min_order_value': {'$min': '$amount'}
                }
            },
            {'$sort': {'total_sales': -1}},
            {'$limit': top_n}
        ]
        
        return list(self.db['sales_outbound'].aggregate(pipeline))

    def _analyze_customer_trend(self, base_pipeline: List[Dict], top_n: int) -> List[Dict]:
        """分析客户销售趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': '$customer_name',
                    'total_sales': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'order_count': {'$sum': 1},
                    'avg_order_value': {'$avg': '$amount'},
                    'first_order_date': {'$min': '$outbound_date'},
                    'last_order_date': {'$max': '$outbound_date'}
                }
            },
            {'$sort': {'total_sales': -1}},
            {'$limit': top_n}
        ]
        
        return list(self.db['sales_outbound'].aggregate(pipeline))

    def _analyze_monthly_trend(self, base_pipeline: List[Dict]) -> List[Dict]:
        """分析月度销售趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': {'$dateToString': {'format': '%Y-%m', 'date': '$outbound_date'}},
                    'total_sales': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'order_count': {'$sum': 1},
                    'avg_order_value': {'$avg': '$amount'},
                    'unique_customers': {'$addToSet': '$customer_name'}
                }
            },
            {
                '$project': {
                    'month': '$_id',
                    'total_sales': 1,
                    'total_quantity': 1,
                    'order_count': 1,
                    'avg_order_value': 1,
                    'customer_count': {'$size': '$unique_customers'}
                }
            },
            {'$sort': {'month': 1}}
        ]
        
        return list(self.db['sales_outbound'].aggregate(pipeline))

    def _analyze_weekly_trend(self, base_pipeline: List[Dict]) -> List[Dict]:
        """分析周度销售趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$outbound_date'},
                        'week': {'$week': '$outbound_date'}
                    },
                    'total_sales': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'order_count': {'$sum': 1}
                }
            },
            {
                '$project': {
                    'week': {'$concat': [
                        {'$toString': '$_id.year'}, 
                        '-W', 
                        {'$toString': '$_id.week'}
                    ]},
                    'year': '$_id.year',
                    'week_number': '$_id.week',
                    'total_sales': 1,
                    'total_quantity': 1,
                    'order_count': 1
                }
            },
            {'$sort': {'year': 1, 'week_number': 1}}
        ]
        
        return list(self.db['sales_outbound'].aggregate(pipeline))

    def _analyze_quarterly_trend(self, base_pipeline: List[Dict]) -> List[Dict]:
        """分析季度销售趋势"""
        pipeline = base_pipeline + [
            {
                '$addFields': {
                    'quarter': {
                        '$concat': [
                            {'$toString': {'$year': '$outbound_date'}},
                            '-Q',
                            {'$toString': {'$ceil': {'$divide': [{'$month': '$outbound_date'}, 3]}}}
                        ]
                    }
                }
            },
            {
                '$group': {
                    '_id': '$quarter',
                    'total_sales': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'order_count': {'$sum': 1},
                    'unique_customers': {'$addToSet': '$customer_name'},
                    'unique_products': {'$addToSet': '$sales_product_name'}
                }
            },
            {
                '$project': {
                    'quarter': '$_id',
                    'total_sales': 1,
                    'total_quantity': 1,
                    'order_count': 1,
                    'customer_count': {'$size': '$unique_customers'},
                    'product_count': {'$size': '$unique_products'}
                }
            },
            {'$sort': {'quarter': 1}}
        ]
        
        return list(self.db['sales_outbound'].aggregate(pipeline))

    def analyze_customer_value(self, analysis_type: str = 'rfm') -> Dict:
        """分析客户价值（增强RFM模型）"""
        if analysis_type != 'rfm':
            return {'success': False, 'message': '不支持的客户价值分析类型'}

        try:
            self.logger.info("开始进行客户价值RFM分析")
            now = datetime.now()
            
            # RFM分析管道
            pipeline = [
                {
                    '$group': {
                        '_id': '$customer_name',
                        'last_purchase_date': {'$max': '$outbound_date'},
                        'frequency': {'$sum': 1},
                        'monetary': {'$sum': '$amount'},
                        'avg_order_value': {'$avg': '$amount'},
                        'first_purchase_date': {'$min': '$outbound_date'},
                        'total_quantity': {'$sum': '$quantity'}
                    }
                },
                {
                    '$project': {
                        'customer_name': '$_id',
                        '_id': 0,
                        'last_purchase_date': '$last_purchase_date',
                        'frequency': '$frequency',
                        'monetary': '$monetary',
                        'avg_order_value': '$avg_order_value',
                        'first_purchase_date': '$first_purchase_date',
                        'total_quantity': '$total_quantity'
                    }
                }
            ]

            results = list(self.db['sales_outbound'].aggregate(pipeline))

            # 计算RFM指标并分级
            for item in results:
                # Recency (最近一次购买距今天数)
                recency_days = (now - item['last_purchase_date']).days
                item['recency'] = recency_days
                
                # 客户生命周期（天数）
                lifecycle_days = (item['last_purchase_date'] - item['first_purchase_date']).days
                item['lifecycle_days'] = max(lifecycle_days, 1)
                
                # 购买频率（次/天）
                item['purchase_frequency'] = item['frequency'] / max(lifecycle_days, 1)

            # RFM评分计算
            if results:
                # 排序并计算分位数
                results_by_recency = sorted(results, key=lambda x: x['recency'])
                results_by_frequency = sorted(results, key=lambda x: x['frequency'], reverse=True)
                results_by_monetary = sorted(results, key=lambda x: x['monetary'], reverse=True)
                
                n = len(results)
                
                # 计算RFM评分
                for i, item in enumerate(results):
                    # Recency评分 (最近购买的客户得分高)
                    r_rank = next((j for j, x in enumerate(results_by_recency) if x['customer_name'] == item['customer_name']), 0)
                    item['r_score'] = 5 - int(r_rank / (n / 5))
                    
                    # Frequency评分
                    f_rank = next((j for j, x in enumerate(results_by_frequency) if x['customer_name'] == item['customer_name']), 0)
                    item['f_score'] = int(f_rank / (n / 5)) + 1
                    
                    # Monetary评分
                    m_rank = next((j for j, x in enumerate(results_by_monetary) if x['customer_name'] == item['customer_name']), 0)
                    item['m_score'] = int(m_rank / (n / 5)) + 1
                    
                    # 限制评分范围
                    item['r_score'] = max(1, min(5, item['r_score']))
                    item['f_score'] = max(1, min(5, item['f_score']))
                    item['m_score'] = max(1, min(5, item['m_score']))
                    
                    # 综合RFM评分
                    item['rfm_score'] = item['r_score'] + item['f_score'] + item['m_score']
                    
                    # 客户分类
                    if item['rfm_score'] >= 13:
                        item['customer_segment'] = '冠军客户'
                    elif item['rfm_score'] >= 11:
                        item['customer_segment'] = '忠诚客户'
                    elif item['rfm_score'] >= 9:
                        item['customer_segment'] = '潜力客户'
                    elif item['rfm_score'] >= 7:
                        item['customer_segment'] = '新客户'
                    elif item['rfm_score'] >= 5:
                        item['customer_segment'] = '风险客户'
                    else:
                        item['customer_segment'] = '流失客户'

            # 按RFM评分排序
            results.sort(key=lambda x: x['rfm_score'], reverse=True)

            self.logger.info(f"客户价值分析完成，分析客户数: {len(results)}")
            return {'success': True, 'data': results}
            
        except Exception as e:
            self.logger.error(f"分析客户价值失败: {str(e)}")
            return {'success': False, 'message': f'分析客户价值失败: {str(e)}'}

    def analyze_inventory_turnover(self, date_range: Dict, include_dead_stock: bool = True) -> Dict:
        """分析库存周转率（增强版）"""
        try:
            self.logger.info("开始分析库存周转率")
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            # 计算销售成本
            sales_pipeline = [
                {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
                {
                    '$group': {
                        '_id': '$sales_product_name',
                        'total_cost_of_goods_sold': {'$sum': '$amount'},
                        'total_quantity_sold': {'$sum': '$quantity'},
                        'sales_count': {'$sum': 1},
                        'last_sale_date': {'$max': '$outbound_date'}
                    }
                }
            ]
            sales_result = list(self.db['sales_outbound'].aggregate(sales_pipeline))

            # 获取当前库存信息
            inventory_pipeline = [
                {
                    '$project': {
                        'material_name': 1,
                        'current_stock': 1,
                        'unit_price': 1,
                        'inventory_value': {'$multiply': ['$current_stock', '$unit_price']},
                        'safety_stock': 1,
                        'last_updated': 1
                    }
                }
            ]
            inventory_result = list(self.db['inventory_summary'].aggregate(inventory_pipeline))

            # 创建库存字典
            inventory_dict = {item['material_name']: item for item in inventory_result}

            # 分析每个产品的周转率
            turnover_analysis = []
            total_inventory_value = 0
            total_cogs = 0

            for sales_item in sales_result:
                product_name = sales_item['_id']
                inventory_item = inventory_dict.get(product_name, {})
                
                if inventory_item:
                    inventory_value = inventory_item.get('inventory_value', 0)
                    cogs = sales_item['total_cost_of_goods_sold']
                    
                    # 计算周转率
                    turnover_rate = cogs / inventory_value if inventory_value > 0 else 0
                    
                    # 计算周转天数
                    days_in_period = (end_date - start_date).days
                    turnover_days = days_in_period / turnover_rate if turnover_rate > 0 else float('inf')
                    
                    # 判断是否为呆滞库存
                    days_since_last_sale = (datetime.now() - sales_item['last_sale_date']).days if sales_item['last_sale_date'] else float('inf')
                    is_dead_stock = days_since_last_sale > 90  # 90天未销售视为呆滞
                    
                    turnover_analysis.append({
                        'product_name': product_name,
                        'inventory_value': inventory_value,
                        'current_stock': inventory_item.get('current_stock', 0),
                        'unit_price': inventory_item.get('unit_price', 0),
                        'cogs': cogs,
                        'turnover_rate': round(turnover_rate, 2),
                        'turnover_days': round(turnover_days, 1) if turnover_days != float('inf') else None,
                        'quantity_sold': sales_item['total_quantity_sold'],
                        'sales_count': sales_item['sales_count'],
                        'last_sale_date': sales_item['last_sale_date'].isoformat() if sales_item['last_sale_date'] else None,
                        'days_since_last_sale': days_since_last_sale if days_since_last_sale != float('inf') else None,
                        'is_dead_stock': is_dead_stock,
                        'stock_status': self._classify_stock_status(turnover_rate, days_since_last_sale)
                    })
                    
                    total_inventory_value += inventory_value
                    total_cogs += cogs

            # 识别呆滞库存
            dead_stock_items = []
            if include_dead_stock:
                for product_name, inventory_item in inventory_dict.items():
                    # 检查是否在销售数据中
                    has_sales = any(sales['_id'] == product_name for sales in sales_result)
                    if not has_sales and inventory_item.get('current_stock', 0) > 0:
                        dead_stock_items.append({
                            'product_name': product_name,
                            'current_stock': inventory_item.get('current_stock', 0),
                            'inventory_value': inventory_item.get('current_stock', 0) * inventory_item.get('unit_price', 0),
                            'unit_price': inventory_item.get('unit_price', 0),
                            'last_updated': inventory_item.get('last_updated').isoformat() if inventory_item.get('last_updated') else None,
                            'turnover_rate': 0,
                            'is_dead_stock': True,
                            'stock_status': '呆滞库存'
                        })

            # 计算总体周转率
            overall_turnover_rate = total_cogs / total_inventory_value if total_inventory_value > 0 else 0
            
            # 按周转率排序
            turnover_analysis.sort(key=lambda x: x['turnover_rate'], reverse=True)
            
            # 统计汇总
            total_products = len(turnover_analysis) + len(dead_stock_items)
            fast_moving_items = len([item for item in turnover_analysis if item['turnover_rate'] > 2])
            slow_moving_items = len([item for item in turnover_analysis if 0 < item['turnover_rate'] <= 0.5])
            dead_stock_count = len([item for item in turnover_analysis if item['is_dead_stock']]) + len(dead_stock_items)

            result_data = {
                'overall_turnover_rate': round(overall_turnover_rate, 2),
                'total_inventory_value': round(total_inventory_value, 2),
                'total_cogs': round(total_cogs, 2),
                'total_products': total_products,
                'fast_moving_items': fast_moving_items,
                'slow_moving_items': slow_moving_items,
                'dead_stock_count': dead_stock_count,
                'turnover_analysis': turnover_analysis,
                'dead_stock_items': dead_stock_items,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days
                },
                'generated_at': datetime.now().isoformat()
            }

            self.logger.info(f"库存周转率分析完成，总周转率: {overall_turnover_rate}")
            return {'success': True, 'data': result_data}
            
        except Exception as e:
            self.logger.error(f"分析库存周转率失败: {str(e)}")
            return {'success': False, 'message': f'分析库存周转率失败: {str(e)}'}

    def _classify_stock_status(self, turnover_rate: float, days_since_last_sale: Optional[float]) -> str:
        """库存状态分类"""
        if days_since_last_sale and days_since_last_sale > 90:
            return '呆滞库存'
        elif turnover_rate > 4:
            return '快速周转'
        elif turnover_rate > 2:
            return '正常周转'
        elif turnover_rate > 0.5:
            return '缓慢周转'
        else:
            return '滞销库存'

    def analyze_purchase_trend(self, dimension: str, date_range: Dict, top_n: int = 20) -> Dict:
        """分析采购趋势"""
        try:
            self.logger.info(f"开始分析采购趋势，维度: {dimension}")
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            base_pipeline = [
                {'$match': {'inbound_date': {'$gte': start_date, '$lte': end_date}}}
            ]

            if dimension == 'supplier':
                trend_data = self._analyze_supplier_trend(base_pipeline, top_n)
            elif dimension == 'material':
                trend_data = self._analyze_material_purchase_trend(base_pipeline, top_n)
            elif dimension == 'month':
                trend_data = self._analyze_purchase_monthly_trend(base_pipeline)
            else:
                return {'success': False, 'message': '不支持的采购分析维度'}

            self.logger.info(f"采购趋势分析完成，数据点: {len(trend_data)}")
            return {'success': True, 'data': trend_data, 'dimension': dimension}
            
        except Exception as e:
            self.logger.error(f"分析采购趋势失败: {str(e)}")
            return {'success': False, 'message': f'分析采购趋势失败: {str(e)}'}

    def _analyze_supplier_trend(self, base_pipeline: List[Dict], top_n: int) -> List[Dict]:
        """分析供应商采购趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': '$supplier_name',
                    'total_purchases': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'purchase_count': {'$sum': 1},
                    'avg_purchase_value': {'$avg': '$amount'},
                    'max_purchase_value': {'$max': '$amount'},
                    'min_purchase_value': {'$min': '$amount'},
                    'first_purchase_date': {'$min': '$inbound_date'},
                    'last_purchase_date': {'$max': '$inbound_date'},
                    'unique_materials': {'$addToSet': '$material_name'}
                }
            },
            {
                '$project': {
                    'supplier_name': '$_id',
                    'total_purchases': 1,
                    'total_quantity': 1,
                    'purchase_count': 1,
                    'avg_purchase_value': 1,
                    'max_purchase_value': 1,
                    'min_purchase_value': 1,
                    'first_purchase_date': 1,
                    'last_purchase_date': 1,
                    'material_variety': {'$size': '$unique_materials'}
                }
            },
            {'$sort': {'total_purchases': -1}},
            {'$limit': top_n}
        ]
        
        return list(self.db['purchase_inbound'].aggregate(pipeline))

    def _analyze_material_purchase_trend(self, base_pipeline: List[Dict], top_n: int) -> List[Dict]:
        """分析物料采购趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': '$material_name',
                    'total_purchases': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'purchase_count': {'$sum': 1},
                    'avg_unit_price': {'$avg': {'$divide': ['$amount', '$quantity']}},
                    'max_unit_price': {'$max': {'$divide': ['$amount', '$quantity']}},
                    'min_unit_price': {'$min': {'$divide': ['$amount', '$quantity']}},
                    'supplier_count': {'$addToSet': '$supplier_name'}
                }
            },
            {
                '$project': {
                    'material_name': '$_id',
                    'total_purchases': 1,
                    'total_quantity': 1,
                    'purchase_count': 1,
                    'avg_unit_price': 1,
                    'max_unit_price': 1,
                    'min_unit_price': 1,
                    'supplier_count': {'$size': '$supplier_count'},
                    'price_volatility': {'$subtract': ['$max_unit_price', '$min_unit_price']}
                }
            },
            {'$sort': {'total_purchases': -1}},
            {'$limit': top_n}
        ]
        
        return list(self.db['purchase_inbound'].aggregate(pipeline))

    def _analyze_purchase_monthly_trend(self, base_pipeline: List[Dict]) -> List[Dict]:
        """分析月度采购趋势"""
        pipeline = base_pipeline + [
            {
                '$group': {
                    '_id': {'$dateToString': {'format': '%Y-%m', 'date': '$inbound_date'}},
                    'total_purchases': {'$sum': '$amount'},
                    'total_quantity': {'$sum': '$quantity'},
                    'purchase_count': {'$sum': 1},
                    'avg_purchase_value': {'$avg': '$amount'},
                    'unique_suppliers': {'$addToSet': '$supplier_name'},
                    'unique_materials': {'$addToSet': '$material_name'}
                }
            },
            {
                '$project': {
                    'month': '$_id',
                    'total_purchases': 1,
                    'total_quantity': 1,
                    'purchase_count': 1,
                    'avg_purchase_value': 1,
                    'supplier_count': {'$size': '$unique_suppliers'},
                    'material_count': {'$size': '$unique_materials'}
                }
            },
            {'$sort': {'month': 1}}
        ]
        
        return list(self.db['purchase_inbound'].aggregate(pipeline))

    def generate_comparison_analysis(self, metrics: List[str], dimensions: List[str], date_range: Dict) -> Dict:
        """生成多维度对比分析（增强版）"""
        try:
            self.logger.info(f"开始生成对比分析，指标: {metrics}, 维度: {dimensions}")
            start_date = datetime.fromisoformat(date_range['start']) if date_range.get('start') else datetime.min
            end_date = datetime.fromisoformat(date_range['end']) if date_range.get('end') else datetime.max

            if not metrics or not dimensions:
                return {'success': False, 'message': '必须提供至少一个指标和维度'}

            # 销售数据分析
            sales_results = []
            if any(metric in ['total_sales', 'sales_count', 'avg_order_value'] for metric in metrics):
                sales_results = self._generate_sales_comparison(metrics, dimensions, start_date, end_date)

            # 采购数据分析
            purchase_results = []
            if any(metric in ['total_purchases', 'purchase_count', 'avg_purchase_value'] for metric in metrics):
                purchase_results = self._generate_purchase_comparison(metrics, dimensions, start_date, end_date)

            # 库存数据分析
            inventory_results = []
            if any(metric in ['inventory_value', 'stock_quantity'] for metric in metrics):
                inventory_results = self._generate_inventory_comparison(metrics, dimensions)

            result_data = {
                'sales_analysis': sales_results,
                'purchase_analysis': purchase_results,
                'inventory_analysis': inventory_results,
                'metrics': metrics,
                'dimensions': dimensions,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'generated_at': datetime.now().isoformat()
            }

            self.logger.info("对比分析生成完成")
            return {'success': True, 'data': result_data}
            
        except Exception as e:
            self.logger.error(f"生成对比分析失败: {str(e)}")
            return {'success': False, 'message': f'生成对比分析失败: {str(e)}'}

    def _generate_sales_comparison(self, metrics: List[str], dimensions: List[str], start_date: datetime, end_date: datetime) -> List[Dict]:
        """生成销售对比分析"""
        dimension_map = {
            'product': '$sales_product_name',
            'customer': '$customer_name',
            'month': {'$dateToString': {'format': '%Y-%m', 'date': '$outbound_date'}}
        }
        
        group_id = {}
        for dim in dimensions:
            if dim in dimension_map:
                group_id[dim] = dimension_map[dim]
        
        if not group_id:
            return []

        group_stage = {'_id': group_id}
        for metric in metrics:
            if metric == 'total_sales':
                group_stage['total_sales'] = {'$sum': '$amount'}
            elif metric == 'sales_count':
                group_stage['sales_count'] = {'$sum': 1}
            elif metric == 'avg_order_value':
                group_stage['avg_order_value'] = {'$avg': '$amount'}

        pipeline = [
            {'$match': {'outbound_date': {'$gte': start_date, '$lte': end_date}}},
            {'$group': group_stage},
            {'$sort': {'_id': 1}}
        ]

        return list(self.db['sales_outbound'].aggregate(pipeline))

    def _generate_purchase_comparison(self, metrics: List[str], dimensions: List[str], start_date: datetime, end_date: datetime) -> List[Dict]:
        """生成采购对比分析"""
        dimension_map = {
            'material': '$material_name',
            'supplier': '$supplier_name',
            'month': {'$dateToString': {'format': '%Y-%m', 'date': '$inbound_date'}}
        }
        
        group_id = {}
        for dim in dimensions:
            if dim in dimension_map:
                group_id[dim] = dimension_map[dim]
        
        if not group_id:
            return []

        group_stage = {'_id': group_id}
        for metric in metrics:
            if metric == 'total_purchases':
                group_stage['total_purchases'] = {'$sum': '$amount'}
            elif metric == 'purchase_count':
                group_stage['purchase_count'] = {'$sum': 1}
            elif metric == 'avg_purchase_value':
                group_stage['avg_purchase_value'] = {'$avg': '$amount'}

        pipeline = [
            {'$match': {'inbound_date': {'$gte': start_date, '$lte': end_date}}},
            {'$group': group_stage},
            {'$sort': {'_id': 1}}
        ]

        return list(self.db['purchase_inbound'].aggregate(pipeline))

    def _generate_inventory_comparison(self, metrics: List[str], dimensions: List[str]) -> List[Dict]:
        """生成库存对比分析"""
        dimension_map = {
            'material': '$material_name',
            'supplier': '$supplier_name',
            'warehouse': '$warehouse'
        }
        
        group_id = {}
        for dim in dimensions:
            if dim in dimension_map:
                group_id[dim] = dimension_map[dim]
        
        if not group_id:
            return []

        group_stage = {'_id': group_id}
        for metric in metrics:
            if metric == 'inventory_value':
                group_stage['inventory_value'] = {'$sum': {'$multiply': ['$current_stock', '$unit_price']}}
            elif metric == 'stock_quantity':
                group_stage['stock_quantity'] = {'$sum': '$current_stock'}

        pipeline = [
            {'$group': group_stage},
            {'$sort': {'_id': 1}}
        ]

        return list(self.db['inventory_summary'].aggregate(pipeline))

    def get_dashboard_summary(self, date_range: Dict) -> Dict:
        """获取仪表板汇总数据"""
        try:
            self.logger.info("开始生成仪表板汇总数据")
            
            # 获取业务概览
            overview_result = self.get_business_overview(date_range)
            if not overview_result['success']:
                return overview_result
            
            overview_data = overview_result['data']
            
            # 获取销售趋势（月度）
            sales_trend_result = self.analyze_sales_trend('month', date_range)
            sales_trend_data = sales_trend_result['data'] if sales_trend_result['success'] else []
            
            # 获取客户价值分析（Top 10）
            customer_value_result = self.analyze_customer_value('rfm')
            customer_value_data = customer_value_result['data'][:10] if customer_value_result['success'] else []
            
            # 获取库存周转分析
            inventory_turnover_result = self.analyze_inventory_turnover(date_range, include_dead_stock=True)
            inventory_turnover_data = inventory_turnover_result['data'] if inventory_turnover_result['success'] else {}
            
            # 汇总数据
            dashboard_data = {
                'overview': overview_data,
                'sales_trend': sales_trend_data,
                'top_customers': customer_value_data,
                'inventory_turnover': {
                    'overall_rate': inventory_turnover_data.get('overall_turnover_rate', 0),
                    'fast_moving_items': inventory_turnover_data.get('fast_moving_items', 0),
                    'dead_stock_count': inventory_turnover_data.get('dead_stock_count', 0),
                    'total_inventory_value': inventory_turnover_data.get('total_inventory_value', 0)
                },
                'key_metrics': {
                    'total_revenue': overview_data.get('total_sales', 0),
                    'total_orders': overview_data.get('total_sales_count', 0),
                    'avg_order_value': overview_data.get('avg_order_value', 0),
                    'active_customers': overview_data.get('active_customers', 0),
                    'inventory_value': overview_data.get('total_inventory_value', 0),
                    'low_stock_alerts': overview_data.get('low_stock_items', 0)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info("仪表板汇总数据生成完成")
            return {'success': True, 'data': dashboard_data}
            
        except Exception as e:
            self.logger.error(f"生成仪表板汇总数据失败: {str(e)}")
            return {'success': False, 'message': f'生成仪表板汇总数据失败: {str(e)}'}

if __name__ == '__main__':
    import argparse
    import json
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='数据分析服务')
    parser.add_argument('--method', required=True, help='要调用的方法名')
    parser.add_argument('--params', help='方法参数（JSON格式）')
    
    args = parser.parse_args()
    
    try:
        # 初始化服务
        service = DataAnalysisService()
        
        # 解析参数
        params = {}
        if args.params:
            params = json.loads(args.params)
        
        # 调用相应的方法
        result = None
        
        if args.method == 'get_dashboard_summary':
            date_range = {
                'start': params.get('start_date', '2024-01-01') + 'T00:00:00',
                'end': params.get('end_date', '2024-12-31') + 'T23:59:59'
            }
            result = service.get_dashboard_summary(date_range)
            
        elif args.method == 'analyze_sales_trend':
            date_range = {
                'start': params.get('start_date', '2024-01-01') + 'T00:00:00',
                'end': params.get('end_date', '2024-12-31') + 'T23:59:59'
            }
            dimension = params.get('dimension', 'month')
            top_n = params.get('top_n', 20)
            result = service.analyze_sales_trend(dimension, date_range, top_n)
            
        elif args.method == 'analyze_inventory_turnover':
            date_range = {
                'start': params.get('start_date', '2024-01-01') + 'T00:00:00',
                'end': params.get('end_date', '2024-12-31') + 'T23:59:59'
            }
            include_dead_stock = params.get('include_dead_stock', True)
            result = service.analyze_inventory_turnover(date_range, include_dead_stock)
            
        elif args.method == 'analyze_customer_value':
            analysis_type = params.get('analysis_type', 'rfm')
            result = service.analyze_customer_value(analysis_type)
            
        elif args.method == 'analyze_purchase_trend':
            date_range = {
                'start': params.get('start_date', '2024-01-01') + 'T00:00:00',
                'end': params.get('end_date', '2024-12-31') + 'T23:59:59'
            }
            dimension = params.get('dimension', 'supplier')
            top_n = params.get('top_n', 20)
            result = service.analyze_purchase_trend(dimension, date_range, top_n)
            
        elif args.method == 'generate_comparison_analysis':
            date_range = {
                'start': params.get('start_date', '2024-01-01') + 'T00:00:00',
                'end': params.get('end_date', '2024-12-31') + 'T23:59:59'
            }
            metrics = params.get('metrics', ['total_sales'])
            dimensions = params.get('dimensions', ['month'])
            result = service.generate_comparison_analysis(metrics, dimensions, date_range)
            
        elif args.method == 'get_business_overview':
            date_range = {
                'start': params.get('start_date', '2024-01-01') + 'T00:00:00',
                'end': params.get('end_date', '2024-12-31') + 'T23:59:59'
            }
            result = service.get_business_overview(date_range)
            
        else:
            result = {
                'success': False,
                'message': f'不支持的方法: {args.method}'
            }
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, default=str))
        
    except Exception as e:
        # 输出错误结果
        error_result = {
            'success': False,
            'message': f'执行失败: {str(e)}'
        }
        print(json.dumps(error_result, ensure_ascii=False))
